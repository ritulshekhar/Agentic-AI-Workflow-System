# Architecture Explanation for Freshers

Welcome! If you are new to AI engineering, Multi-Agent Systems, or Python backend development, this document will explain how our Customer Support System is structured using simple analogies.

---

## 1. What is a Multi-Agent System?

Think of a traditional computer program as an **assembly line**. Data goes in, goes straight down the line, and comes out the other end.

A **Multi-Agent System** is like an **office department**. Instead of one giant computer code doing everything, we break the job into small, specific roles:
*   **The Mailroom Clerk (Classification Agent)**: Looks at the envelope, decides if it's about money, shipping, or technical issues, and routes it.
*   **The Researcher (Retrieval Agent)**: Goes to the filing cabinet (our local text files) and finds the exact rule sheet for that category.
*   **The Draft Writer (Response Agent)**: Takes the customer's letter and the rule sheets and writes a polite response draft.
*   **The Manager (Supervisor Agent)**: Proofreads the draft. If it's perfect, they mail it (Approve). If it's missing details or rude, they write feedback and send it back to the Writer (Response Agent) to redo.

---

## 2. Understanding LangGraph Concepts

LangGraph is the library we use to coordinate this "office department." It operates like a board game:

### A. The State (The Clipboard)
Imagine a clipboard that gets passed from desk to desk in our office. Everyone writes their updates on it:
*   The mail clerk writes the *category*.
*   The researcher clips the *retrieved policy paragraphs*.
*   The writer writes the *email draft*.
*   The manager writes the *approval status* and *feedback*.
In our code, this clipboard is called the `AgentState`.

### B. Nodes (The Desks)
Each desk (or node) represents a specific agent's workspace. A node is simply a Python function that reads the clipboard (`AgentState`), does some work, and writes its updates back to the clipboard.

### C. Edges (The Hallways)
Edges connect the desks, defining the order of movement:
*   **Standard Edge**: Direct path (e.g., Mailroom clerk *always* passes the clipboard to the Researcher next).
*   **Conditional Edge**: A decision point. The manager looks at the clipboard. If approved, they walk to the exit. If rejected, they walk back to the Writer's desk.

---

## 3. The Backend (FastAPI) vs Frontend (Streamlit)

Our application is split into two halves:

```
┌─────────────────────────────────┐
│     Streamlit Frontend          │  ◄── (Web UI, Dashboard, Input form)
└────────┬───────────────▲────────┘
         │               │
         │ (HTTP Post)   │ (JSON Results)
         ▼               │
┌────────────────────────┴────────┐
│     FastAPI Backend             │  ◄── (REST Endpoints: /api/solve-ticket)
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│     LangGraph Workflow          │  ◄── (The 4 agents: Classifier,
└─────────────────────────────────┘      Retriever, Responder, Supervisor)
```

1.  **FastAPI (The Engine)**: A lightweight Python web server. It runs in the background. It takes requests via URLs (endpoints) like `/api/solve-ticket`, runs the LangGraph agent workflow, and sends the answer back as clean JSON data. It also keeps track of business statistics in memory.
2.  **Streamlit (The Dashboard & UI)**: A library for building web pages in python. It creates the input box, visualizes each agent's thoughts as they execute, and renders Plotly charts showing operational success rates and customer satisfaction.

---

## 4. How the "Dual-Mode Standalone" Design Works

Normally, you need to run the FastAPI backend in one terminal tab and the Streamlit frontend in a second terminal tab. This can be complex for a recruiter to set up or difficult to host for free online.

To solve this, we built a **Dual-Driver engine**:
*   When Streamlit starts, it automatically sends a ping to see if FastAPI is running on your machine.
*   **Mode A (FastAPI Connection)**: If FastAPI is active, Streamlit connects to it using web API requests (`http://localhost:8000`).
*   **Mode B (In-Process Fallback)**: If FastAPI is offline, Streamlit bypasses the web requests and **imports the agent code directly** inside the frontend process. It runs the entire agent workflow and updates the charts locally in the browser's session memory.
This makes the app **100% standalone**, allowing you to host the entire system on free hosting websites (like Streamlit Community Cloud) with a single click!
