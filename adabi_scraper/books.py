import logging
import re
from typing import Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .session import ScraperSession, normalize_url
from .catalogues import clean_text

logger = logging.getLogger(__name__)


def extract_books_from_soup(soup: BeautifulSoup, page_url: str, cat_info: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Extracts book items from a single catalogue page soup.
    Returns mapping of entry_url -> book_dict
    """
    books: dict[str, dict[str, Any]] = {}

    for a in soup.find_all("a", href=True):
        raw_href = a["href"].strip()
        full_url = normalize_url(raw_href, page_url)

        # Match book page entry pattern: e.g. .../Book4/Book_page1.html
        match = re.search(r"/(Book\d+)/([^/#\?]+\.html?)", full_url, re.IGNORECASE)
        if not match:
            continue

        book_dir = match.group(1)
        filename = match.group(2)

        # We want the entry page (usually Book_page1.html or similar)
        # Normalize to Book_page1.html as the primary entry point
        entry_url = re.sub(r"/[^/]+\.html?$", "/Book_page1.html", full_url, flags=re.IGNORECASE)
        about_url = re.sub(r"/[^/]+\.html?$", "/aboutbook.htm", full_url, flags=re.IGNORECASE)

        text = clean_text(a.get_text())

        if entry_url not in books:
            books[entry_url] = {
                "book_id": book_dir,
                "catalogue_slug": cat_info.get("slug", "unknown"),
                "catalogue_name": cat_info.get("name_sindhi", ""),
                "title": text,
                "entry_url": entry_url,
                "about_url": about_url,
                "source_page": page_url,
            }
        elif text and not books[entry_url]["title"]:
            # Populate title if previously captured from an image tag
            books[entry_url]["title"] = text

    return books


def find_catalogue_pagination_urls(soup: BeautifulSoup, current_url: str) -> list[str]:
    """
    Finds pagination links within the catalogue (e.g. بقايا ڪتاب, Main_History2.HTML, etc.)
    """
    next_urls: list[str] = []

    for a in soup.find_all("a", href=True):
        raw_href = a["href"].strip()
        text = clean_text(a.get_text())
        full_url = normalize_url(raw_href, current_url)

        is_pagination = False
        # Check text: e.g. 'بقايا ڪتاب' or 'بقايا ليکڪ'
        if "بقايا" in text:
            is_pagination = True

        # Check URL pattern: e.g. Main_History2.HTML, Main_Poetry-1.HTML, Main_Children1.HTML
        if re.search(r"Main_[a-zA-Z_\-]+[0-9]+\.html?", raw_href, re.IGNORECASE):
            is_pagination = True

        if is_pagination and full_url != current_url and full_url not in next_urls:
            next_urls.append(full_url)

    return next_urls


def get_books_in_catalogue(session: ScraperSession, cat_info: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Crawls a catalogue and all its pagination pages, returning all unique books.
    """
    cat_url = cat_info["url"]
    logger.info("Discovering books in catalogue '%s' (%s)", cat_info.get("name_sindhi"), cat_url)

    visited_pages: set[str] = set()
    pages_to_visit = [cat_url]
    all_books: dict[str, dict[str, Any]] = {}

    while pages_to_visit:
        current_page_url = pages_to_visit.pop(0)
        if current_page_url in visited_pages:
            continue
        visited_pages.add(current_page_url)

        try:
            soup, _ = session.get_soup(current_page_url)
        except Exception as e:
            logger.warning("Failed to fetch catalogue page %s: %s", current_page_url, e)
            continue

        # Extract books on this page
        page_books = extract_books_from_soup(soup, current_page_url, cat_info)
        for url, book_data in page_books.items():
            if url not in all_books:
                all_books[url] = book_data
            elif book_data["title"] and not all_books[url]["title"]:
                all_books[url]["title"] = book_data["title"]

        # Discover next catalogue pagination pages
        next_pages = find_catalogue_pagination_urls(soup, current_page_url)
        for np in next_pages:
            if np not in visited_pages and np not in pages_to_visit:
                pages_to_visit.append(np)

    # Sort books naturally by book_id (e.g. Book1, Book2, ..., Book10)
    def natural_sort_key(b: dict[str, Any]):
        match = re.search(r"\d+", b.get("book_id", "0"))
        return int(match.group(0)) if match else 0

    sorted_books = sorted(all_books.values(), key=natural_sort_key)
    logger.info("Found %d books in catalogue '%s'", len(sorted_books), cat_info.get("name_sindhi"))
    return sorted_books


def get_all_books_across_catalogues(
    session: ScraperSession,
    catalogues: list[dict[str, Any]],
    limit_per_catalogue: int | None = None
) -> list[dict[str, Any]]:
    """
    Collects all books across multiple catalogues.
    """
    all_books: list[dict[str, Any]] = []
    for cat in catalogues:
        cat_books = get_books_in_catalogue(session, cat)
        if limit_per_catalogue:
            cat_books = cat_books[:limit_per_catalogue]
        all_books.extend(cat_books)
    return all_books
