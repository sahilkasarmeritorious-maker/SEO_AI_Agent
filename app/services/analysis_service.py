import json
import uuid
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Analysis
from agents.seo_agent import SEOAgent
from agents.ux_agent import UXAgent
from app.core.logging import logger


class AnalysisService:
    @staticmethod
    def create_analysis(db: Session, user_id: int, url: str):
        """Create analysis record in DB."""
        analysis = Analysis(
            user_id=user_id,
            url=url,
            analysis_id=None,  # Will use auto-increment ID
            status="pending"
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Set analysis_id to the auto-generated ID
        analysis.analysis_id = str(analysis.id)
        db.commit()

        # Start background analysis - DON'T pass db!
        thread = threading.Thread(
            target=AnalysisService._run_analysis,
            args=(analysis.id, url),  # Only pass ID and URL
            daemon=True
        )
        thread.start()

        return analysis
    
    @staticmethod
    def _run_analysis(analysis_id: int, url: str):
        """Run both SEO and UX analysis in background."""
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            logger.info(f"Starting analysis {analysis_id} for {url}")

            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            analysis.status = "processing"
            db.commit()

            # Run both agents
            seo_agent = SEOAgent()
            ux_agent = UXAgent()

            seo_report = seo_agent.analyze(url)
            ux_report = ux_agent.analyze(url)

            # Save SEO results
            analysis.status = "completed"
            analysis.seo_overall_score = seo_report.overall_score
            analysis.seo_strengths = json.dumps([s.dict() if hasattr(s, 'dict') else s for s in seo_report.strengths])
            analysis.seo_weaknesses = json.dumps([w.dict() if hasattr(w, 'dict') else w for w in seo_report.weaknesses])
            analysis.seo_missing_elements = json.dumps([m.dict() if hasattr(m, 'dict') else m for m in seo_report.missing_elements])
            analysis.seo_recommendations = json.dumps([r.dict() if hasattr(r, 'dict') else r for r in seo_report.recommendations])

            # Save UX results
            analysis.ux_overall_score = ux_report.overall_score
            analysis.ux_strengths = json.dumps([s.dict() if hasattr(s, 'dict') else s for s in ux_report.strengths])
            analysis.ux_weaknesses = json.dumps([w.dict() if hasattr(w, 'dict') else w for w in ux_report.weaknesses])
            analysis.ux_missing_elements = json.dumps([m.dict() if hasattr(m, 'dict') else m for m in ux_report.missing_elements])
            analysis.ux_recommendations = json.dumps([r.dict() if hasattr(r, 'dict') else r for r in ux_report.recommendations])

            analysis.processing_time_ms = int(seo_report.processing_time_ms + ux_report.processing_time_ms)
            analysis.completed_at = datetime.utcnow()

            db.commit()
            logger.info(f"Analysis {analysis_id} completed: SEO {seo_report.overall_score}, UX {ux_report.overall_score}")

        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed: {str(e)}")
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            analysis.status = "failed"
            analysis.error = str(e)
            analysis.completed_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()
    
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