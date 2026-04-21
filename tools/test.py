#!/usr/bin/env python3
"""Test scraper and parser on multiple real websites."""

from scraper import PageScraper
from html_parser import HTMLParser
import json
from datetime import datetime

def test_website(url):
    """Test a single website and return results."""
    print(f"\n🌐 Testing: {url}")
    print(f"{'─'*60}")
    
    try:
        # Scrape
        with PageScraper(timeout_ms=30000) as scraper:
            scrape_result = scraper.scrape(url)
        
        if not scrape_result.success:
            return {
                "url": url,
                "success": False,
                "error": scrape_result.error,
                "timestamp": datetime.now().isoformat()
            }
        
        # Parse
        parser = HTMLParser(scrape_result.html, base_url=scrape_result.final_url)
        parsed = parser.parse()
        
        # Return results
        return {
            "url": url,
            "success": True,
            "status_code": scrape_result.status_code,
            "title": scrape_result.title,
            "load_time_ms": scrape_result.load_time_ms,
            "html_length": len(scrape_result.html),
            "screenshot_size_kb": scrape_result.screenshot_size_kb,
            "headings": {
                "h1": len(parsed.headings.h1),
                "h2": len(parsed.headings.h2),
                "h3": len(parsed.headings.h3),
            },
            "links": {
                "total": len(parsed.links),
                "internal": parsed.internal_link_count,
                "external": parsed.external_link_count,
            },
            "images": {
                "total": len(parsed.images),
                "with_alt": sum(1 for img in parsed.images if img.has_alt),
                "missing_alt": len(parsed.images_missing_alt),
            },
            "forms": len(parsed.forms),
            "videos": len(parsed.videos),
            "word_count": parsed.word_count,
            "has_schema": parsed.has_schema_markup,
            "schema_types": parsed.schema_types,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "url": url,
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Test multiple websites."""
    
    # Test URLs
    test_urls = [
        "https://example.com",
        "https://github.com",
        "https://wikipedia.org",
    ]
    
    print(f"\n{'='*60}")
    print(f"MULTI-WEBSITE TESTING")
    print(f"{'='*60}")
    
    results = []
    
    for url in test_urls:
        result = test_website(url)
        results.append(result)
        
        if result["success"]:
            print(f"✅ SUCCESS")
            print(f"   Title: {result['title']}")
            print(f"   Status: {result['status_code']}")
            print(f"   Load time: {result['load_time_ms']}ms")
            print(f"   Headings: H1={result['headings']['h1']}, H2={result['headings']['h2']}")
            print(f"   Links: {result['links']['total']} ({result['links']['internal']} internal)")
            print(f"   Images: {result['images']['total']} ({result['images']['missing_alt']} missing alt)")
        else:
            print(f"❌ FAILED: {result['error']}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    successful = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    print(f"✅ Successful: {successful}/{len(test_urls)}")
    print(f"❌ Failed: {failed}/{len(test_urls)}")
    
    # Save results to file
    with open("/tmp/test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📁 Results saved to: /tmp/test_results.json")

if __name__ == "__main__":
    main()