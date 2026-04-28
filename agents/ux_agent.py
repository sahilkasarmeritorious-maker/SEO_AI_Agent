import json
import time
import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import Config
from core.llm import llm
from schema.report import SEOReport  # Reuse same report structure
from tools.scraper import PageScraper
from tools.html_parser import HTMLParser


class UXAgent:
    """Analyzes website UX metrics and provides recommendations."""
    
    def __init__(self):
        """Initialize UX agent."""
        with open("prompts/ux.txt", "r") as f:
            self.system_prompt = f.read()
    
    async def analyze(self, url: str) -> SEOReport:  # ✅ async
        """
        Analyze a website's UX asynchronously.
        
        Args:
            url: Website URL to analyze
        
        Returns:
            UX Report with findings and recommendations
        """
        start_time = time.time()
        
        print(f"\n UX Agent analyzing: {url}")
        print(f"{'─'*60}")
        
        try:
            # Step 1: Scrape website
            print(" Step 1: Scraping website...")
            scraper = PageScraper()
            async with scraper as scraper:  # ✅ Async context manager
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
            ux_findings = await self._call_llm(analysis_data)
            
            # Step 5: Create report
            print(" Step 4: Creating report...")
            processing_time = (time.time() - start_time) * 1000
            
            report = SEOReport(
                url=url,
                overall_score=ux_findings.get("overall_score", 50),
                strengths=ux_findings.get("strengths", []),
                weaknesses=ux_findings.get("weaknesses", []),
                missing_elements=ux_findings.get("missing_elements", []),
                recommendations=ux_findings.get("recommendations", []),
                processing_time_ms=processing_time
            )
            
            print(f"   Analysis complete in {processing_time:.0f}ms")
            print(f"   Overall Score: {report.overall_score}/100")
            
            return report
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            raise
    
    def _prepare_analysis_data(self, scrape_result, parsed_page) -> dict:
        """Prepare structured data for LLM analysis."""
        return {
            "url": scrape_result.final_url,
            "title": scrape_result.title,
            "load_time_ms": scrape_result.load_time_ms,
            "meta": {
                "viewport": parsed_page.meta.viewport,
                "description": parsed_page.meta.description,
                "language": parsed_page.meta.language,
            },
            "navigation": {
                "total_links": len(parsed_page.links),
                "internal_links": parsed_page.internal_link_count,
                "external_links": parsed_page.external_link_count,
                "links_with_meaningful_text": sum(1 for l in parsed_page.links if len(l.text.strip()) > 3),
                "links_missing_text": sum(1 for l in parsed_page.links if len(l.text.strip()) == 0),
                "new_tab_links": sum(1 for l in parsed_page.links if l.opens_new_tab),
            },
            "images": {
                "total": len(parsed_page.images),
                "with_alt": sum(1 for img in parsed_page.images if img.has_alt),
                "missing_alt": len(parsed_page.images_missing_alt),
                "alt_coverage_percent": (sum(1 for img in parsed_page.images if img.has_alt) / len(parsed_page.images) * 100) if parsed_page.images else 0,
                "decorative_images": sum(1 for img in parsed_page.images if img.is_decorative),
            },
            "content": {
                "word_count": parsed_page.word_count,
                "reading_time_minutes": parsed_page.word_count / 200 if parsed_page.word_count > 0 else 0,
                "paragraph_count": len(parsed_page.paragraphs),
                "average_paragraph_length": (parsed_page.word_count / len(parsed_page.paragraphs)) if parsed_page.paragraphs else 0,
            },
            "forms": {
                "total": len(parsed_page.forms),
                "forms_with_labels": sum(1 for f in parsed_page.forms if f.has_labels),
                "forms_missing_labels": sum(1 for f in parsed_page.forms if not f.has_labels),
                "total_inputs": sum(f.input_count for f in parsed_page.forms),
            },
            "accessibility": {
                "has_skip_links": parsed_page.has_skip_links,
                "has_focus_indicators": parsed_page.has_focus_indicators,
                "heading_structure": {
                    "has_single_h1": parsed_page.headings.has_single_h1,
                    "has_skipped_levels": parsed_page.headings.has_skipped_levels,
                    "total_headings": parsed_page.headings.total,
                },
                "buttons_with_text": sum(1 for b in parsed_page.buttons if b.text),
                "buttons_missing_text": sum(1 for b in parsed_page.buttons if not b.text),
            },
            "layout": {
                "is_mobile_responsive": parsed_page.is_mobile_responsive,
                "has_viewport_meta": parsed_page.meta.viewport != "",
                "elements_count": len(parsed_page.all_elements) if hasattr(parsed_page, 'all_elements') else 0,
            },
            "performance": {
                "page_load_time_ms": scrape_result.load_time_ms,
                "screenshot_size_kb": scrape_result.screenshot_size_kb,
            },
        }
    
    async def _call_llm(self, analysis_data: dict) -> dict:
        """Call LLM to analyze UX data (non-blocking)."""
        # Create prompt
        data_str = json.dumps(analysis_data, indent=2)

        human_message = HumanMessage(
            content=f"""Analyze this website's UX:

    {data_str}

    Provide a detailed UX analysis in JSON format."""
        )

        system_message = SystemMessage(content=self.system_prompt)

        # Run LLM in executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: llm.invoke([system_message, human_message])
                ),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            print("  LLM call timed out after 60s")
            return {"overall_score": 50, "error": "LLM call timed out"}

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
            print(f" JSON parsing failed: {e}")
            print(f"   Raw response: {response_text[:200]}...")
            findings = {"overall_score": 50, "error": str(e)}

        return findings