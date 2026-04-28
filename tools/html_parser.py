import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import re


# ═══════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════

@dataclass
class MetaInfo:
    title: str = ""
    description: str = ""
    keywords: str = ""
    canonical: str = ""
    robots: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    og_type: str = ""
    twitter_card: str = ""
    twitter_title: str = ""
    twitter_description: str = ""
    viewport: str = ""
    charset: str = ""
    language: str = ""


@dataclass
class HeadingStructure:
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    h3: list[str] = field(default_factory=list)
    h4: list[str] = field(default_factory=list)
    h5: list[str] = field(default_factory=list)
    h6: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of heading elements across all levels."""
        return sum(len(getattr(self, f"h{i}")) for i in range(1, 7))

    @property
    def has_single_h1(self) -> bool:
        """True if there is exactly one H1 — the ideal state."""
        return len(self.h1) == 1

    @property
    def has_skipped_levels(self) -> bool:
        """Detects if heading levels are skipped (e.g. H1 directly to H3)."""
        levels_used = [i for i in range(1, 7) if len(getattr(self, f"h{i}")) > 0]
        for i in range(len(levels_used) - 1):
            if levels_used[i + 1] - levels_used[i] > 1:
                return True
        return False


@dataclass
class LinkInfo:
    href: str
    text: str
    is_external: bool
    has_nofollow: bool
    opens_new_tab: bool


@dataclass
class ImageInfo:
    src: str
    alt: str
    has_alt: bool
    width: Optional[str]
    height: Optional[str]
    is_decorative: bool
    loading: str = "auto"


@dataclass
class FormInfo:
    action: str
    method: str
    input_count: int
    has_labels: bool
    input_types: list[str]
    has_submit: bool


@dataclass
class VideoInfo:
    src: str
    sources: list[str]
    has_controls: bool
    autoplay: bool


@dataclass
class ButtonInfo:
    text: str
    button_type: str
    is_submit: bool


@dataclass
class ParsedPage:
    url: str
    meta: MetaInfo
    headings: HeadingStructure
    links: list[LinkInfo]
    images: list[ImageInfo]
    forms: list[FormInfo]
    videos: list[VideoInfo]
    buttons: list[ButtonInfo]
    paragraphs: list[str]
    word_count: int
    has_schema_markup: bool
    schema_types: list[str]
    internal_link_count: int
    external_link_count: int
    images_missing_alt: list[str]
    has_skip_links: bool
    has_focus_indicators: bool
    is_mobile_responsive: bool
    all_elements: list = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# HTML PARSER
# ═══════════════════════════════════════════════════════════════

class HTMLParser:
    """Parse and extract structured data from HTML."""
    
    def __init__(self, html: str, base_url: str = ""):
        self.html = html
        self.base_url = base_url
        self.soup = BeautifulSoup(html, "html.parser")
    
    def parse(self) -> ParsedPage:
        """Parse HTML and extract all data."""
        # Extract once and reuse to avoid redundant parsing
        links = self._extract_links()
        images = self._extract_images()

        return ParsedPage(
            url=self.base_url,
            meta=self._extract_meta(),
            headings=self._extract_headings(),
            links=links,
            images=images,
            forms=self._extract_forms(),
            videos=self._extract_videos(),
            buttons=self._extract_buttons(),
            paragraphs=self._extract_paragraphs(),
            word_count=self._count_words(),
            has_schema_markup=self._has_schema_markup(),
            schema_types=self._extract_schema_types(),
            internal_link_count=sum(1 for l in links if not l.is_external),
            external_link_count=sum(1 for l in links if l.is_external),
            images_missing_alt=[img.src for img in images if not img.has_alt],
            has_skip_links=self._has_skip_links(),
            has_focus_indicators=self._has_focus_indicators(),
            is_mobile_responsive=self._is_mobile_responsive(),
        )
    
    def _extract_meta(self) -> MetaInfo:
        """Extract meta information."""
        meta = MetaInfo()
        
        title_tag = self.soup.find("title")
        meta.title = title_tag.text if title_tag else ""
        
        for tag in self.soup.find_all("meta"):
            name = tag.get("name", "").lower()
            prop = tag.get("property", "").lower()
            content = tag.get("content", "")
            
            if name == "description":
                meta.description = content
            elif name == "keywords":
                meta.keywords = content
            elif name == "robots":
                meta.robots = content
            elif name == "viewport":
                meta.viewport = content
            elif name == "charset":
                meta.charset = content
            elif prop == "og:title":
                meta.og_title = content
            elif prop == "og:description":
                meta.og_description = content
            elif prop == "og:image":
                meta.og_image = content
            elif prop == "og:type":
                meta.og_type = content
            elif name == "twitter:card":
                meta.twitter_card = content
            elif name == "twitter:title":
                meta.twitter_title = content
            elif name == "twitter:description":
                meta.twitter_description = content
        
        # Language
        html_tag = self.soup.find("html")
        meta.language = html_tag.get("lang", "") if html_tag else ""
        
        # Canonical
        canonical_tag = self.soup.find("link", {"rel": "canonical"})
        meta.canonical = canonical_tag.get("href", "") if canonical_tag else ""
        
        return meta
    
    def _extract_headings(self) -> HeadingStructure:
        """Extract all headings."""
        headings = HeadingStructure()
        
        for i in range(1, 7):
            tags = self.soup.find_all(f"h{i}")
            heading_list = getattr(headings, f"h{i}")
            for tag in tags:
                text = tag.get_text(strip=True)
                if text:
                    heading_list.append(text)
        
        return headings
    
    def _extract_links(self) -> list[LinkInfo]:
        """Extract all links."""
        links = []
        
        for tag in self.soup.find_all("a", href=True):
            href = tag.get("href", "")
            text = tag.get_text(strip=True)
            
            is_external = self._is_external_url(href)
            has_nofollow = "nofollow" in tag.get("rel", [])
            opens_new_tab = tag.get("target", "") == "_blank"
            
            links.append(LinkInfo(
                href=href,
                text=text,
                is_external=is_external,
                has_nofollow=has_nofollow,
                opens_new_tab=opens_new_tab,
            ))
        
        return links
    
    def _extract_images(self) -> list[ImageInfo]:
        """Extract all images."""
        images = []
        
        for tag in self.soup.find_all("img"):
            src = tag.get("src", "")
            alt = tag.get("alt", "")
            width = tag.get("width")
            height = tag.get("height")
            loading = tag.get("loading", "auto")
            
            # Check if decorative (empty alt with role="presentation" or aria-hidden)
            is_decorative = (
                alt == "" and 
                (tag.get("role") == "presentation" or tag.get("aria-hidden") == "true")
            )
            
            images.append(ImageInfo(
                src=src,
                alt=alt,
                has_alt=len(alt) > 0,
                width=width,
                height=height,
                is_decorative=is_decorative,
                loading=loading,
            ))
        
        return images
    
    def _extract_forms(self) -> list[FormInfo]:
        """Extract all forms."""
        forms = []
        
        for form_tag in self.soup.find_all("form"):
            action = form_tag.get("action", "")
            method = form_tag.get("method", "GET").upper()
            
            inputs = form_tag.find_all(["input", "textarea", "select"])
            input_count = len(inputs)
            input_types = [inp.get("type", "text") for inp in inputs if inp.name == "input"]
            
            labels = form_tag.find_all("label")
            has_labels = len(labels) > 0
            
            has_submit = any(
                inp.get("type") == "submit" 
                for inp in form_tag.find_all("input")
            )
            
            forms.append(FormInfo(
                action=action,
                method=method,
                input_count=input_count,
                has_labels=has_labels,
                input_types=input_types,
                has_submit=has_submit,
            ))
        
        return forms
    
    def _extract_videos(self) -> list[VideoInfo]:
        """Extract all videos."""
        videos = []
        
        for video_tag in self.soup.find_all("video"):
            src = video_tag.get("src", "")
            sources = [s.get("src", "") for s in video_tag.find_all("source")]
            has_controls = "controls" in video_tag.attrs
            autoplay = "autoplay" in video_tag.attrs
            
            videos.append(VideoInfo(
                src=src,
                sources=sources,
                has_controls=has_controls,
                autoplay=autoplay,
            ))
        
        return videos
    
    def _extract_buttons(self) -> list[ButtonInfo]:
        """Extract all buttons."""
        buttons = []
        
        for btn_tag in self.soup.find_all(["button", "input"]):
            if btn_tag.name == "input" and btn_tag.get("type") not in ["button", "submit", "reset"]:
                continue
            
            text = btn_tag.get_text(strip=True) if btn_tag.name == "button" else btn_tag.get("value", "")
            button_type = btn_tag.get("type", "button")
            is_submit = button_type == "submit"
            
            buttons.append(ButtonInfo(
                text=text,
                button_type=button_type,
                is_submit=is_submit,
            ))
        
        return buttons
    
    def _extract_paragraphs(self) -> list[str]:
        """Extract all paragraphs."""
        paragraphs = []
        
        for p_tag in self.soup.find_all("p"):
            text = p_tag.get_text(strip=True)
            if text:
                paragraphs.append(text)
        
        return paragraphs
    
    def _count_words(self) -> int:
        """Count total words on page."""
        text = self.soup.get_text(strip=True)
        words = text.split()
        return len(words)
    
    def _has_schema_markup(self) -> bool:
        """Check if page has schema markup."""
        return bool(self.soup.find("script", {"type": "application/ld+json"}))
    
    def _extract_schema_types(self) -> list[str]:
        """Extract schema markup types."""
        types = []
        
        for script_tag in self.soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script_tag.string)
                if isinstance(data, dict):
                    schema_type = data.get("@type", "")
                    if schema_type:
                        types.append(schema_type)
            except:
                pass
        
        return types
    
    def _has_skip_links(self) -> bool:
        """Check for skip navigation links."""
        for link in self.soup.find_all("a"):
            href = link.get("href", "").lower()
            text = link.get_text(strip=True).lower()
            if "skip" in text or "skip" in href:
                return True
        return False
    
    def _has_focus_indicators(self) -> bool:
        """Check for focus indicators in CSS."""
        style_tags = self.soup.find_all("style")
        css_text = " ".join(tag.string or "" for tag in style_tags)
        return ":focus" in css_text or ":focus-visible" in css_text
    
    def _is_mobile_responsive(self) -> bool:
        """Check if page is mobile responsive."""
        meta_tags = self.soup.find_all("meta", {"name": "viewport"})
        return len(meta_tags) > 0
    
    def _is_external_url(self, url: str) -> bool:
        """Check if URL is external."""
        if url.startswith("http://") or url.startswith("https://"):
            parsed_url = urlparse(url)
            parsed_base = urlparse(self.base_url)
            return parsed_url.netloc != parsed_base.netloc
        return False