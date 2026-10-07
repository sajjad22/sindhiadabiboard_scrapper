import logging
import re
from typing import Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .session import ScraperSession, BASE_URL, normalize_url

logger = logging.getLogger(__name__)

# Known Sindhi titles for catalogues if link text is missing or garbled
KNOWN_CATALOGUES_META: dict[str, dict[str, str]] = {
    "Religion": {"name_sindhi": "دينيات", "name_en": "Religion"},
    "History": {"name_sindhi": "تاريخ", "name_en": "History"},
    "Philosophy": {"name_sindhi": "فلسفو", "name_en": "Philosophy"},
    "Folk_Litrature": {"name_sindhi": "لوڪ ادب", "name_en": "Folk Literature"},
    "Navel": {"name_sindhi": "ناول", "name_en": "Novels"},
    "Personalties": {"name_sindhi": "شخصيات", "name_en": "Personalities"},
    "Dictionaries": {"name_sindhi": "لغات", "name_en": "Dictionaries"},
    "children_Litrature": {"name_sindhi": "ٻاراڻو ادب", "name_en": "Children Literature"},
    "Safarnama": {"name_sindhi": "سفرناما", "name_en": "Travelogue"},
    "Poetry": {"name_sindhi": "شاعري", "name_en": "Poetry"},
    "Articles": {"name_sindhi": "مضمون", "name_en": "Articles"},
    "Lateefyat": {"name_sindhi": "لطيفيات", "name_en": "Shah Latif Studies"},
    "Sufism": {"name_sindhi": "تصوف", "name_en": "Sufism"},
    "Tanqeed": {"name_sindhi": "تنقيد", "name_en": "Criticism"},
    "Stories": {"name_sindhi": "ڪهاڻيون", "name_en": "Stories"},
    "Dramas": {"name_sindhi": "ناٽڪ", "name_en": "Dramas"},
    "Magazines": {"name_sindhi": "رسالا", "name_en": "Magazines"},
    "Political_Litrature": {"name_sindhi": "سياسيات", "name_en": "Political Literature"},
    "Specialized": {"name_sindhi": "علميات", "name_en": "Specialized / Sciences"},
    "Science_n_Tech": {"name_sindhi": "سائنس ۽ ٽيڪنالوجي", "name_en": "Science & Tech"},
    "Lasaniyat": {"name_sindhi": "لسانيات", "name_en": "Linguistics"},
    "Litrature": {"name_sindhi": "ادب", "name_en": "Literature"},
    "Writers": {"name_sindhi": "ليکڪ", "name_en": "Writers"},
    "english": {"name_sindhi": "انگريزي", "name_en": "English Literature"},
    "Urdu_Farsi": {"name_sindhi": "اڙدو ۽ فارسي ادب", "name_en": "Urdu & Persian Literature"},
    "shaikh_ayaz": {"name_sindhi": "شيخ اياز", "name_en": "Shaikh Ayaz Poetry"},
    "gulphul": {"name_sindhi": "گل ڦل (رسالو)", "name_en": "Gul Phul Magazine"},
    "sartyoon": {"name_sindhi": "سرتيون (رسالو)", "name_en": "Sartyoon Magazine"},
    "mehran": {"name_sindhi": "مهراڻ (رسالو)", "name_en": "Mehran Magazine"},
}


def clean_text(text: str) -> str:
    """Cleans excess whitespace and newlines from extracted text."""
    if not text:
        return ""
    return " ".join(text.split())


def extract_slug_from_url(url: str) -> str:
    """Extracts catalogue slug from URL."""
    match = re.search(r"Catalogue/([^/]+)/", url, re.IGNORECASE)
    if match:
        return match.group(1)
    # Check fallback like Catalogue/Main_Catalog.HTML
    match2 = re.search(r"Catalogue/([^/]+)\.", url, re.IGNORECASE)
    if match2:
        return match2.group(1)
    return "unknown"


def get_all_catalogues(session: ScraperSession, expand_magazines: bool = True) -> list[dict[str, Any]]:
    """
    Scrapes the homepage and extracts all valid catalogues.
    If expand_magazines is True, expands Magazines into Gulphul, Sartyoon, and Mehran.
    """
    logger.info("Fetching homepage to extract catalogues: %s", BASE_URL)
    soup, _ = session.get_soup(BASE_URL)

    catalogues: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    # Find category links from table97 (sidebar) and general links
    table97 = soup.find("table", id="table97")
    search_scope = table97 if table97 else soup

    for a in search_scope.find_all("a", href=True):
        raw_href = a["href"].strip()
        if "catalogue/" not in raw_href.lower():
            continue

        # Skip broken main catalog page
        if "main_catalog" in raw_href.lower():
            continue

        full_url = normalize_url(raw_href, BASE_URL)
        if full_url in seen_urls:
            continue

        slug = extract_slug_from_url(full_url)
        name = clean_text(a.get_text())

        # Fallback to known metadata if link text was empty or incomplete
        meta = KNOWN_CATALOGUES_META.get(slug, {})
        if not name or len(name) < 2:
            name = meta.get("name_sindhi", slug)

        cat_data = {
            "id": slug,
            "slug": slug,
            "name_sindhi": name,
            "name_en": meta.get("name_en", slug.replace("_", " ").title()),
            "url": full_url,
        }
        catalogues.append(cat_data)
        seen_urls.add(full_url)

    # Ensure Shaikh Ayaz is included (often prominent section on homepage)
    shaikh_url = normalize_url("Catalogue/shaikh_ayaz/Main_shaikh_ayaz.HTML", BASE_URL)
    if shaikh_url not in seen_urls:
        meta = KNOWN_CATALOGUES_META["shaikh_ayaz"]
        catalogues.append({
            "id": "shaikh_ayaz",
            "slug": "shaikh_ayaz",
            "name_sindhi": meta["name_sindhi"],
            "name_en": meta["name_en"],
            "url": shaikh_url,
        })
        seen_urls.add(shaikh_url)

    # If expand_magazines is requested, check Magazines page for sub-catalogues
    if expand_magazines:
        mag_cat = next((c for c in catalogues if c["slug"].lower() == "magazines"), None)
        if mag_cat:
            try:
                mag_soup, _ = session.get_soup(mag_cat["url"])
                sub_cats = []
                for sub_a in mag_soup.find_all("a", href=True):
                    sub_href = sub_a["href"].strip()
                    sub_url = normalize_url(sub_href, mag_cat["url"])
                    sub_slug = extract_slug_from_url(sub_url)
                    if sub_slug.lower() in ("gulphul", "sartyoon", "mehran") and sub_url not in seen_urls:
                        sub_meta = KNOWN_CATALOGUES_META.get(sub_slug, {})
                        sub_name = clean_text(sub_a.get_text()) or sub_meta.get("name_sindhi", sub_slug)
                        sub_data = {
                            "id": sub_slug,
                            "slug": sub_slug,
                            "name_sindhi": sub_name,
                            "name_en": sub_meta.get("name_en", sub_slug.title()),
                            "url": sub_url,
                            "parent": "Magazines",
                        }
                        sub_cats.append(sub_data)
                        seen_urls.add(sub_url)
                if sub_cats:
                    catalogues.extend(sub_cats)
            except Exception as e:
                logger.warning("Could not expand magazines: %s", e)

    logger.info("Discovered %d catalogues", len(catalogues))
    return catalogues
