import os
import sys
import time
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure backend directory is in the path for in-process execution fallback
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try importing backend agents directly (for in-process execution fallback)
try:
    from backend.agents import run_support_workflow
    HAS_BACKEND_CODE = True
except ImportError:
    HAS_BACKEND_CODE = False

# =====================================================================
# 1. Page Configuration & Custom CSS Styling
# =====================================================================
st.set_page_config(
    page_title="AgentFlow - Agentic Support Workflow System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling using HTML/CSS injection
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@400;600;800&display=swap');
    
    /* Main typography rules */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3, h4, .outfit-font {
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
    }
    
    /* Sleek gradient main header */
    .main-header {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    
    /* Subtitle styling */
    .sub-header {
        color: #9ca3af;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Glassmorphic card containers */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(5px);
    }
    
    /* Agent Steps styling badges */
    .agent-card {
        border-left: 4px solid #6366f1;
        background: rgba(99, 102, 241, 0.04);
        padding: 1rem 1.2rem;
        border-radius: 0 12px 12px 0;
        margin-bottom: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.03);
        border-right: 1px solid rgba(255, 255, 255, 0.03);
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    
    .agent-name {
        font-weight: 700;
        color: #818cf8;
        font-size: 1rem;
        margin-bottom: 0.3rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .agent-thoughts {
        font-style: italic;
        color: #d1d5db;
        font-size: 0.95rem;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
        background: rgba(0, 0, 0, 0.2);
        padding: 0.6rem;
        border-radius: 6px;
    }
    
    /* Response Display Box */
    .response-box {
        background: rgba(16, 185, 129, 0.05);
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-left: 5px solid #10b981;
        padding: 1.5rem;
        border-radius: 8px;
        color: #f3f4f6;
        white-space: pre-wrap;
        font-size: 1rem;
        line-height: 1.5;
    }
    
    /* Status indicators */
    .status-badge {
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    
    .status-pass {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid #10b981;
    }
    
    .status-fail {
        background-color: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid #ef4444;
    }
    
    /* Sidebar styling enhancements */
    .sidebar-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f3f4f6;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. Connection Settings & In-Memory Fallback Metrics Setup
# =====================================================================
BACKEND_URL = "http://127.0.0.1:8000"

# Initial mock data used for in-process memory
INITIAL_IN_PROCESS_METRICS = {
    "total_tickets": 142,
    "success_count": 136,
    "failure_count": 6,
    "success_rate": 95.7,
    "avg_resolution_time": 4.2,
    "total_resolution_time": 142 * 4.2,
    "csat_score": 4.80,
    "csat_votes": 85,
    "tickets_by_category": {
        "Refunds & Returns": 48,
        "Shipping & Delivery": 54,
        "Technical Support & Accounts": 32,
        "General Queries": 8
    },
    "history": [
        {"day": "Mon", "tickets": 15, "success_rate": 93.3},
        {"day": "Tue", "tickets": 22, "success_rate": 95.4},
        {"day": "Wed", "tickets": 18, "success_rate": 100.0},
        {"day": "Thu", "tickets": 25, "success_rate": 92.0},
        {"day": "Fri", "tickets": 28, "success_rate": 96.4},
        {"day": "Sat", "tickets": 14, "success_rate": 100.0},
        {"day": "Sun", "tickets": 20, "success_rate": 95.0}
    ]
}

# Initializing session state variables
if "in_process_metrics" not in st.session_state:
    # Deep copy dictionary
    st.session_state.in_process_metrics = {
        **INITIAL_IN_PROCESS_METRICS,
        "tickets_by_category": dict(INITIAL_IN_PROCESS_METRICS["tickets_by_category"]),
        "history": list(INITIAL_IN_PROCESS_METRICS["history"])
    }

# Check if the FastAPI backend is running
@st.cache_data(ttl=2) # Check server status quickly
def check_fastapi_connection() -> bool:
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=1.0)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

is_backend_active = check_fastapi_connection()

# =====================================================================
# 3. Sidebar Panel Configurations
# =====================================================================
with st.sidebar:
    st.markdown("<div class='sidebar-header'>🤖 AgentFlow Controls</div>", unsafe_allow_html=True)
    
    # Connection Mode Selection
    if is_backend_active:
        st.success("🟢 FastAPI Backend Server Connected")
        connection_mode = st.radio(
            "Execution Driver",
            options=["FastAPI Server API", "In-Process Engine (Direct Code)"],
            help="Choose whether to request ticket solutions from the FastAPI backend service or run the python libraries directly."
        )
    else:
        st.warning("🟡 FastAPI Server Offline. Defaulting to In-Process.")
        connection_mode = "In-Process Engine (Direct Code)"
        st.info("Direct Code mode allows this application to run standalone without external API servers. Perfect for hosting on Streamlit Cloud!")

    st.markdown("---")
    st.markdown("<div class='sidebar-header'>⚙️ LLM Configuration</div>", unsafe_allow_html=True)
    
    # Toggle Mock LLM vs Active LLMs
    llm_driver = st.checkbox("Enable Mock LLM Mode", value=True, help="Simulate AI reasoning and ticket outputs instantly without entering actual API keys.")
    
    api_key = ""
    endpoint = ""
    model_name = ""
    
    if not llm_driver:
        # Prompt for API details
        st.markdown("**LLM Credentials**")
        api_key = st.text_input("API Key", type="password", help="Input your OpenAI or OpenAI-compatible (e.g. Groq, OpenRouter) key.")
        endpoint = st.text_input("Base URL", value="https://api.openai.com/v1", help="Custom API server endpoint.")
        model_name = st.text_input("Model Name", value="gpt-3.5-turbo", help="Specific model parameter for agent prompts.")
        
        if not api_key:
            st.error("Please enter a valid API Key to disable Mock Mode.")

    st.markdown("---")
    st.markdown("<div class='sidebar-header'>📌 Quick Templates</div>", unsafe_allow_html=True)
    st.write("Click a template query to autofill:")
    
    templates = {
        "1. Refund Issue (Urgent/Loop Demo)": "URGENT: I ordered a jacket 10 days ago but it is clearance merchandise. I was charged $80. The packaging arrived completely torn and damaged, and the button is broken. I want my money back ASAP, please rush this!",
        "2. Technical Account Lockout": "Help! I am locked out of my account. I lost my mobile phone which had my Google Authenticator app for Two-Factor Authentication. Can someone please reset my security 2FA settings so I can access my dashboard?",
        "3. Delayed Shipping Inquiry": "My tracking number is active but has been stuck in 'Delivered' status on FedEx since yesterday. I checked my front porch and asked my neighbors but nobody has it. Where is my delivery?",
        "4. Standard Return General Question": "I bought a pair of shoes last week but they are slightly too small. They are unused and still have the tags attached. How many days do I have to return them, and is return shipping free?"
    }
    
    for t_name, t_text in templates.items():
        if st.button(t_name):
            st.session_state.autofill_query = t_text

# =====================================================================
# 4. Main Page Header
# =====================================================================
st.markdown("<div class='main-header'>Agentic AI Customer Support System</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Orchestrating Multiple AI Agents using Python, LangChain, LangGraph, and FastAPI</div>", unsafe_allow_html=True)

# Main Application Tabs
tab1, tab2 = st.tabs(["🚀 Ticket Resolution Workspace", "📊 Business Performance Dashboard"])

# =====================================================================
# TAB 1: Ticket Resolution Workspace
# =====================================================================
with tab1:
    col_input, col_kb = st.columns([7, 5])
    
    with col_input:
        st.subheader("📬 Customer Support Input")
        
        # Pull text from clicked template if existing
        default_val = st.session_state.get("autofill_query", "")
        
        # User input text box
        user_query = st.text_area(
            "Enter customer support request / ticket content:",
            value=default_val,
            height=130,
            placeholder="Type customer question here..."
        )
        
        # Clear template state so it does not persist on every submit
        if "autofill_query" in st.session_state:
            del st.session_state.autofill_query
            
        run_btn = st.button("▶ Run Agent Workflow", type="primary", use_container_width=True)
        
    with col_kb:
        st.subheader("📁 Local Knowledge Base Docs")
        st.write("Current business policies stored in plain text files:")
        
        # Collapsible files viewer for educational purposes
        with st.expander("📄 refund_policy.txt", expanded=False):
            if os.path.exists("knowledge_base/refund_policy.txt"):
                with open("knowledge_base/refund_policy.txt", "r") as f:
                    st.code(f.read(), language="text")
            else:
                st.write("File not found.")
                
        with st.expander("📄 shipping_info.txt", expanded=False):
            if os.path.exists("knowledge_base/shipping_info.txt"):
                with open("knowledge_base/shipping_info.txt", "r") as f:
                    st.code(f.read(), language="text")
            else:
                st.write("File not found.")
                
        with st.expander("📄 technical_support.txt", expanded=False):
            if os.path.exists("knowledge_base/technical_support.txt"):
                with open("knowledge_base/technical_support.txt", "r") as f:
                    st.code(f.read(), language="text")
            else:
                st.write("File not found.")

    st.markdown("---")
    
    # Workflow Execution Processing
    if run_btn:
        if not user_query.strip():
            st.error("Please enter a query or select a quick template first.")
        elif not llm_driver and not api_key:
            st.error("Live LLM Mode requires an API key in the sidebar configuration.")
        else:
            st.subheader("⚙️ LangGraph Multi-Agent Trace")
            
            # Setup configuration payload
            config_payload = {
                "mock_mode": llm_driver,
                "api_key": api_key,
                "base_url": endpoint,
                "model_name": model_name
            }
            
            # Run loading indicators
            with st.status("Executing Multi-Agent Workflow...", expanded=True) as status_box:
                result = None
                
                # Check execution mode
                if connection_mode == "FastAPI Server API":
                    # REST API Call
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/api/solve-ticket",
                            json={"query": user_query, "llm_config": config_payload},
                            timeout=60.0
                        )
                        if resp.status_code == 200:
                            result = resp.json()
                        else:
                            st.error(f"Backend Server returned an error: {resp.text}")
                    except Exception as e:
                        st.error(f"Failed to communicate with FastAPI server: {e}")
                else:
                    # In-process python library invocation
                    if HAS_BACKEND_CODE:
                        try:
                            start_time_ip = time.time()
                            # Invoke graph
                            result = run_support_workflow(query=user_query, llm_config=config_payload)
                            
                            elapsed_ip = round(time.time() - start_time_ip, 2)
                            result["resolution_time_seconds"] = elapsed_ip
                            
                            # --- Update direct-run in-memory session_state metrics ---
                            db = st.session_state.in_process_metrics
                            db["total_tickets"] += 1
                            
                            category = result.get("category", "General Queries")
                            if category not in db["tickets_by_category"]:
                                db["tickets_by_category"][category] = 0
                            db["tickets_by_category"][category] += 1
                            
                            success = result.get("success", True)
                            if success:
                                db["success_count"] += 1
                            else:
                                db["failure_count"] += 1
                                
                            db["success_rate"] = round((db["success_count"] / db["total_tickets"]) * 100, 1)
                            db["total_resolution_time"] += elapsed_ip
                            db["avg_resolution_time"] = round(db["total_resolution_time"] / db["total_tickets"], 2)
                            
                            score = 5 if (success and result.get("retry_count", 0) == 0) else (4 if success else 2)
                            db["csat_votes"] += 1
                            db["csat_score"] = round(
                                ((db["csat_score"] * (db["csat_votes"] - 1)) + score) / db["csat_votes"], 2
                            )
                        except Exception as e:
                            st.error(f"In-process execution crashed: {e}")
                    else:
                        st.error("Backend python modules could not be imported.")
                
                # Render step-by-step agent logs inside loading container
                if result:
                    steps = result.get("steps", [])
                    for idx, s in enumerate(steps):
                        # Format colors and labels for agents
                        agent = s.get("agent", "Agent")
                        action = s.get("action", "Working")
                        thoughts = s.get("thoughts", "")
                        res_detail = s.get("result", "")
                        elapsed = s.get("elapsed_seconds", 0.0)
                        
                        icon = "📁"
                        if "Classification" in agent:
                            icon = "🧭"
                        elif "Retrieval" in agent:
                            icon = "🔍"
                        elif "Response" in agent:
                            icon = "✍️"
                        elif "Supervisor" in agent:
                            icon = "⚖️"
                            
                        st.markdown(f"""
                        <div class="agent-card">
                            <div class="agent-name">
                                <span>{icon} {agent}</span> 
                                <span style="font-weight:normal; color:#6b7280; font-size:0.85rem;">— {action} ({elapsed}s)</span>
                            </div>
                            <div class="agent-thoughts">
                                <strong>Thoughts:</strong> {thoughts}
                            </div>
                            <div style="font-size:0.95rem; color:#a7f3d0; margin-top:0.3rem;">
                                <strong>Output:</strong> {res_detail}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        time.sleep(0.3) # Introduce short visual pacing
                        
                    status_box.update(label="Workflow Execution Finished successfully!", state="complete", expanded=True)
                else:
                    status_box.update(label="Workflow failed to run.", state="error")
            
            # Displays final output result box
            if result:
                st.markdown("### 🏆 Final Workflow Results")
                
                col1, col2 = st.columns([7, 5])
                
                with col1:
                    st.write("**Approved Customer Response Email:**")
                    st.markdown(f"""
                    <div class="response-box">{result.get("response", "No draft found.")}</div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.write("**Workflow Summary & Metadata:**")
                    
                    status_lbl = "Approved / Resolved" if result.get("success", True) else "Rejected / Flagged"
                    status_cls = "status-pass" if result.get("success", True) else "status-fail"
                    
                    st.markdown(f"""
                    <div class="glass-card">
                        <p><strong>Query Category:</strong> <span class="status-badge" style="background:#4f46e5; color:#fff; border:1px solid #6366f1;">{result.get("category", "Uncategorized")}</span></p>
                        <p><strong>Workflow Status:</strong> <span class="status-badge {status_cls}">{status_lbl}</span></p>
                        <p><strong>Supervisor Retries:</strong> {result.get("retry_count", 0)} / 2</p>
                        <p><strong>Resolution Latency:</strong> {result.get("resolution_time_seconds", 0.0)} seconds</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Expander for raw retrieved documents context
                    with st.expander("🔍 Show Retrieved KB Context", expanded=True):
                        st.code(result.get("context", "No context retrieved."), language="text")

# =====================================================================
# TAB 2: Business Performance Dashboard
# =====================================================================
with tab2:
    st.subheader("📈 Mock Operations Dashboard")
    st.write("Tracking business performance, success rates, and customer satisfaction metrics for the multi-agent system.")
    
    # 1. Fetch current active metrics
    if connection_mode == "FastAPI Server API":
        try:
            resp = requests.get(f"{BACKEND_URL}/api/metrics", timeout=5.0)
            if resp.status_code == 200:
                metrics = resp.json()
            else:
                metrics = st.session_state.in_process_metrics
        except:
            # Fallback to session state if FastAPI fails
            metrics = st.session_state.in_process_metrics
    else:
        metrics = st.session_state.in_process_metrics
        
    # Reset button for metrics
    col_reset_btn = st.columns([10, 2])
    with col_reset_btn[1]:
        if st.button("Reset Dashboard Stats", use_container_width=True):
            if connection_mode == "FastAPI Server API":
                try:
                    requests.post(f"{BACKEND_URL}/api/metrics/reset")
                    st.toast("Backend metrics reset!")
                    st.rerun()
                except:
                    st.session_state.in_process_metrics = {
                        **INITIAL_IN_PROCESS_METRICS,
                        "tickets_by_category": dict(INITIAL_IN_PROCESS_METRICS["tickets_by_category"]),
                        "history": list(INITIAL_IN_PROCESS_METRICS["history"])
                    }
                    st.toast("Local metrics reset!")
                    st.rerun()
            else:
                st.session_state.in_process_metrics = {
                    **INITIAL_IN_PROCESS_METRICS,
                    "tickets_by_category": dict(INITIAL_IN_PROCESS_METRICS["tickets_by_category"]),
                    "history": list(INITIAL_IN_PROCESS_METRICS["history"])
                }
                st.toast("Local metrics reset!")
                st.rerun()

    # 2. KPI Cards row
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <p style="color:#9ca3af; margin-bottom:0.1rem; font-size:0.9rem;">Total Tickets Handled</p>
            <h2 style="font-size:2.5rem; margin:0; color:#fff;">{metrics.get("total_tickets", 0)}</h2>
            <p style="color:#60a5fa; font-size:0.8rem; margin:0;">🤖 100% Agent Processed</p>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_col2:
        # Determine color for success rate
        s_rate = metrics.get("success_rate", 100.0)
        s_color = "#34d399" if s_rate > 90 else ("#fbbf24" if s_rate > 80 else "#f87171")
        
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <p style="color:#9ca3af; margin-bottom:0.1rem; font-size:0.9rem;">Workflow Success Rate</p>
            <h2 style="font-size:2.5rem; margin:0; color:{s_color};">{s_rate}%</h2>
            <p style="color:#34d399; font-size:0.8rem; margin:0;">🎯 QA Supervisor Approved</p>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_col3:
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <p style="color:#9ca3af; margin-bottom:0.1rem; font-size:0.9rem;">Avg Resolution Time</p>
            <h2 style="font-size:2.5rem; margin:0; color:#a78bfa;">{metrics.get("avg_resolution_time", 0.0)}s</h2>
            <p style="color:#a78bfa; font-size:0.8rem; margin:0;">⚡ Live Pipeline Latency</p>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_col4:
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <p style="color:#9ca3af; margin-bottom:0.1rem; font-size:0.9rem;">Customer Satisfaction (CSAT)</p>
            <h2 style="font-size:2.5rem; margin:0; color:#f472b6;">⭐ {metrics.get("csat_score", 0.0)}/5.0</h2>
            <p style="color:#f472b6; font-size:0.8rem; margin:0;">🗣️ Based on {metrics.get("csat_votes", 0)} votes</p>
        </div>
        """, unsafe_allow_html=True)

    # 3. Charts Section
    chart_col1, chart_col2 = st.columns([5, 7])
    
    with chart_col1:
        st.write("**Ticket Classification Distribution**")
        cat_data = metrics.get("tickets_by_category", {})
        
        if cat_data:
            df_cat = pd.DataFrame(list(cat_data.items()), columns=["Category", "Count"])
            
            # Premium color palette matching styling tokens
            colors = ["#6366f1", "#a855f7", "#ec4899", "#14b8a6"]
            
            fig_donut = px.pie(
                df_cat, 
                values="Count", 
                names="Category", 
                hole=0.45,
                color_discrete_sequence=colors
            )
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f3f4f6"),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                margin=dict(t=10, b=50, l=10, r=10),
                height=320
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("No classification data recorded yet.")
            
    with chart_col2:
        st.write("**Historical Ticket Volume & Core Success Rates**")
        history = metrics.get("history", [])
        
        if history:
            df_hist = pd.DataFrame(history)
            
            # Dual-axis graph: volume as bar, success rate as line
            fig_hist = go.Figure()
            
            # 1. Bar chart for volume
            fig_hist.add_trace(go.Bar(
                x=df_hist["day"],
                y=df_hist["tickets"],
                name="Ticket Volume",
                marker_color="rgba(99, 102, 241, 0.65)",
                yaxis="y"
            ))
            
            # 2. Line chart for success rate
            fig_hist.add_trace(go.Scatter(
                x=df_hist["day"],
                y=df_hist["success_rate"],
                name="Success Rate (%)",
                mode="lines+markers",
                line=dict(color="#10b981", width=3),
                marker=dict(size=8),
                yaxis="y2"
            ))
            
            # Configure dual axes layout
            fig_hist.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f3f4f6"),
                height=320,
                margin=dict(t=20, b=10, l=10, r=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
                yaxis=dict(
                    title=dict(
                        text="Volume (Tickets)",
                        font=dict(color="#818cf8")
                    ),
                    tickfont=dict(color="#818cf8"),
                    gridcolor="rgba(255,255,255,0.05)"
                ),
                yaxis2=dict(
                    title=dict(
                        text="Success Rate (%)",
                        font=dict(color="#10b981")
                    ),
                    tickfont=dict(color="#10b981"),
                    overlaying="y",
                    side="right",
                    range=[50, 105],
                    showgrid=False
                )
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("No historical trends recorded.")

# Footer info
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#6b7280; font-size:0.85rem;'>"
    "Agentic Customer Support System — Built with Python, LangGraph, FastAPI, and Streamlit. "
    "Created for training freshers and workflow demonstrations."
    "</p>",
    unsafe_allow_html=True
)
