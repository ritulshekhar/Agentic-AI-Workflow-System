import json
import re
import time
from typing import List, Dict, Any, Literal, TypedDict
from pydantic import BaseModel, Field

# LangChain & LangGraph Imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# Local Imports
from backend.retriever import LocalRetriever

# =====================================================================
# 1. State Definition
# =====================================================================
# This defines the data schema passed between nodes in our LangGraph workflow.
class AgentState(TypedDict):
    query: str                   # The original user support request
    category: str                # Identified ticket category
    retrieved_context: str       # Text fetched from knowledge base files
    draft_response: str          # Response drafted by the Response Agent
    feedback: str                # Feedback provided by the Supervisor Agent
    validation_passes: bool      # Did the Supervisor approve the response?
    retry_count: int             # Number of times response went back for revision
    agent_steps: List[Dict[str, Any]] # Custom logs for visual step-by-step display
    llm_config: Dict[str, Any]   # LLM parameters: API key, endpoint, model, mock mode toggle

# =====================================================================
# 2. Local Retriever Initialization
# =====================================================================
# Reads the local knowledge base directory
retriever = LocalRetriever(kb_dir="knowledge_base")

# =====================================================================
# 3. Live LLM Configuration Helper
# =====================================================================
def get_llm(llm_config: Dict[str, Any]) -> ChatOpenAI:
    """
    Initializes and returns a ChatOpenAI instance based on the configurations
    passed at runtime (e.g., custom API keys, custom endpoints, model name).
    """
    api_key = llm_config.get("api_key") or "dummy-key"
    base_url = llm_config.get("base_url") or "https://api.openai.com/v1"
    model_name = llm_config.get("model_name") or "gpt-3.5-turbo"
    
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0.2, # Lower temperature for stable, predictable customer support answers
        max_retries=2
    )

# =====================================================================
# 4. Agent Nodes Implementation
# =====================================================================

# --- A. Classification Agent ---
def classification_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes the user's query to categorize it into:
    Refunds & Returns, Shipping & Delivery, Technical Support & Accounts, or General Queries.
    """
    query = state["query"]
    llm_config = state["llm_config"]
    agent_steps = state.get("agent_steps", [])
    
    start_time = time.time()
    
    if llm_config.get("mock_mode", True):
        # --- Mock Classification Logic ---
        time.sleep(1.2) # Simulate network/inference latency
        query_l = query.lower()
        
        # Simple heuristics for classification
        if any(w in query_l for w in ["refund", "return", "cancel", "money", "charged", "billing", "fee"]):
            category = "Refunds & Returns"
            reasoning = "Query contains financial and return terms such as refund or billing."
        elif any(w in query_l for w in ["shipping", "deliver", "express", "tracking", "fedex", "ups", "usps", "customs", "delay"]):
            category = "Shipping & Delivery"
            reasoning = "Query mentions shipping, delivery speed, or tracking parameters."
        elif any(w in query_l for w in ["login", "password", "crash", "error", "2fa", "account", "locked", "bug", "troubleshoot"]):
            category = "Technical Support & Accounts"
            reasoning = "Query requests assistance with logins, account configuration, or app errors."
        else:
            category = "General Queries"
            reasoning = "Query is general in nature and does not match specific departmental keywords."
            
        thoughts = f"Analyzing incoming support ticket: '{query}'. Detected keywords suggest category: '{category}'. Reason: {reasoning}"
    else:
        # --- Live LLM Classification Logic ---
        llm = get_llm(llm_config)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI Routing Agent. Analyze the customer support ticket and classify it into EXACTLY one of these categories:\n"
                       "- Refunds & Returns\n"
                       "- Shipping & Delivery\n"
                       "- Technical Support & Accounts\n"
                       "- General Queries\n\n"
                       "Respond in JSON format with the keys 'category' and 'reasoning'."),
            ("human", "{query}")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        try:
            res = chain.invoke({"query": query})
            category = res.get("category", "General Queries")
            reasoning = res.get("reasoning", "LLM determined routing classification.")
            thoughts = f"LLM Routing Chain response: Category='{category}'. Reason: {reasoning}"
        except Exception as e:
            # Fallback
            category = "General Queries"
            thoughts = f"Classification chain failed with error: {str(e)}. Defaulted to General."
            
    step_log = {
        "agent": "Classification Agent",
        "action": f"Classifying ticket category",
        "thoughts": thoughts,
        "result": f"Routed to: {category}",
        "elapsed_seconds": round(time.time() - start_time, 2)
    }
    
    return {
        "category": category,
        "agent_steps": agent_steps + [step_log]
    }


# --- B. Retrieval Agent ---
def retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    Searches the local knowledge base for policies matching the query and category.
    """
    query = state["query"]
    category = state["category"]
    agent_steps = state.get("agent_steps", [])
    
    start_time = time.time()
    time.sleep(1.0) # Simulate latency
    
    # Retrieve relevant context from local files
    retrieved_docs = retriever.retrieve(query=query, category=category, top_k=2)
    
    context_str = ""
    sources = []
    for idx, doc in enumerate(retrieved_docs):
        sources.append(doc["source"])
        context_str += f"[Source: {doc['source']}]\n{doc['content']}\n\n"
    
    context_str = context_str.strip()
    sources_str = ", ".join(set(sources)) if sources else "None"
    
    thoughts = f"Query identified as '{category}'. Searching local files. Selected documents: {sources_str} based on content score."
    
    step_log = {
        "agent": "Retrieval Agent",
        "action": f"Querying local knowledge base",
        "thoughts": thoughts,
        "result": f"Retrieved relevant content from: {sources_str}",
        "elapsed_seconds": round(time.time() - start_time, 2)
    }
    
    return {
        "retrieved_context": context_str,
        "agent_steps": agent_steps + [step_log]
    }


# --- C. Response Agent ---
def response_node(state: AgentState) -> Dict[str, Any]:
    """
    Drafts (or refines) a professional response to the customer based on the query and retrieved context.
    """
    query = state["query"]
    category = state["category"]
    context = state["retrieved_context"]
    feedback = state.get("feedback", "")
    retry_count = state.get("retry_count", 0)
    llm_config = state["llm_config"]
    agent_steps = state.get("agent_steps", [])
    
    start_time = time.time()
    
    if llm_config.get("mock_mode", True):
        # --- Mock Response Logic ---
        time.sleep(1.5)
        
        # A mock response template based on classification
        if category == "Refunds & Returns":
            draft = (
                "Hi there,\n\n"
                "Thank you for reaching out to customer support. Regarding your refund request, "
                "our policy allows you to return any unused item in its original packaging within 30 days of receipt "
                "for a full refund. Digital products are non-refundable once accessed, and clearance items are final sale.\n\n"
                "Standard returns have a standard $5.99 return shipping deduction, but if this return is due to a company error "
                "or shipping defect, we will waive this fee and provide a free label. Once we receive your item, please allow 5-7 "
                "business days to process your refund. Let us know if you'd like to initiate this return.\n\n"
                "Best regards,\nCustomer Support Team"
            )
        elif category == "Shipping & Delivery":
            draft = (
                "Hello,\n\n"
                "Thank you for contacting us. We've retrieved your order shipping status. Standard delivery within the continental US "
                "takes 3 to 5 business days, while Express takes 1 to 2 business days. If your order has been dispatched, a tracking number "
                "was sent to your email. Please note it can take up to 24 hours for carriers to activate tracking links.\n\n"
                "If your shipment is delayed due to weather or seasonal peaks, our standard guidelines ask to wait 3 additional business "
                "days beyond the estimate before we can launch an investigation. Please let us know if your package is still missing after "
                "this timeline so we can assist further.\n\n"
                "Best regards,\nCustomer Support Team"
            )
        elif category == "Technical Support & Accounts":
            draft = (
                "Hi there,\n\n"
                "Thank you for getting in touch. To resolve login or password issues, please try clicking 'Forgot Password' on the login screen. "
                "This sends a reset link valid for 1 hour. Make sure to check your Spam folder if it doesn't arrive. For application crashes, "
                "we recommend clearing your browser cookies and cache, or upgrading your mobile app to the latest version.\n\n"
                "Please note that for 2FA verification resets, a support supervisor must manually verify your identity before disabling security settings. "
                "If you continue to experience issues, let us know your exact device model or operating system.\n\n"
                "Warm regards,\nTechnical Support Team"
            )
        else:
            draft = (
                "Hello,\n\n"
                "Thank you for writing to support. We have received your query and would be happy to help. Based on your ticket, "
                "we are checking our company information to provide you with the most accurate details. A customer support representative "
                "will get back to you shortly, or you can reply with additional details to help us troubleshoot your issue.\n\n"
                "Best regards,\nCustomer Support Team"
            )
            
        # If there was feedback from the supervisor, simulate a draft update!
        if feedback and retry_count > 0:
            draft = "[REVISED] " + draft.replace(
                "Best regards,\nCustomer Support Team", 
                "We apologize for the inconvenience and hope this revised information solves your issue.\n\nBest regards,\nCustomer Support Team"
            )
            thoughts = f"Refining response based on supervisor feedback: '{feedback}'. Appended apology and reinforced explanation."
        else:
            thoughts = f"Drafting standard support response for category '{category}' using retrieved policy sheets."
            
    else:
        # --- Live LLM Response Logic ---
        llm = get_llm(llm_config)
        
        system_message = (
            "You are a professional customer support representative. Draft a helpful, polite, and detailed support reply "
            "answering the customer's query. You MUST use the provided knowledge base policies to construct your answer. "
            "Do not invent facts or offer exceptions not listed in the policies.\n\n"
            "KNOWLEDGE BASE POLICIES:\n"
            "{context}"
        )
        
        if feedback:
            system_message += f"\n\nCRITICAL FEEDBACK FROM SUPERVISOR (You MUST address this in your revised draft):\n{feedback}"
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "Customer Query: {query}")
        ])
        
        chain = prompt | llm | StrOutputParser()
        
        try:
            draft = chain.invoke({
                "context": context,
                "query": query
            })
            if feedback:
                thoughts = f"LLM generated revised response addressing supervisor feedback: '{feedback}'."
            else:
                thoughts = "LLM drafted initial response using retrieved KB context guidelines."
        except Exception as e:
            draft = f"Error generating response: {str(e)}"
            thoughts = f"Response generator failed: {str(e)}"
            
    step_log = {
        "agent": "Response Agent",
        "action": "Generating draft response" if retry_count == 0 else f"Refining draft (Attempt {retry_count + 1})",
        "thoughts": thoughts,
        "result": f"Response drafted (Length: {len(draft)} characters)",
        "elapsed_seconds": round(time.time() - start_time, 2)
    }
    
    return {
        "draft_response": draft,
        "agent_steps": agent_steps + [step_log]
    }


# --- D. Supervisor Agent ---
def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates the draft response generated by the Response Agent.
    Checks if:
    1. The answer actually addresses the customer's query.
    2. The tone is highly professional and polite.
    3. The response only states facts from the retrieved knowledge base (no hallucinations).
    
    If it fails validation, returns feedback. For educational looping purposes, we can trigger a mock failure
    on the first run of specific queries (e.g. if the customer complains with "urgent" or "angry" keywords)
    to show the graph backtracking in action!
    """
    query = state["query"]
    draft = state["draft_response"]
    context = state["retrieved_context"]
    retry_count = state.get("retry_count", 0)
    llm_config = state["llm_config"]
    agent_steps = state.get("agent_steps", [])
    
    start_time = time.time()
    
    if llm_config.get("mock_mode", True):
        # --- Mock Supervisor Logic ---
        time.sleep(1.4)
        
        # Trigger an educational mock revision loop if the query contains "urgent" or "angry"
        # and we haven't retried yet.
        is_urgent = any(w in query.lower() for w in ["urgent", "rush", "asap", "disappointed", "angry", "terrible", "hate"])
        
        if is_urgent and retry_count == 0:
            validation_passes = False
            feedback = "The ticket is flagged as urgent/angry. The drafted response needs to contain a formal apology for the inconvenience and express extreme urgency."
            thoughts = "Evaluation: Draft is factual, but customer is highly distressed/demanding. Rejecting initial draft to request adding an empathetic apology."
            result = "FAIL - Routing back to Response Agent for revision."
        else:
            validation_passes = True
            feedback = ""
            thoughts = "Evaluation: Draft covers the query perfectly, matches retrieved policies, and maintains a helpful support tone. Approved."
            result = "PASS - Response approved for dispatch."
            
    else:
        # --- Live LLM Supervisor Logic ---
        llm = get_llm(llm_config)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Quality Assurance Supervisor. Evaluate the customer support draft response against the customer query and retrieved facts.\n\n"
                       "CRITERIA:\n"
                       "1. Empathy & Tone: Is it polite, professional, and friendly?\n"
                       "2. Factual Accuracy: Does it stay strictly within the limits of the retrieved facts? If the query cannot be answered by the facts, it should politely state so and not make up details.\n"
                       "3. Answer Completeness: Does it address all parts of the user query?\n\n"
                       "Retrieved Facts:\n{context}\n\n"
                       "Draft Response:\n{draft}\n\n"
                       "Provide your evaluation in JSON format with the keys:\n"
                       "- 'is_valid' (boolean: true if it passes all criteria, false if revision is required)\n"
                       "- 'feedback' (string: detailed description of what needs adjustment if is_valid is false, empty string otherwise)"),
            ("human", "Customer Query: {query}")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        
        try:
            res = chain.invoke({
                "context": context,
                "draft": draft,
                "query": query
            })
            validation_passes = res.get("is_valid", True)
            feedback = res.get("feedback", "")
            
            if validation_passes:
                thoughts = "LLM Supervisor approved the response. Factual, helpful, and polite."
                result = "PASS - Response approved."
            else:
                thoughts = f"LLM Supervisor requested revisions. Feedback: {feedback}"
                result = "FAIL - Revision requested."
        except Exception as e:
            # Fallback
            validation_passes = True
            feedback = ""
            thoughts = f"Supervisor validation failed to run due to LLM error: {str(e)}. Auto-approving to prevent blocking."
            result = "PASS - Bypass approval."
            
    # Record the step
    step_log = {
        "agent": "Supervisor Agent",
        "action": "Reviewing draft quality",
        "thoughts": thoughts,
        "result": result,
        "elapsed_seconds": round(time.time() - start_time, 2)
    }
    
    # Increment retry count if validation failed
    next_retry_count = retry_count if validation_passes else retry_count + 1
    
    return {
        "validation_passes": validation_passes,
        "feedback": feedback,
        "retry_count": next_retry_count,
        "agent_steps": agent_steps + [step_log]
    }

# =====================================================================
# 5. Routing Decisions (LangGraph Conditional Edges)
# =====================================================================
def route_after_supervisor(state: AgentState) -> Literal["Response Agent", "End Workflow"]:
    """
    Decides the next node based on Supervisor validation and retry limits.
    """
    validation_passes = state["validation_passes"]
    retry_count = state["retry_count"]
    
    # If supervisor approves, end workflow and return response
    if validation_passes:
        return "End Workflow"
    
    # If supervisor rejects but we haven't exceeded 2 retries, route back to response agent
    if retry_count <= 2:
        return "Response Agent"
    
    # Safety valve: If we've retried too many times, terminate to avoid loops
    # Log safety exit in steps
    state["agent_steps"].append({
        "agent": "Supervisor Agent",
        "action": "Safety termination",
        "thoughts": "Workflow hit maximum retry budget (2 times). Approving current draft to avoid infinite loops.",
        "result": "PASS - Terminated after retry limit.",
        "elapsed_seconds": 0.0
    })
    return "End Workflow"

# =====================================================================
# 6. Workflow Graph Construction
# =====================================================================
def build_workflow() -> StateGraph:
    """
    Assembles the LangGraph state machine.
    """
    # 1. Initialize State Graph with schema
    workflow = StateGraph(AgentState)
    
    # 2. Register all node functions
    workflow.add_node("Classification Agent", classification_node)
    workflow.add_node("Retrieval Agent", retrieval_node)
    workflow.add_node("Response Agent", response_node)
    workflow.add_node("Supervisor Agent", supervisor_node)
    
    # 3. Connect nodes with edges
    workflow.set_entry_point("Classification Agent")
    
    workflow.add_edge("Classification Agent", "Retrieval Agent")
    workflow.add_edge("Retrieval Agent", "Response Agent")
    workflow.add_edge("Response Agent", "Supervisor Agent")
    
    # 4. Add conditional routing from Supervisor
    workflow.add_conditional_edges(
        "Supervisor Agent",
        route_after_supervisor,
        {
            "Response Agent": "Response Agent",
            "End Workflow": END
        }
    )
    
    # 5. Compile the graph
    return workflow.compile()

# Instantiated workflow graph ready to run
workflow_graph = build_workflow()

# =====================================================================
# 7. Helper Executor function
# =====================================================================
def run_support_workflow(query: str, llm_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Utility wrapper to run the compiled LangGraph workflow.
    """
    initial_state: AgentState = {
        "query": query,
        "category": "",
        "retrieved_context": "",
        "draft_response": "",
        "feedback": "",
        "validation_passes": False,
        "retry_count": 0,
        "agent_steps": [],
        "llm_config": llm_config
    }
    
    final_state = workflow_graph.invoke(initial_state)
    
    # Return formatted result
    return {
        "query": final_state["query"],
        "category": final_state["category"],
        "context": final_state["retrieved_context"],
        "response": final_state["draft_response"],
        "success": final_state["validation_passes"],
        "retry_count": final_state["retry_count"],
        "steps": final_state["agent_steps"]
    }
