import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup


# =============================================================================
# DATA CLASSES — structured containers for extracted data
# =============================================================================
# Each dataclass maps to one domain of analysis.
# Agents receive these objects and can access fields by name.

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
        """
        Detects if heading levels are skipped (e.g. H1 directly to H3).
        This is a WCAG accessibility issue and bad for document structure.
        """
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
    has_captions: bool
    width: Optional[str]
    height: Optional[str]


@dataclass
class ParsedPage:
    base_url: str
    meta: MetaInfo
    headings: HeadingStructure
    links: list[LinkInfo]
    images: list[ImageInfo]
    forms: list[FormInfo]
    videos: list[VideoInfo]
    scripts: list[str]
    stylesheets: list[str]
    iframes: list[str]
    schema_types: list[str]
    word_count: int
    inline_styles_count: int

    # Computed counts (derived from the lists above — set during parsing)
    internal_link_count: int = 0
    external_link_count: int = 0

    @property
    def has_schema_markup(self) -> bool:
        return len(self.schema_types) > 0

    @property
    def has_viewport_meta(self) -> bool:
        return bool(self.meta.viewport)

    @property
    def images_missing_alt(self) -> list[ImageInfo]:
        """Images that have NO alt attribute at all — accessibility violation."""
        return [img for img in self.images if not img.has_alt]

    @property
    def images_without_dimensions(self) -> list[ImageInfo]:
        """Images missing width/height — causes Cumulative Layout Shift (CLS)."""
        return [img for img in self.images if not img.width or not img.height]

    def to_dict(self) -> dict:
        """Convert entire ParsedPage to a JSON-serialisable dict."""
        return asdict(self)


# =============================================================================
# MAIN CLASS — HTMLParser
# =============================================================================

class HTMLParser:

    def __init__(self, html: str, base_url: str = ""):
        """
        Initialise the parser with HTML content and the page's base URL.

        Args:
            html    : Raw HTML string from PageScraper.scrape()
            base_url: The page's URL — used to resolve relative links/images
                      to absolute URLs (e.g. "/about" → "https://example.com/about")
        """
        self.html = html
        self.base_url = base_url

        # Extract the domain from base_url for internal/external link classification.
        # urlparse("https://example.com/page").netloc → "example.com"
        self.domain = urlparse(base_url).netloc if base_url else ""

        # Build the BeautifulSoup tree once.
        # "lxml" is faster than Python's built-in "html.parser" and handles
        # malformed HTML more gracefully.
        self._soup = BeautifulSoup(html, "lxml")

    # -------------------------------------------------------------------------
    # PUBLIC METHOD — parse()
    # -------------------------------------------------------------------------

    def parse(self) -> ParsedPage:
        links = self._parse_links()
        internal = [l for l in links if not l.is_external]
        external = [l for l in links if l.is_external]

        return ParsedPage(
            base_url=self.base_url,
            meta=self._parse_meta(),
            headings=self._parse_headings(),
            links=links,
            images=self._parse_images(),
            forms=self._parse_forms(),
            videos=self._parse_videos(),
            scripts=self._parse_scripts(),
            stylesheets=self._parse_stylesheets(),
            iframes=self._parse_iframes(),
            schema_types=self._parse_schema_types(),
            word_count=self._calculate_word_count(),
            inline_styles_count=self._count_inline_styles(),
            internal_link_count=len(internal),
            external_link_count=len(external),
        )

    # -------------------------------------------------------------------------
    # PRIVATE PARSE METHODS — each extracts one category of data
    # -------------------------------------------------------------------------

    def _get_meta_content(self, name: str = None, prop: str = None) -> str:
        if name:
            tag = self._soup.find("meta", attrs={"name": name})
        elif prop:
            tag = self._soup.find("meta", attrs={"property": prop})
        else:
            return ""
        return tag.get("content", "").strip() if tag else ""

    def _parse_meta(self) -> MetaInfo:
        """
        Extracts all <head> metadata.
        Covers: title, description, Open Graph, Twitter Cards, viewport,
                canonical, robots, charset, and language.
        """
        title_tag = self._soup.find("title")
        canonical_tag = self._soup.find("link", attrs={"rel": "canonical"})
        charset_tag = self._soup.find("meta", attrs={"charset": True})
        html_tag = self._soup.find("html")

        return MetaInfo(
            title=title_tag.get_text().strip() if title_tag else "",
            description=self._get_meta_content(name="description"),
            keywords=self._get_meta_content(name="keywords"),
            canonical=canonical_tag.get("href", "") if canonical_tag else "",
            robots=self._get_meta_content(name="robots"),
            og_title=self._get_meta_content(prop="og:title"),
            og_description=self._get_meta_content(prop="og:description"),
            og_image=self._get_meta_content(prop="og:image"),
            og_type=self._get_meta_content(prop="og:type"),
            twitter_card=self._get_meta_content(name="twitter:card"),
            twitter_title=self._get_meta_content(name="twitter:title"),
            twitter_description=self._get_meta_content(name="twitter:description"),
            viewport=self._get_meta_content(name="viewport"),
            charset=charset_tag.get("charset", "") if charset_tag else "",
            language=html_tag.get("lang", "") if html_tag else "",
        )

    def _parse_headings(self) -> HeadingStructure:
        return HeadingStructure(
            h1=[h.get_text(strip=True) for h in self._soup.find_all("h1")],
            h2=[h.get_text(strip=True) for h in self._soup.find_all("h2")],
            h3=[h.get_text(strip=True) for h in self._soup.find_all("h3")],
            h4=[h.get_text(strip=True) for h in self._soup.find_all("h4")],
            h5=[h.get_text(strip=True) for h in self._soup.find_all("h5")],
            h6=[h.get_text(strip=True) for h in self._soup.find_all("h6")],
        )

    def _parse_links(self) -> list[LinkInfo]:
        links = []
        for a_tag in self._soup.find_all("a", href=True):
            href = a_tag.get("href", "").strip()

            # Skip non-navigational link types
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue

            # urljoin converts relative URLs to absolute.
            # urljoin("https://example.com/page", "/about") → "https://example.com/about"
            # urljoin("https://example.com/page", "https://other.com") → "https://other.com"
            abs_href = urljoin(self.base_url, href) if self.base_url else href
            parsed = urlparse(abs_href)

            # A link is external if it has a netloc (domain) AND that domain
            # differs from our page's domain.
            is_external = bool(parsed.netloc) and parsed.netloc != self.domain

            # rel attribute can be a list: rel="nofollow noopener noreferrer"
            rel_values = a_tag.get("rel", [])

            links.append(LinkInfo(
                href=abs_href,
                text=a_tag.get_text(strip=True),
                is_external=is_external,
                has_nofollow="nofollow" in rel_values,
                opens_new_tab=a_tag.get("target", "") == "_blank",
            ))
        return links

    def _parse_images(self) -> list[ImageInfo]:
        images = []
        for img in self._soup.find_all("img"):
            src = img.get("src", "").strip()
            alt = img.get("alt", None)       # None means alt attr is completely absent
            has_alt = alt is not None        # alt="" is present (even if empty)

            images.append(ImageInfo(
                src=urljoin(self.base_url, src) if self.base_url and src else src,
                alt=alt if alt is not None else "",
                has_alt=has_alt,
                width=img.get("width"),
                height=img.get("height"),
                is_decorative=(alt == ""),    # alt="" = deliberately decorative
                loading=img.get("loading", "auto"),
            ))
        return images

    def _parse_forms(self) -> list[FormInfo]:
        forms = []
        for form in self._soup.find_all("form"):
            inputs = form.find_all(["input", "textarea", "select"])
            input_types = list({i.get("type", "text") for i in inputs})

            # Check for submit mechanism — either a submit input or a button
            has_submit = bool(
                form.find("input", type="submit") or
                form.find("button", type="submit") or
                form.find("button", type=None)   # button without type defaults to submit
            )

            forms.append(FormInfo(
                action=form.get("action", ""),
                method=form.get("method", "get").upper(),
                input_count=len(inputs),
                has_labels=bool(form.find_all("label")),
                input_types=input_types,
                has_submit=has_submit,
            ))
        return forms

    def _parse_videos(self) -> list[VideoInfo]:
        videos = []
        for video in self._soup.find_all("video"):
            # <source> children provide multiple format options (mp4, webm, etc.)
            sources = [s.get("src", "") for s in video.find_all("source", src=True)]

            videos.append(VideoInfo(
                src=video.get("src", ""),
                sources=sources,
                has_controls=video.has_attr("controls"),
                autoplay=video.has_attr("autoplay"),
                has_captions=bool(video.find("track", attrs={"kind": "captions"})),
                width=video.get("width"),
                height=video.get("height"),
            ))
        return videos

    def _parse_scripts(self) -> list[str]:
        return [
            s.get("src", "").strip()
            for s in self._soup.find_all("script", src=True)
            if s.get("src", "").strip()
        ]

    def _parse_stylesheets(self) -> list[str]:
        return [
            link.get("href", "").strip()
            for link in self._soup.find_all("link", rel="stylesheet")
            if link.get("href", "").strip()
        ]

    def _parse_iframes(self) -> list[str]:
        return [
            urljoin(self.base_url, f.get("src", ""))
            for f in self._soup.find_all("iframe", src=True)
        ]

    def _parse_schema_types(self) -> list[str]:
        schema_types = []
        for script in self._soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                # JSON-LD can be a single object or an array of objects
                if isinstance(data, list):
                    for item in data:
                        if "@type" in item:
                            schema_types.append(item["@type"])
                elif isinstance(data, dict) and "@type" in data:
                    schema_types.append(data["@type"])
            except (json.JSONDecodeError, AttributeError):
                # Malformed JSON-LD — skip silently
                pass
        return schema_types

    def _calculate_word_count(self) -> int:
        # Work on a copy so we don't mutate the original soup tree
        soup_copy = BeautifulSoup(self.html, "lxml")
        for invisible in soup_copy(["script", "style", "noscript", "head", "meta"]):
            invisible.decompose()   # removes the tag and its contents entirely

        visible_text = soup_copy.get_text(separator=" ", strip=True)
        return len(visible_text.split())

    def _count_inline_styles(self) -> int:
        return len(self._soup.find_all(style=True))


# =============================================================================
# PRETTY PRINTER — for terminal testing
# =============================================================================

class ParseResultPrinter:
    # Emoji indicators for pass/fail/warning states
    OK = "Done ✓✓"
    WARN = "Warning !! "
    FAIL = "Failed XX"

    def __init__(self, page: ParsedPage):
        self.page = page

    def _status(self, condition: bool, warn_on_false: bool = False) -> str:
        """Returns OK, WARN, or FAIL emoji based on condition."""
        if condition:
            return self.OK
        return self.WARN if warn_on_false else self.FAIL

    def print(self) -> None:
        """Print the full parsed page summary to stdout."""
        p = self.page
        self._section("META")
        print(f"  Title        : {p.meta.title or f'{self.FAIL} MISSING'}")
        desc = p.meta.description
        print(f"  Description  : {(desc[:80] + '...') if len(desc) > 80 else desc or f'{self.FAIL} MISSING'}")
        print(f"  Canonical    : {p.meta.canonical or f'{self.WARN} not set'}")
        print(f"  OG Title     : {p.meta.og_title or f'{self.WARN} not set'}")
        print(f"  OG Image     : {p.meta.og_image or f'{self.WARN} not set'}")
        print(f"  Language     : {p.meta.language or f'{self.WARN} not set'}")
        print(f"  Charset      : {p.meta.charset or f'{self.WARN} not set'}")
        print(f"  Viewport     : {p.meta.viewport or f'{self.FAIL} MISSING'}")
        print(f"  Robots       : {p.meta.robots or '(not set — defaults to index,follow)'}")

        self._section("HEADINGS")
        h1_status = self.OK if p.headings.has_single_h1 else (self.WARN if len(p.headings.h1) == 0 else self.FAIL)
        print(f"  H1 ({len(p.headings.h1)}) {h1_status}: {p.headings.h1}")
        print(f"  H2 ({len(p.headings.h2)}): {p.headings.h2[:4]}{'...' if len(p.headings.h2) > 4 else ''}")
        print(f"  H3–H6 count  : {sum(len(getattr(p.headings, f'h{i}')) for i in range(3, 7))}")
        if p.headings.has_skipped_levels:
            print(f"  {self.WARN} Heading levels skipped (e.g. H1 → H3)")

        self._section("LINKS")
        print(f"  Total        : {len(p.links)}")
        print(f"  Internal     : {p.internal_link_count}")
        print(f"  External     : {p.external_link_count}")
        notext = [l for l in p.links if not l.text]
        if notext:
            print(f"  {self.WARN} {len(notext)} links with no anchor text")

        self._section("IMAGES")
        missing = len(p.images_missing_alt)
        lazy = sum(1 for i in p.images if i.loading == "lazy")
        no_dims = len(p.images_without_dimensions)
        print(f"  Total        : {len(p.images)}")
        print(f"  Missing alt  : {missing} {self.OK if missing == 0 else self.FAIL}")
        print(f"  Lazy loaded  : {lazy}/{len(p.images)}")
        print(f"  No dimensions: {no_dims} {self.OK if no_dims == 0 else self.WARN}")

        self._section("TECHNICAL")
        print(f"  Word count   : {p.word_count:,} {self.OK if p.word_count >= 300 else self.WARN}")
        print(f"  Scripts      : {len(p.scripts)}")
        print(f"  Stylesheets  : {len(p.stylesheets)}")
        print(f"  Inline styles: {p.inline_styles_count} {self.OK if p.inline_styles_count < 20 else self.WARN}")
        print(f"  Iframes      : {len(p.iframes)}")
        print(f"  Videos       : {len(p.videos)}")
        print(f"  Forms        : {len(p.forms)}")

        self._section("SCHEMA / STRUCTURED DATA")
        if p.has_schema_markup:
            print(f"  {self.OK} Found: {', '.join(p.schema_types)}")
        else:
            print(f"  {self.FAIL} No JSON-LD schema markup found")

        if p.forms:
            self._section("FORMS")
            for i, f in enumerate(p.forms, 1):
                label_status = self.OK if f.has_labels else self.FAIL
                print(f"  Form {i}: method={f.method}, inputs={f.input_count}, "
                      f"labels={label_status}, submit={self.OK if f.has_submit else self.FAIL}")

        if p.videos:
            self._section("VIDEOS")
            for i, v in enumerate(p.videos, 1):
                print(f"  Video {i}: controls={self.OK if v.has_controls else self.WARN}, "
                      f"autoplay={self.FAIL if v.autoplay else self.OK}, "
                      f"captions={self.OK if v.has_captions else self.WARN}")

    def _section(self, title: str) -> None:
        """Prints a section header."""
        print(f"\n{'─' * 50}")
        print(f"  {title}")
        print(f"{'─' * 50}")


# =============================================================================
# CLI ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    import sys

    # Read HTML from stdin — pipe scraped HTML into this script:
    # python tools/scraper.py https://... | python tools/html_parser.py
    if not sys.stdin.isatty():
        html_input = sys.stdin.read()
        base = sys.argv[1] if len(sys.argv) > 1 else ""
    else:
        # Fallback: parse a saved HTML file
        if len(sys.argv) < 2:
            print("Usage: python html_parser.py <base_url> < page.html")
            sys.exit(1)
        with open(sys.argv[1], encoding="utf-8") as f:
            html_input = f.read()
        base = sys.argv[2] if len(sys.argv) > 2 else ""

    parser = HTMLParser(html_input, base_url=base)
    result = parser.parse()
    ParseResultPrinter(result).print()