import uuid
import threading
import json
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.seo_agent import SEOAgent
from schema.report import SEOReport

# ═══════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="🔍 Website Analysis API",
    description="Analyze websites using AI agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════

class AnalysisRequest(BaseModel):
    """Request to analyze a website."""
    url: str = Field(..., description="Website URL to analyze", example="https://example.com")

class JobResponse(BaseModel):
    """Response when job is submitted."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status: pending, processing, completed, failed")
    message: str = Field(..., description="Status message")

class JobStatus(BaseModel):
    """Status of analysis job."""
    job_id: str
    status: str
    url: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

# ═══════════════════════════════════════════════════════════════
# IN-MEMORY JOB STORAGE
# ═══════════════════════════════════════════════════════════════

jobs: Dict[str, Dict[str, Any]] = {}

# ═══════════════════════════════════════════════════════════════
# ANALYSIS ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.post(
    "/api/analyze",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit URL for Analysis"
)
def submit_analysis(request: AnalysisRequest):
    """Submit a website URL for analysis. Returns job_id to track progress."""
    
    # Validate URL
    if not request.url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL cannot be empty"
        )
    
    if not request.url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://"
        )
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Create job entry
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "url": request.url,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result": None,
        "error": None
    }
    
    print(f"\n📝 New job: {job_id}")
    print(f"   URL: {request.url}")
    
    # Start analysis in background thread
    thread = threading.Thread(
        target=_run_analysis_background,
        args=(job_id, request.url),
        daemon=True
    )
    thread.start()
    
    return JobResponse(
        job_id=job_id,
        status="processing",
        message=f"Analysis started. Use GET /api/results/{job_id} to check status"
    )

@app.get(
    "/api/results/{job_id}",
    response_model=JobStatus,
    summary="Get Analysis Results"
)
def get_results(job_id: str):
    """Get analysis results by job_id. Returns status and results when completed."""
    
    if job_id not in jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    
    job = jobs[job_id]
    
    return JobStatus(
        job_id=job["job_id"],
        status=job["status"],
        url=job["url"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
        error=job["error"],
        result=job["result"]
    )

# ═══════════════════════════════════════════════════════════════
# BACKGROUND TASK
# ═══════════════════════════════════════════════════════════════

def _run_analysis_background(job_id: str, url: str):
    """Run SEO analysis in background thread."""
    try:
        print(f"🚀 Starting analysis: {url}")
        jobs[job_id]["status"] = "processing"
        
        # Initialize and run agent
        agent = SEOAgent()
        report: SEOReport = agent.analyze(url)
        
        # Convert report to dict
        result_dict = {
            "url": report.url,
            "overall_score": report.overall_score,
            "timestamp": report.timestamp.isoformat(),
            "processing_time_ms": report.processing_time_ms,
            "strengths": [
                {"finding": s.finding, "impact": s.impact}
                for s in report.strengths
            ],
            "weaknesses": [
                {"finding": w.finding, "impact": w.impact, "recommendation": w.recommendation}
                for w in report.weaknesses
            ],
            "missing_elements": [
                {"element": m.element, "importance": m.importance, "why": m.why}
                for m in report.missing_elements
            ],
            "recommendations": [
                {"priority": r.priority, "action": r.action, "expected_benefit": r.expected_benefit}
                for r in report.recommendations
            ]
        }
        
        # Update job with results
        jobs[job_id]["result"] = result_dict
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        print(f"✅ Job completed: {job_id}")
        print(f"   Score: {report.overall_score}/100")
        
    except Exception as e:
        print(f"❌ Job failed: {job_id}")
        print(f"   Error: {str(e)}")
        
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

# ═══════════════════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🚀 Website Analysis API")
    print("="*60)
    print("📍 Server: http://localhost:8000")
    print("📚 Swagger UI: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )