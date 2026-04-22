import json
import time
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import Config
from core.llm import llm
from schema.report import SEOReport  # Reuse same report structure
from tools.scraper import PageScraper
from tools.html_parser import HTMLParser


llm = ChatGoogleGenerativeAI(
    model=Config.LLM_MODEL,
    google_api_key=Config.GEMINI_API_KEY,
    temperature=Config.LLM_TEMPERATURE,
    max_tokens=Config.LLM_MAX_TOKENS
)

__all__ = ["llm"]

class UXAgent:
    """Analyzes website UX metrics and provides recommendations."""
    
    def __init__(self):
        """Initialize UX agent."""
        with open("prompts/ux.txt", "r") as f:
            self.system_prompt = f.read()
    
    def analyze(self, url: str) -> SEOReport:
        """
        Analyze a website's UX.
        
        Args:
            url: Website URL to analyze
        
        Returns:
            UX Report with findings and recommendations
        """
        start_time = time.time()
        
        print(f"\n[UX Agent] Analyzing: {url}")
        print(f"{'─'*60}")
        
        try:
            # Step 1: Scrape website
            print("[UX] Step 1: Scraping website...")
            scraper = PageScraper()
            scraper.start()
            scrape_result = scraper.scrape(url)
            scraper.stop()
            
            if not scrape_result.success:
                raise Exception(f"Scraping failed: {scrape_result.error}")
            
            print(f"   OK: Scraped {scrape_result.title}")
            
            # Step 2: Parse HTML
            print("[UX] Step 2: Parsing HTML...")
            parser = HTMLParser(scrape_result.html, base_url=scrape_result.final_url)
            parsed_page = parser.parse()
            print(f"   OK: Parsed structure")
            
            # Step 3: Prepare data for LLM
            print("[UX] Step 3: Analyzing with AI...")
            analysis_data = self._prepare_analysis_data(scrape_result, parsed_page)
            
            # Step 4: Call LLM
            ux_findings = self._call_llm(analysis_data)
            
            # Step 5: Create report
            print("[UX] Step 4: Creating report...")
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
            
            print(f"   OK: Analysis complete in {processing_time:.0f}ms")
            print(f"   Score: {report.overall_score}/100")
            
            return report
            
        except Exception as e:
            print(f"   ERROR: {str(e)}")
            raise
    
    def _prepare_analysis_data(self, scrape_result, parsed_page) -> dict:
        """Prepare structured data for LLM analysis."""
        return {
            "url": scrape_result.final_url,
            "title": scrape_result.title,
            "navigation": {
                "total_links": len(parsed_page.links),
                "internal_links": parsed_page.internal_link_count,
                "has_nav_menu": any(link.href for link in parsed_page.links[:10]),
            },
            "layout": {
                "headings": len(parsed_page.headings.h1) + len(parsed_page.headings.h2),
                "images": len(parsed_page.images),
                "forms": len(parsed_page.forms),
                "buttons": len([l for l in parsed_page.links if any(word in l.text.lower() for word in ["button", "click", "submit", "sign"])]),
            },
            "content": {
                "word_count": parsed_page.word_count,
                "paragraphs_count": parsed_page.word_count // 100 if parsed_page.word_count else 0,
                "avg_paragraph_length": (parsed_page.word_count // 100) if parsed_page.word_count else 0,
            },
            "accessibility": {
                "images_with_alt": sum(1 for img in parsed_page.images if img.has_alt),
                "total_images": len(parsed_page.images),
                "has_meta_viewport": parsed_page.meta.viewport is not None,
            },
            "forms": {
                "total_forms": len(parsed_page.forms),
                "has_contact_form": any("contact" in str(f).lower() for f in parsed_page.forms),
            }
        }
    
    def _call_llm(self, analysis_data: dict) -> dict:
        """Call LLM to analyze UX data."""
        data_str = json.dumps(analysis_data, indent=2)
        
        human_message = HumanMessage(
            content=f"""Analyze this website's UX:

{data_str}

Provide a detailed UX analysis in JSON format."""
        )
        
        system_message = SystemMessage(content=self.system_prompt)
        
        response = llm.invoke([system_message, human_message])
        response_text = response.content
        
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[json_start:json_end]
            findings = json.loads(json_str)
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[UX] Warning: JSON parsing failed: {e}")
            findings = {"overall_score": 50, "error": str(e)}
        
        return findings