import sys
from pathlib import Path
from urllib.parse import urlparse
from agents.seo_agent import SEOAgent

def get_website_name_from_url(url: str) -> str:
    """Extract website name from URL for filename."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")  # Remove www. prefix
    domain = domain.replace(".", "_")  # Replace dots with underscores
    return domain

def test_seo_agent():
    """Test SEO agent on a real website."""
    
    print(f"\n{'='*60}")
    print("SEO AGENT TEST")
    print(f"{'='*60}")
    
    # Initialize agent
    try:
        agent = SEOAgent()
        print("✅ Agent initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False
    
    # Test website
    test_url = "https://meritorious.global/"
    
    try:
        # Run analysis
        report = agent.analyze(test_url)
        
        # Display results
        print(f"\n{'='*60}")
        print("RESULTS")
        print(f"{'='*60}")
        
        print(f"\n📊 Score: {report.overall_score}/100")
        print(f"💪 Strengths: {len(report.strengths)}")
        print(f"⚠️  Weaknesses: {len(report.weaknesses)}")
        print(f"❌ Missing: {len(report.missing_elements)}")
        print(f"📝 Recommendations: {len(report.recommendations)}")
        
        # Show details
        print(f"\n{'─'*60}")
        print("DETAILED REPORT (JSON)")
        print(f"{'─'*60}")
        print(report.to_json())
        
        # Create Reports folder
        reports_dir = Path("Reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Get website name for filename
        website_name = get_website_name_from_url(test_url)
        
        # Save JSON report
        json_path = reports_dir / f"{website_name}_seo_report.json"
        with open(json_path, "w") as f:
            f.write(report.to_json())
        print(f"\n📁 Report saved to: {json_path}")
        
        # Save Markdown report
        md_path = reports_dir / f"{website_name}_seo_report.md"
        with open(md_path, "w") as f:
            f.write(report.to_markdown())
        
        print(f"📁 Markdown saved to: {md_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_seo_agent()
    sys.exit(0 if success else 1)