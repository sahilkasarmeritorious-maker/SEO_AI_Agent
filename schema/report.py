from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import json

class SEOFinding(BaseModel):
    """Individual SEO finding."""
    finding: str = Field(..., description="What was found")
    impact: str = Field(..., description="high, medium, or low")

class SEOWeakness(BaseModel):
    """SEO weakness with recommendation."""
    finding: str = Field(..., description="What's wrong")
    impact: str = Field(..., description="high, medium, or low")
    recommendation: str = Field(..., description="How to fix it")

class SEOMissingElement(BaseModel):
    """Missing SEO element."""
    element: str = Field(..., description="What's missing")
    importance: str = Field(..., description="critical, high, medium, or low")
    why: str = Field(..., description="Why it matters")

class SEORecommendation(BaseModel):
    """SEO recommendation."""
    priority: str = Field(..., description="high, medium, or low")
    action: str = Field(..., description="What to do")
    expected_benefit: str = Field(..., description="Expected outcome")

class SEOReport(BaseModel):
    """Complete SEO analysis report."""
    url: str
    overall_score: int = Field(..., ge=0, le=100, description="Overall SEO score 0-100")
    
    strengths: List[SEOFinding] = Field(default_factory=list)
    weaknesses: List[SEOWeakness] = Field(default_factory=list)
    missing_elements: List[SEOMissingElement] = Field(default_factory=list)
    recommendations: List[SEORecommendation] = Field(default_factory=list)
    
    timestamp: datetime = Field(default_factory=datetime.now)
    processing_time_ms: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "overall_score": 72,
                "strengths": [{"finding": "Single H1 present", "impact": "high"}],
                "weaknesses": [{"finding": "Missing meta description", "impact": "high", "recommendation": "Add 120-160 character description"}],
                "missing_elements": [],
                "recommendations": []
            }
        }
    
    def to_json(self) -> str:
        """Convert to formatted JSON string."""
        return json.dumps(self.dict(), indent=2, default=str)
    
    def to_markdown(self) -> str:
        """Convert to markdown format."""
        md = f"""# SEO Analysis Report

**URL:** {self.url}  
**Overall Score:** {self.overall_score}/100  
**Analyzed:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

---

## 💪 Strengths ({len(self.strengths)})

"""
        for s in self.strengths:
            md += f"- **{s.finding}** (Impact: {s.impact})\n"
        
        md += f"""
## ⚠️ Weaknesses ({len(self.weaknesses)})

"""
        for w in self.weaknesses:
            md += f"- **{w.finding}** (Impact: {w.impact})\n"
            md += f"  → Recommendation: {w.recommendation}\n\n"
        
        md += f"""
## ❌ Missing Elements ({len(self.missing_elements)})

"""
        for m in self.missing_elements:
            md += f"- **{m.element}** (Importance: {m.importance})\n"
            md += f"  → Why: {m.why}\n\n"
        
        md += f"""
## 📝 Recommendations ({len(self.recommendations)})

"""
        for r in self.recommendations:
            md += f"- [{r.priority.upper()}] {r.action}\n"
            md += f"  → Expected benefit: {r.expected_benefit}\n\n"
        
        return md