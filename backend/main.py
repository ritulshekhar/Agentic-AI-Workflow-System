import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Local Imports
from backend.agents import run_support_workflow

# =====================================================================
# 1. FastAPI Application Setup
# =====================================================================
app = FastAPI(
    title="Agentic AI Customer Support System Backend",
    description="A FastAPI backend orchestrating multiple AI agents via LangGraph to solve tickets.",
    version="1.0.0"
)

# Enable CORS so Streamlit (running on another port) can fetch statistics and post tickets
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development and online demonstrations
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# 2. In-Memory Mock Database for Business Metrics
# =====================================================================
# We pre-populate this with high-quality mock data so the dashboard is immediately rich and visual.
DEFAULT_METRICS = {
    "total_tickets": 142,
    "success_count": 136,
    "failure_count": 6,
    "success_rate": 95.7,
    "avg_resolution_time": 4.2,  # in seconds
    "total_resolution_time": 142 * 4.2,
    "csat_score": 4.8, # Client Satisfaction Score (out of 5.0)
    "csat_votes": 85,
    "tickets_by_category": {
        "Refunds & Returns": 48,
        "Shipping & Delivery": 54,
        "Technical Support & Accounts": 32,
        "General Queries": 8
    },
    # Historical volume data for a line chart (last 7 days)
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

# The active metrics store (resets to defaults)
metrics_db = dict(DEFAULT_METRICS)

# =====================================================================
# 3. Pydantic Models for Input Validation
# =====================================================================
class LLMConfigInput(BaseModel):
    mock_mode: bool = Field(default=True, description="Toggle between Mock LLM execution and live APIs")
    api_key: Optional[str] = Field(default=None, description="OpenAI or OpenAI-compatible API Key")
    base_url: Optional[str] = Field(default=None, description="OpenAI-compatible Base URL")
    model_name: Optional[str] = Field(default=None, description="Model identifier for completion")

class SolveTicketRequest(BaseModel):
    query: str = Field(..., description="The customer's help request message")
    llm_config: LLMConfigInput = Field(default_factory=LLMConfigInput)

# =====================================================================
# 4. API Endpoints
# =====================================================================

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Agentic Customer Support API. Use POST /api/solve-ticket to process queries.",
        "docs_url": "/docs"
    }

@app.post("/api/solve-ticket")
def solve_ticket(request: SolveTicketRequest):
    """
    Submits a customer support ticket to the multi-agent system.
    Processes the request through LangGraph, logs stats, updates metrics, and returns the result.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Ticket query cannot be empty.")
    
    start_time = time.time()
    
    try:
        # Convert Pydantic config inputs to dict
        config_dict = request.llm_config.dict()
        
        # Execute LangGraph workflow
        result = run_support_workflow(query=request.query, llm_config=config_dict)
        
        elapsed_time = round(time.time() - start_time, 2)
        
        # Update active database metrics
        metrics_db["total_tickets"] += 1
        
        # Update category count
        category = result.get("category", "General Queries")
        if category not in metrics_db["tickets_by_category"]:
            metrics_db["tickets_by_category"][category] = 0
        metrics_db["tickets_by_category"][category] += 1
        
        # Update success/failure statistics
        success = result.get("success", True)
        if success:
            metrics_db["success_count"] += 1
        else:
            metrics_db["failure_count"] += 1
            
        # Update success rate float
        metrics_db["success_rate"] = round(
            (metrics_db["success_count"] / metrics_db["total_tickets"]) * 100, 1
        )
        
        # Update average resolution time
        metrics_db["total_resolution_time"] += elapsed_time
        metrics_db["avg_resolution_time"] = round(
            metrics_db["total_resolution_time"] / metrics_db["total_tickets"], 2
        )
        
        # Add to client satisfaction voting pool (randomized realistic voter satisfaction for the demo)
        # e.g., standard workflow rates 4-5 stars, retries rate slightly lower, failures rate 1 star.
        if success:
            retry_count = result.get("retry_count", 0)
            score = 5 if retry_count == 0 else 4
        else:
            score = 2
            
        metrics_db["csat_votes"] += 1
        metrics_db["csat_score"] = round(
            ((metrics_db["csat_score"] * (metrics_db["csat_votes"] - 1)) + score) / metrics_db["csat_votes"], 2
        )
        
        # Append elapsed time info to return payload
        result["resolution_time_seconds"] = elapsed_time
        return result
        
    except Exception as e:
        # Update failures
        metrics_db["total_tickets"] += 1
        metrics_db["failure_count"] += 1
        metrics_db["success_rate"] = round(
            (metrics_db["success_count"] / metrics_db["total_tickets"]) * 100, 1
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during workflow orchestration: {str(e)}"
        )

@app.get("/api/metrics")
def get_metrics():
    """
    Returns aggregated customer support business metrics.
    """
    return metrics_db

@app.post("/api/metrics/reset")
def reset_metrics():
    """
    Resets the dashboard metrics to their pre-populated state.
    """
    global metrics_db
    metrics_db = dict(DEFAULT_METRICS)
    # Ensure nested elements are copies
    metrics_db["tickets_by_category"] = dict(DEFAULT_METRICS["tickets_by_category"])
    metrics_db["history"] = list(DEFAULT_METRICS["history"])
    return {"message": "Metrics reset to initial mock dataset."}

# Standard run procedure
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
