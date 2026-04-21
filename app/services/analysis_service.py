import json
import uuid
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Analysis
from agents.seo_agent import SEOAgent
from app.core.logging import logger


class AnalysisService:
    @staticmethod
    def create_analysis(db: Session, user_id: int, url: str):
        """Create analysis record in DB."""
        job_id = str(uuid.uuid4())
        
        analysis = Analysis(
            user_id=user_id,
            url=url,
            job_id=job_id,
            status="pending"
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Start background analysis
        thread = threading.Thread(
            target=AnalysisService._run_analysis,
            args=(db, analysis.id, url),
            daemon=True
        )
        thread.start()
        
        return analysis
    
    @staticmethod
    def _run_analysis(db: Session, analysis_id: int, url: str):
        """Run SEO analysis in background."""
        try:
            logger.info(f"Starting analysis {analysis_id} for {url}")
            
            # Update status
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            analysis.status = "processing"
            db.commit()
            
            # Run agent
            agent = SEOAgent()
            report = agent.analyze(url)
            
            # Update with results
            analysis.status = "completed"
            analysis.overall_score = report.overall_score
            analysis.strengths = json.dumps([s.dict() for s in report.strengths])
            analysis.weaknesses = json.dumps([w.dict() for w in report.weaknesses])
            analysis.missing_elements = json.dumps([m.dict() for m in report.missing_elements])
            analysis.recommendations = json.dumps([r.dict() for r in report.recommendations])
            analysis.processing_time_ms = int(report.processing_time_ms)
            analysis.completed_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"Analysis {analysis_id} completed with score {report.overall_score}")
            
        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed: {str(e)}")
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            analysis.status = "failed"
            analysis.error = str(e)
            analysis.completed_at = datetime.utcnow()
            db.commit()
    
    @staticmethod
    def get_user_analyses(db: Session, user_id: int, skip: int = 0, limit: int = 10):
        """Get user's analysis history."""
        return db.query(Analysis).filter(
            Analysis.user_id == user_id
        ).order_by(Analysis.created_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_analysis_by_id(db: Session, analysis_id: int):
        """Get single analysis."""
        return db.query(Analysis).filter(Analysis.id == analysis_id).first()