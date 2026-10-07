import logging
import re
from typing import Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .session import ScraperSession, normalize_url
from .catalogues import clean_text

logger = logging.getLogger(__name__)


def parse_about_book(session: ScraperSession, about_url: str) -> dict[str, Any]:
    """
    Parses aboutbook.htm if available to extract metadata:
    Title, Author, Edition, Publisher, Year, etc.
    """
    meta: dict[str, Any] = {}
    try:
        soup, resp = session.get_soup(about_url)
        if resp.status_code != 200:
            return meta

        full_text = soup.get_text(separator="\n", strip=True)

        labels = [
            ("title", r"ڪتاب\s*جو\s*نالو"),
            ("author", r"(?:مصنف|مرتب|مترجم|(?<![\w\u0600-\u06FF])از(?![\w\u0600-\u06FF])|ليکڪ)"),
            ("edition", r"ايڊيشن"),
            ("publisher", r"ڇپائيندڙ"),
            ("year", r"سال"),
            ("pages", r"صفحا"),
        ]

        all_labels_pattern = r"(?:" + "|".join(pat for _, pat in labels) + r"|ڪاپي\s*رائيٽ|توهان\s*هن\s*وقت|ڪتاب\s*جو\s*تعارف|©|Published|Printed|$)"

        for key, pat in labels:
            match = re.search(pat + r"\s*[؛:؛]?\s*(.*?)(?=" + all_labels_pattern + r")", full_text, re.DOTALL)
            if match:
                val = clean_text(match.group(1))
                # Strip leading punctuation or placeholder dashes
                val = re.sub(r"^[\s؛:؛\-_]+|[\s؛:؛\-_]+$", "", val).strip()
                if val and val != "--":
                    meta[key] = val

        # Check intro snippet
        intro_match = re.search(r"ڪتاب\s*جو\s*تعارف\s*(.*?)(?=©|Sindhi Adabi Board|$)", full_text, re.DOTALL)
        if intro_match:
            intro_val = clean_text(intro_match.group(1))
            if intro_val and intro_val != "--":
                meta["intro"] = intro_val

    except Exception as e:
        logger.debug("aboutbook.htm not parsed for %s: %s", about_url, e)

    return meta


def clean_page_content(soup: BeautifulSoup) -> tuple[str, str]:
    """
    Cleans a book page and returns (header_meta, clean_text_content).
    Removes banners, iframes, footers, and pagination bars.
    """
    # Remove script, style, and iframe tags
    for tag in soup(["script", "style", "iframe", "noscript"]):
        tag.decompose()

    # Locate main container (typically table155)
    main_container = soup.find("table", id="table155")
    if not main_container:
        # Fallback to the table with highest text length or body
        tables = soup.find_all("table")
        if tables:
            main_container = max(tables, key=lambda t: len(t.get_text(strip=True)))
        else:
            main_container = soup.body

    if not main_container:
        return "", ""

    # Extract header banner metadata (table156 or contains 'سيڪشن؛')
    header_meta = ""
    t156 = main_container.find("table", id="table156")
    if t156:
        header_meta = clean_text(t156.get_text())
        t156.decompose()
    else:
        for el in main_container.find_all(lambda e: "سيڪشن" in e.get_text() and len(e.get_text()) < 150):
            header_meta = clean_text(el.get_text())
            el.decompose()
            break

    # Remove navigation links (e.g., نئون صفحو, ٻيا صفحا, ڪتاب جو ٽائيٽل صفحو)
    for p in main_container.find_all(["p", "td", "div", "tr"]):
        text = p.get_text()
        if any(nav_kw in text for nav_kw in ("نئون صفحو", "ٻيا صفحا", "ڪتاب جو ٽائيٽل صفحو")) and len(text) < 350:
            p.decompose()

    # Remove footer / copyright table (table139)
    for ft in main_container.find_all("table", id="table139"):
        ft.decompose()

    # Extract raw text lines
    raw_lines = main_container.get_text(separator="\n").splitlines()
    cleaned_lines: list[str] = []
    for line in raw_lines:
        s = clean_text(line)
        if s:
            # Skip lingering navigation keywords
            if s in ("نئون صفحو", "ڪتاب جو ٽائيٽل صفحو", "هوم پيج", "لائبريري ڪئٽلاگ"):
                continue
            cleaned_lines.append(s)

    content_text = "\n".join(cleaned_lines)
    # Normalize multiple newlines
    content_text = re.sub(r"\n{3,}", "\n\n", content_text).strip()

    return header_meta, content_text


def extract_page_number(url: str) -> int:
    """Extracts integer page number from a Book_page<N>.html URL."""
    match = re.search(r"page(\d+)", url, re.IGNORECASE)
    return int(match.group(1)) if match else 1


def discover_book_pages(session: ScraperSession, entry_url: str, limit_pages: int | None = None) -> list[str]:
    """
    Discovers all pages of a book starting from entry_url (Book_page1.html).
    """
    discovered: set[str] = {entry_url}
    to_visit = [entry_url]
    visited = set()

    while to_visit:
        cur_url = to_visit.pop(0)
        if cur_url in visited:
            continue
        visited.add(cur_url)

        try:
            soup, _ = session.get_soup(cur_url)
        except Exception as e:
            logger.warning("Could not fetch page %s: %s", cur_url, e)
            continue

        # Look for page links
        for a in soup.find_all("a", href=True):
            raw_href = a["href"].split("#")[0].strip()
            if not raw_href:
                continue

            # Check if link points to another page of this book
            if re.search(r"Book_page\d+\.html?", raw_href, re.IGNORECASE) or re.search(r"page\d+\.html?", raw_href, re.IGNORECASE):
                page_full = normalize_url(raw_href, cur_url)
                if page_full not in discovered:
                    discovered.add(page_full)
                    # Visit up to a few pages to uncover the full pagination bar
                    if len(visited) < 5:
                        to_visit.append(page_full)

    # Sort pages in natural numerical order: 1, 2, 3, ...
    sorted_pages = sorted(discovered, key=extract_page_number)

    if limit_pages:
        sorted_pages = sorted_pages[:limit_pages]

    return sorted_pages


def scrape_full_book(
    session: ScraperSession,
    book_info: dict[str, Any],
    limit_pages: int | None = None
) -> dict[str, Any]:
    """
    Scrapes all pages of a book and compiles all content into a single structure.
    """
    entry_url = book_info["entry_url"]
    about_url = book_info.get("about_url", "")
    logger.info("Scraping book '%s' (%s)", book_info.get("title") or book_info.get("book_id"), entry_url)

    # 1. Fetch metadata from aboutbook.htm if available
    metadata = {}
    if about_url:
        metadata = parse_about_book(session, about_url)

    # 2. Discover all pages of the book
    page_urls = discover_book_pages(session, entry_url, limit_pages=limit_pages)
    logger.info("Book has %d discovered page(s)", len(page_urls))

    # 3. Scrape and clean each page in order
    pages_content: list[dict[str, Any]] = []
    title_from_page1 = ""
    author_from_page1 = ""

    for i, p_url in enumerate(page_urls, start=1):
        try:
            soup, _ = session.get_soup(p_url)
            header_meta, text = clean_page_content(soup)

            # Check page 1 for title/author fallback if needed
            if i == 1:
                main_tbl = soup.find("table", id="table155")
                if main_tbl:
                    short_rows = []
                    for r in main_tbl.find_all("tr", recursive=False)[1:]:
                        r_text = clean_text(r.get_text())
                        if r_text and len(r_text) < 120 and not any(kw in r_text for kw in ("نئون صفحو", "ٻيا صفحا")):
                            short_rows.append(r_text)
                        else:
                            break
                    if short_rows and not metadata.get("title"):
                        title_from_page1 = short_rows[0]
                    if len(short_rows) > 1 and not metadata.get("author"):
                        author_from_page1 = short_rows[1]

                # Fallback to lines if not found
                if not title_from_page1 or not author_from_page1:
                    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
                    if lines and not metadata.get("title") and not title_from_page1:
                        title_from_page1 = lines[0]
                    if len(lines) > 1 and not metadata.get("author") and not author_from_page1:
                        author_from_page1 = lines[1]

            page_num = extract_page_number(p_url)
            pages_content.append({
                "page_number": page_num,
                "url": p_url,
                "header_meta": header_meta,
                "content": text,
            })
        except Exception as e:
            logger.warning("Error scraping page %s: %s", p_url, e)

    # Consolidate metadata
    resolved_title = (
        metadata.get("title")
        or book_info.get("title")
        or title_from_page1
        or book_info.get("book_id", "Unknown Book")
    )
    resolved_author = metadata.get("author") or author_from_page1 or "سنڌي ادبي بورڊ"

    # Build compiled single-file representation
    compiled_lines: list[str] = [
        "=" * 80,
        f"ڪتاب: {resolved_title}",
        f"مصنف / مرتب: {resolved_author}",
        f"ڪئٽلاگ: {book_info.get('catalogue_name')} ({book_info.get('catalogue_slug')})",
    ]

    if metadata.get("edition"):
        compiled_lines.append(f"ايڊيشن: {metadata['edition']}")
    if metadata.get("year"):
        compiled_lines.append(f"سال: {metadata['year']}")
    if metadata.get("publisher"):
        compiled_lines.append(f"ڇپائيندڙ: {metadata['publisher']}")
    if metadata.get("pages"):
        compiled_lines.append(f"صفحا (مجموعي): {metadata['pages']}")

    compiled_lines.extend([
        f"اصل لنڪ: {entry_url}",
        f"ڊائون لوڊ ڪيل صفحا: {len(pages_content)}",
        "=" * 80,
        "",
    ])

    if metadata.get("intro"):
        compiled_lines.extend([
            "--- ڪتاب جو تعارف ---",
            metadata["intro"],
            "",
            "=" * 80,
            "",
        ])

    # Append all pages in sequential order
    for p in pages_content:
        p_num = p["page_number"]
        p_hdr = p.get("header_meta", "")
        compiled_lines.extend([
            "-" * 60,
            f"صفحو : {p_num}" + (f" | {p_hdr}" if p_hdr else ""),
            "-" * 60,
            "",
            p["content"],
            "",
        ])

    full_compiled_text = "\n".join(compiled_lines)

    return {
        "book_id": book_info.get("book_id"),
        "title": resolved_title,
        "author": resolved_author,
        "catalogue_slug": book_info.get("catalogue_slug"),
        "catalogue_name": book_info.get("catalogue_name"),
        "entry_url": entry_url,
        "metadata": metadata,
        "pages_count": len(pages_content),
        "pages": pages_content,
        "full_text": full_compiled_text,
    }
