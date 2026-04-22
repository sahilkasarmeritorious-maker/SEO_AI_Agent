import sys
from pathlib import Path
from urllib.parse import urlparse
from agents.seo_agent import SEOAgent
from agents.ux_agent import UXAgent

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


def test_ux_agent():
    """Test UX agent on a real website."""
    
    print(f"\n{'='*60}")
    print("UX AGENT TEST")
    print(f"{'='*60}")
    
    # Initialize agent
    try:
        agent = UXAgent()
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
        json_path = reports_dir / f"{website_name}_ux_report.json"
        with open(json_path, "w") as f:
            f.write(report.to_json())
        print(f"\n📁 Report saved to: {json_path}")
        
        # Save Markdown report
        md_path = reports_dir / f"{website_name}_ux_report.md"
        with open(md_path, "w") as f:
            f.write(report.to_markdown())
        
        print(f"📁 Markdown saved to: {md_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_both_agents():
    """Test both SEO and UX agents together."""
    
    print(f"\n{'='*60}")
    print("BOTH AGENTS TEST (SEO + UX)")
    print(f"{'='*60}")
    
    # Initialize agents
    try:
        seo_agent = SEOAgent()
        ux_agent = UXAgent()
        print("✅ Both agents initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False
    
    # Test website
    test_url = "https://meritorious.global/"
    
    try:
        # Run analysis
        print(f"\n🔄 Running both agents in parallel...")
        seo_report = seo_agent.analyze(test_url)
        ux_report = ux_agent.analyze(test_url)
        
        # Display results
        print(f"\n{'='*60}")
        print("COMBINED RESULTS")
        print(f"{'='*60}")
        
        print(f"\n📊 SEO Score: {seo_report.overall_score}/100")
        print(f"📊 UX Score: {ux_report.overall_score}/100")
        print(f"⏱️  Total Processing Time: {seo_report.processing_time_ms + ux_report.processing_time_ms:.0f}ms")
        
        # Create Reports folder
        reports_dir = Path("Reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Get website name for filename
        website_name = get_website_name_from_url(test_url)
        
        # Combined report
        combined_report = {
            "url": test_url,
            "seo": {
                "score": seo_report.overall_score,
                "strengths": [s.dict() if hasattr(s, 'dict') else s for s in seo_report.strengths],
                "weaknesses": [w.dict() if hasattr(w, 'dict') else w for w in seo_report.weaknesses],
                "missing_elements": [m.dict() if hasattr(m, 'dict') else m for m in seo_report.missing_elements],
                "recommendations": [r.dict() if hasattr(r, 'dict') else r for r in seo_report.recommendations]
            },
            "ux": {
                "score": ux_report.overall_score,
                "strengths": [s.dict() if hasattr(s, 'dict') else s for s in ux_report.strengths],
                "weaknesses": [w.dict() if hasattr(w, 'dict') else w for w in ux_report.weaknesses],
                "missing_elements": [m.dict() if hasattr(m, 'dict') else m for m in ux_report.missing_elements],
                "recommendations": [r.dict() if hasattr(r, 'dict') else r for r in ux_report.recommendations]
            },
            "processing_time_ms": seo_report.processing_time_ms + ux_report.processing_time_ms
        }
        
        import json
        
        # Save combined JSON report
        json_path = reports_dir / f"{website_name}_combined_report.json"
        with open(json_path, "w") as f:
            json.dump(combined_report, f, indent=2)
        print(f"\n📁 Combined report saved to: {json_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 TESTING WEBSITE ANALYSIS AGENTS\n")
    
    seo_ok = test_seo_agent()
    ux_ok = test_ux_agent()
    both_ok = test_both_agents()
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"SEO Agent: {'✅ PASS' if seo_ok else '❌ FAIL'}")
    print(f"UX Agent: {'✅ PASS' if ux_ok else '❌ FAIL'}")
    print(f"Both Agents: {'✅ PASS' if both_ok else '❌ FAIL'}")
    print(f"{'='*60}\n")
    
    if seo_ok and ux_ok and both_ok:
        print("🎉 ALL TESTS PASSED! Ready for API testing.\n")
        sys.exit(0)
    else:
        print("⚠️  SOME TESTS FAILED! Fix errors before API testing.\n")
        sys.exit(1)