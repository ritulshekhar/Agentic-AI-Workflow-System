# AgentFlow: Detailed Project Explanation

This document provides a comprehensive technical overview of the **Agentic AI Customer Support Ticket System**. It covers the architecture, state design, agent nodes, and details how **LangGraph** orchestrates state updates and execution loops.

---

## 1. Core Technical Concept

This system is designed as a **Multi-Agent Workflow Engine**. Unlike standard sequential pipelines, an *Agentic Workflow* permits routing decisions, loops, and quality checks dynamically. 

The problem we are solving is the automation of **Customer Support Tickets** using four distinct agents, each specialized in a specific task:
1.  **Classification Agent**: Identifies the department/category of the incoming issue.
2.  **Retrieval Agent**: Looks up company policies in a local text-based knowledge base based on the query category.
3.  **Response Agent**: Drafts or refines an email response utilizing the retrieved policies.
4.  **Supervisor Agent**: Evaluates the drafted response for quality, accuracy, and tone. If it fails, it provides feedback and redirects the state back to the Response Agent.

---

## 2. Technical Stack

*   **Orchestration Engine**: **LangGraph** (an extension of LangChain). LangGraph represents workflows as cyclic graphs (nodes and edges), making it ideal for validation and retry loops.
*   **Agent framework**: **LangChain**. Provides prompt templates, output parsers, and interfaces to OpenAI-compatible LLMs.
*   **Web API Backend**: **FastAPI**. Serves REST endpoints to solve tickets and log live operation metrics.
*   **User Interface**: **Streamlit**. Provides a web-based dashboard and a ticket submission console, rendering real-time agent execution visual traces and operational analytics.

---

## 3. Workflow & Architecture Diagram

Below is the state machine representation of the LangGraph workflow:

```
                  [Customer Support Ticket]
                              │
                              ▼
                     ┌──────────────────┐
                     │  Classification  │  (Identifies query type)
                     │      Agent       │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │    Retrieval     │  (Searches local knowledge
                     │      Agent       │   base files)
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │  Response Agent  │◀──────────────────────┐
                     │  (Drafts Email)  │                       │
                     └────────┬─────────┘                       │
                              │                                 │
                              ▼                                 │
                     ┌──────────────────┐                       │ (If rejected,
                     │ Supervisor Agent │                       │  max 2 retries)
                     │   (Validates)    │                       │
                     └────────┬─────────┘                       │
                              │                                 │
                              ├─── [Approved? No] ──────────────┘
                              │
                              └─── [Approved? Yes] ──► [Final Response]
```

---

## 4. State Management in LangGraph

LangGraph is stateful. The workflow passes a single state dictionary (`AgentState`) between nodes. When a node executes, it returns updates to the keys in the state. The keys in our graph state are defined below:

```python
class AgentState(TypedDict):
    query: str                   # The original customer support ticket text.
    category: str                # Department (e.g., Refunds & Returns).
    retrieved_context: str       # Relevant policy documents fetched by the Retriever.
    draft_response: str          # Draft reply email written by the Response Agent.
    feedback: str                # Quality assurance review comments from the Supervisor.
    validation_passes: bool      # True if the Supervisor approves, False otherwise.
    retry_count: int             # Tracks revision counts to prevent infinite loops.
    agent_steps: List[Dict]      # Log list for the frontend to render step-by-step progress.
    llm_config: Dict             # Contains API keys, endpoints, and mock mode configurations.
```

---

## 5. Walkthrough of the Agent Nodes

### Node 1: Classification Agent (`classification_node`)
*   **Goal**: Categorize incoming customer text.
*   **Process**: 
    *   *Live Mode*: Sends the ticket query to the LLM with a template requesting JSON categorizations: `Refunds & Returns`, `Shipping & Delivery`, `Technical Support & Accounts`, or `General Queries`.
    *   *Mock Mode*: Uses pattern matching heuristics (e.g. searching for keywords like "refund", "locked out") to determine category.
*   **Updates State**: `category`, `agent_steps`.

### Node 2: Retrieval Agent (`retrieval_node`)
*   **Goal**: Search the text database (`knowledge_base/`) for policy paragraphs.
*   **Process**: 
    *   Receives the query and identified category.
    *   Uses `LocalRetriever` to scan the text files (`refund_policy.txt`, `shipping_info.txt`, `technical_support.txt`) and returns the top 2 matching sections using term-overlap matching (giving a boost to files matching the category).
*   **Updates State**: `retrieved_context`, `agent_steps`.

### Node 3: Response Agent (`response_node`)
*   **Goal**: Formulate the response email.
*   **Process**: 
    *   *Initial Run*: Takes the query and the `retrieved_context` and designs a professional email response.
    *   *Revision Run*: If `feedback` is present from the Supervisor, the agent reads the supervisor's feedback notes along with the previous context to draft an improved response.
*   **Updates State**: `draft_response`, `agent_steps`.

### Node 4: Supervisor Agent (`supervisor_node`)
*   **Goal**: Validate response validity, accuracy, and tone.
*   **Process**: 
    *   *Live Mode*: Prompts the LLM to compare the `draft_response` against the `retrieved_context` and check if all query points are solved without inventing fake information. Returns JSON: `{"is_valid": true/false, "feedback": "..."}`.
    *   *Mock Mode*: Approves standard queries. If a query contains urgency tags like `ASAP` or `urgent`, it purposefully rejects the draft *once* to demand a more empathetic apology. This visualizes the backtracking routing logic for demonstration.
*   **Updates State**: `validation_passes`, `feedback`, `retry_count`, `agent_steps`.

---

## 6. Routing Decisions (Conditional Edges)

After the Supervisor Agent runs, a **Conditional Edge** evaluates the state variables:
1.  If `validation_passes` is `True`, routing redirects to `END` (terminates workflow).
2.  If `validation_passes` is `False` and `retry_count <= 2`, routing redirects execution back to the **Response Agent** node.
3.  If `retry_count > 2`, routing directs to `END` anyway to prevent infinite cycles, logging a safety warning to the user.

---

## 7. Business Dashboard and Analytics

In addition to ticket solving, the system aggregates operational metrics:
*   **CSAT Rating**: Simulated customer rating score based on resolution speed and whether a supervisor retry was necessary (perfect runs vote 5 stars, retries vote 4, failures vote 2).
*   **Category Distribution**: Tracks which department is receiving the most tickets.
*   **Historical Trends**: Records volumes and workflow success over a rolling 7-day period.
*   **Dual Mode Operations**: If the FastAPI server is active, it acts as a persistent database store. If Streamlit is run standalone (e.g. on Streamlit Cloud), the dashboard pulls and updates statistics directly in Streamlit session memory.
