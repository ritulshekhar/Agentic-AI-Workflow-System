# AgentFlow: Agentic AI Customer Support System

A beginner-friendly, visually stunning Multi-Agent Workflow System designed to automate customer support ticket handling. This project uses **Python**, **LangChain**, **LangGraph**, **FastAPI**, and **Streamlit** to coordinate specialized agents, perform local knowledge base searches, and provide a visual operator console with a live operations dashboard.

---

## 🚀 Key Features

*   **Stateful Orchestration with LangGraph**: Coordinates 4 specialized agents (Classification, Retrieval, Response, and Supervisor) using graph-based loops.
*   **Self-Correcting Routing Loops**: The Supervisor Agent audits draft replies. If quality checks fail, the workflow loops back to the Response Agent with feedback to refine the draft.
*   **Dual-Driver Architecture**: Can run as a distributed system (Streamlit UI + separate FastAPI backend service) or as a standalone app (Streamlit running the graph in-process). This makes it easy to host online for free (e.g. on Streamlit Cloud).
*   **Zero-Dependency Mock LLM Mode**: Includes a simulated agent execution mode that runs instantly without requiring API keys or payment setups—perfect for quick demos.
*   **Active LLM Mode**: Compatible with OpenAI, Groq, OpenRouter, or any OpenAI-compatible API endpoint.
*   **Mock Operations Dashboard**: Uses interactive Plotly charts (donut and dual-axis volume/success timeline) and real-time KPI card styles to display operational metrics.
*   **Preloaded Query Templates**: Allows clicking template queries (e.g. urgent returns, password resets) to instantly autofill and demonstrate workflow pathways.

---

## 📐 Multi-Agent Workflow Architecture

```mermaid
graph TD
    Start([Customer Query]) --> Classifier[🧭 Classification Agent]
    Classifier --> |Refund/Shipping/Tech/General| Retriever[🔍 Retrieval Agent]
    Retriever --> |Look up text files| Response[✍️ Response Agent]
    Response --> Supervisor[⚖️ Supervisor Agent]
    Supervisor --> |Valid? Yes| End([Approved Response])
    Supervisor --> |Valid? No (Max 2 Retries)| Response
```

### The 4 Agents:
1.  **Classification Agent**: Analyzes customer ticket text to route it to the appropriate department.
2.  **Retrieval Agent**: Searches local text policy files (`knowledge_base/`) using keyword ranking.
3.  **Response Agent**: Drafts the customer reply email based on retrieved facts and previous supervisor feedback.
4.  **Supervisor Agent**: Quality-assures the response against retrieved facts and tone guidelines.

---

## 📂 Project Structure

```
├── requirements.txt            # Python dependencies (LangGraph, FastAPI, Streamlit, etc.)
├── knowledge_base/             # Local text files serving as the knowledge base
│   ├── refund_policy.txt
│   ├── shipping_info.txt
│   └── technical_support.txt
├── backend/
│   ├── __init__.py
│   ├── retriever.py            # Custom plain-text search engine
│   ├── agents.py               # LangGraph workflow and LangChain agent nodes
│   └── main.py                 # FastAPI server and operations metrics database
├── frontend/
│   └── app.py                  # Streamlit application UI and Plotly Dashboard
└── project_docs/               # Educational resources
    ├── project_explanation.md   # Complete codebase walkthrough
    ├── fresher_architecture.md # Conceptual architecture guide for freshers
    └── interview_qa.md         # Prep guide containing agentic QA
```

---

## ⚡ Quick Start Guide

### 1. Installation
Clone this repository to your computer and navigate to the project folder. Run:

```bash
pip install -r requirements.txt
```

### 2. Standalone Mode (In-Process) - Easiest & Best for Streamlit Cloud
You do not need to run a backend server. The Streamlit app will import the agent workflow directly and store operation metrics in browser memory.

Run:
```bash
streamlit run frontend/app.py
```
*Open your browser to `http://localhost:8501` to use the application.*

### 3. Distributed Service Mode (FastAPI Backend + Streamlit UI)
To run the project as a full API service and web app, open two terminal windows:

*   **Terminal 1 (Backend API Service)**:
    ```bash
    python backend/main.py
    ```
    *Starts the FastAPI server on `http://127.0.0.1:8000`.*

*   **Terminal 2 (Frontend Interface)**:
    ```bash
    streamlit run frontend/app.py
    ```
    *Starts the Streamlit interface, which automatically connects to the active backend API.*

---

## 🛠️ Running with Live OpenAI-Compatible LLMs

By default, the sidebar has **"Enable Mock LLM Mode"** toggled **ON** to run without API keys. To connect actual LLM APIs:
1.  Open the Streamlit app sidebar.
2.  Toggle **"Enable Mock LLM Mode"** to **OFF**.
3.  Input your **API Key** (e.g. OpenAI key, Groq key, or OpenRouter key).
4.  Optionally customize the **Base URL** (e.g. `https://api.groq.com/openai/v1` for Groq) and **Model Name** (e.g. `llama3-8b-8192` or `gpt-3.5-turbo`).
5.  Submit a ticket query to run the live agents.

---

## 🎓 Educational Resource Materials
We have created dedicated learning documents for placements and learning:
*   Read [project_explanation.md](file:///Users/harsh/Desktop/Agentic%20AI%20workflow%20System/project_docs/project_explanation.md) for a line-by-line concept breakdown.
*   Read [fresher_architecture.md](file:///Users/harsh/Desktop/Agentic%20AI%20workflow%20System/project_docs/fresher_architecture.md) for a simple explanation of LangGraph states, nodes, and edges.
*   Read [interview_qa.md](file:///Users/harsh/Desktop/Agentic%20AI%20workflow%20System/project_docs/interview_qa.md) to practice agentic AI questions and answers.
