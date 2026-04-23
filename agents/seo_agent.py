import json
import time
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import Config
from core.llm import llm
from schema.report import SEOReport
from tools.scraper import PageScraper
from tools.html_parser import HTMLParser


class SEOAgent:
    """Analyzes website SEO metrics and provides recommendations."""
    
    def __init__(self):
        """Initialize SEO agent."""
        with open("prompts/seo.txt", "r") as f:
            self.system_prompt = f.read()
    
    async def analyze(self, url: str) -> SEOReport:  # ✅ Make async
        """
        Analyze a website's SEO asynchronously.
        
        Args:
            url: Website URL to analyze
        
        Returns:
            SEOReport with findings and recommendations
        """
        start_time = time.time()
        
        print(f"\n SEO Agent analyzing: {url}")
        print(f"{'─'*60}")
        
        try:
            # Step 1: Scrape website
            print(" Step 1: Scraping website...")
            scraper = PageScraper()
            async with scraper as scraper:  # ✅ Use async context manager
                scrape_result = await scraper.scrape(url)  # ✅ await
            
            if not scrape_result.success:
                raise Exception(f"Scraping failed: {scrape_result.error}")
            
            print(f"   Scraped: {scrape_result.title} ({len(scrape_result.html)} chars)")
            
            # Step 2: Parse HTML
            print(" Step 2: Parsing HTML...")
            parser = HTMLParser(scrape_result.html, base_url=scrape_result.final_url)
            parsed_page = parser.parse()
            print(f"   Parsed: {len(parsed_page.headings.h1)} H1, {len(parsed_page.links)} links, {len(parsed_page.images)} images")
            
            # Step 3: Prepare data for LLM
            print(" Step 3: Analyzing with AI...")
            analysis_data = self._prepare_analysis_data(scrape_result, parsed_page)
            
            # Step 4: Call LLM
            seo_findings = self._call_llm(analysis_data)
            
            # Step 5: Create report
            print(" Step 4: Creating report...")
            processing_time = (time.time() - start_time) * 1000
            
            report = SEOReport(
                url=url,
                overall_score=seo_findings.get("overall_score", 50),
                strengths=seo_findings.get("strengths", []),
                weaknesses=seo_findings.get("weaknesses", []),
                missing_elements=seo_findings.get("missing_elements", []),
                recommendations=seo_findings.get("recommendations", []),
                processing_time_ms=processing_time
            )
            
            print(f"    Analysis complete in {processing_time:.0f}ms")
            print(f"    Overall Score: {report.overall_score}/100")
            
            return report
            
        except Exception as e:
            print(f"    Error: {str(e)}")
            raise
    
    def _prepare_analysis_data(self, scrape_result, parsed_page) -> dict:
        """Prepare structured data for LLM analysis."""
        return {
            "url": scrape_result.final_url,
            "title": scrape_result.title,
            "meta": {
                "description": parsed_page.meta.description,
                "keywords": parsed_page.meta.keywords,
                "viewport": parsed_page.meta.viewport,
                "canonical": parsed_page.meta.canonical,
                "og_title": parsed_page.meta.og_title,
                "og_description": parsed_page.meta.og_description,
                "og_image": parsed_page.meta.og_image,
                "language": parsed_page.meta.language,
            },
            "headings": {
                "h1": parsed_page.headings.h1,
                "h2": parsed_page.headings.h2[:5],
                "h3": parsed_page.headings.h3[:5],
                "total": parsed_page.headings.total,
                "has_single_h1": parsed_page.headings.has_single_h1,
                "has_skipped_levels": parsed_page.headings.has_skipped_levels,
            },
            "links": {
                "total": len(parsed_page.links),
                "internal": parsed_page.internal_link_count,
                "external": parsed_page.external_link_count,
                "with_nofollow": sum(1 for l in parsed_page.links if l.has_nofollow),
            },
            "images": {
                "total": len(parsed_page.images),
                "with_alt": sum(1 for img in parsed_page.images if img.has_alt),
                "missing_alt": len(parsed_page.images_missing_alt),
                "alt_coverage_percent": (sum(1 for img in parsed_page.images if img.has_alt) / len(parsed_page.images) * 100) if parsed_page.images else 0,
            },
            "content": {
                "word_count": parsed_page.word_count,
                "forms": len(parsed_page.forms),
                "videos": len(parsed_page.videos),
            },
            "schema": {
                "has_schema_markup": parsed_page.has_schema_markup,
                "schema_types": parsed_page.schema_types,
            }
        }
    
    def _call_llm(self, analysis_data: dict) -> dict:
        """Call LLM to analyze SEO data."""
        # Create prompt
        data_str = json.dumps(analysis_data, indent=2)

        human_message = HumanMessage(
            content=f"""Analyze this website's SEO:

    {data_str}

    Provide a detailed SEO analysis in JSON format."""
        )

        system_message = SystemMessage(content=self.system_prompt)

        # Call LLM
        response = llm.invoke([system_message, human_message])

        # Parse response
        response_text = response.content

        # Extract JSON from response
        try:
            # Try to find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[json_start:json_end]
            findings = json.loads(json_str)

        except (json.JSONDecodeError, ValueError) as e:
            print(f"  JSON parsing failed: {e}")
            print(f"   Raw response: {response_text[:200]}...")
            findings = {"overall_score": 50, "error": str(e)}
        
        return findings