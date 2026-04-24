import json
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Analysis
from agents.seo_agent import SEOAgent  # Now async!
from agents.ux_agent import UXAgent  # Now async!
from app.core.logging import logger
from app.services.chroma_service import chroma_service  # ADD THIS


class AnalysisService:
    @staticmethod
    async def create_analysis(db: AsyncSession, user_id: int, url: str):
        """Create analysis record in DB."""
        analysis = Analysis(
            user_id=user_id,
            url=url,
            analysis_id=None,
            status="pending"
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        
        analysis.analysis_id = str(analysis.id)
        await db.commit()
        
        #  Start background analysis
        asyncio.create_task(AnalysisService._run_analysis(analysis.id, url, user_id))
        
        logger.info(f" Analysis {analysis.id} queued for background processing")
        return analysis
    
    @staticmethod
    async def _run_analysis(analysis_id: int, url: str, user_id: int):  #  ADD user_id
        """Run both SEO and UX analysis in background."""
        from app.db.session import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            try:
                logger.info(f" Starting analysis {analysis_id} for {url}")
                
                result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
                analysis = result.scalars().first()
                
                if not analysis:
                    logger.error(f" Analysis {analysis_id} not found")
                    return
                
                analysis.status = "processing"
                await db.commit()
                logger.info(f" Analysis {analysis_id} now processing...")
                
                #  Run agents asynchronously
                logger.info(f" Running SEO Agent for {url}")
                seo_agent = SEOAgent()
                seo_report = await seo_agent.analyze(url)  #  await async agent
                logger.info(f" SEO Agent completed: {seo_report.overall_score}/100")
                
                logger.info(f" Running UX Agent for {url}")
                ux_agent = UXAgent()
                ux_report = await ux_agent.analyze(url)  #  await async agent
                logger.info(f" UX Agent completed: {ux_report.overall_score}/100")
                
                # Save results
                analysis.seo_overall_score = seo_report.overall_score
                analysis.seo_strengths = json.dumps([s.dict() if hasattr(s, 'dict') else s for s in seo_report.strengths])
                analysis.seo_weaknesses = json.dumps([w.dict() if hasattr(w, 'dict') else w for w in seo_report.weaknesses])
                analysis.seo_missing_elements = json.dumps([m.dict() if hasattr(m, 'dict') else m for m in seo_report.missing_elements])
                analysis.seo_recommendations = json.dumps([r.dict() if hasattr(r, 'dict') else r for r in seo_report.recommendations])
                
                analysis.ux_overall_score = ux_report.overall_score
                analysis.ux_strengths = json.dumps([s.dict() if hasattr(s, 'dict') else s for s in ux_report.strengths])
                analysis.ux_weaknesses = json.dumps([w.dict() if hasattr(w, 'dict') else w for w in ux_report.weaknesses])
                analysis.ux_missing_elements = json.dumps([m.dict() if hasattr(m, 'dict') else m for m in ux_report.missing_elements])
                analysis.ux_recommendations = json.dumps([r.dict() if hasattr(r, 'dict') else r for r in ux_report.recommendations])
                
                analysis.status = "completed"
                analysis.processing_time_ms = int(seo_report.processing_time_ms + ux_report.processing_time_ms)
                analysis.completed_at = datetime.utcnow()
                analysis.error = None
                
                await db.commit()
                logger.info(f" Analysis {analysis_id} COMPLETED! SEO: {seo_report.overall_score}, UX: {ux_report.overall_score}")
                
                # NEW: Save to Chroma (async)
                try:
                    logger.info(f" Saving analysis {analysis_id} to Chroma for user {user_id}...")
                    await chroma_service.save_analysis_to_chroma(user_id, analysis)
                    logger.info(f" Analysis {analysis_id} saved to Chroma successfully!")
                except Exception as chroma_error:
                    logger.error(f"  Failed to save to Chroma: {str(chroma_error)}")
                    # Don't fail entire analysis if Chroma fails
                    pass
                
            except Exception as e:
                logger.error(f" Analysis {analysis_id} FAILED: {str(e)}", exc_info=True)
                try:
                    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
                    analysis = result.scalars().first()
                    if analysis:
                        analysis.status = "failed"
                        analysis.error = str(e)
                        analysis.completed_at = datetime.utcnow()
                        await db.commit()
                except Exception as db_error:
                    logger.error(f" Failed to update analysis error status: {str(db_error)}")
    
    @staticmethod
    async def get_user_analyses(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 10):
        """Get user's analysis history."""
        result = await db.execute(
            select(Analysis)
            .where(Analysis.user_id == user_id)
            .order_by(Analysis.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_analysis_by_id(db: AsyncSession, analysis_id: int):
        """Get single analysis."""
        result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
        return result.scalars().first()