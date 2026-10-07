#!/usr/bin/env python3
"""
Sindhi Adabi Board Scraper (https://www.sindhiadabiboard.org/)

Produces:
1. List of all catalogues (listed first).
2. List of all books.
3. Individual files for books (each book contains all its contents in a single file).
"""

import argparse
import logging
import os
import sys
import time

from adabi_scraper.session import ScraperSession
from adabi_scraper.catalogues import get_all_catalogues
from adabi_scraper.books import get_books_in_catalogue, get_all_books_across_catalogues
from adabi_scraper.reader import scrape_full_book
from adabi_scraper.exporter import (
    save_catalogues,
    save_books_list,
    save_individual_book_file,
    sanitize_filename,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("scraper")


def print_banner():
    print("=" * 80)
    print("    سندھي ادبي بورڊ ڪتاب اسڪريپر (Sindhi Adabi Board Scraper)    ")
    print("    Official Website: http://www.sindhiadabiboard.org/    ")
    print("=" * 80)


def print_catalogues_console(catalogues: list[dict]):
    print("\n" + "=" * 80)
    print("PHASE 1: ڪئٽلاگن جي فهرست (LIST OF ALL CATALOGUES)")
    print("=" * 80)
    print(f"{'#':<4} {'ڪئٽلاگ (سنڌي)':<25} {'Slug / Category':<22} {'URL'}")
    print("-" * 80)
    for i, cat in enumerate(catalogues, start=1):
        s_name = cat.get("name_sindhi", "")
        slug = cat.get("slug", "")
        url = cat.get("url", "")
        print(f"{i:<4} {s_name:<25} {slug:<22} {url}")
    print("-" * 80)
    print(f"ڪل ڪئٽلاگ: {len(catalogues)}\n")


def print_books_console(books: list[dict]):
    print("\n" + "=" * 80)
    print("PHASE 2: دريافت ٿيل ڪتابن جي فهرست (LIST OF ALL BOOKS)")
    print("=" * 80)
    # Group by catalogue
    books_by_cat = {}
    for b in books:
        c_name = b.get("catalogue_name") or b.get("catalogue_slug", "General")
        books_by_cat.setdefault(c_name, []).append(b)

    total = 0
    for c_name, c_books in books_by_cat.items():
        print(f"• {c_name}: {len(c_books)} ڪتاب")
        for b in c_books[:5]:
            title = b.get("title") or b.get("book_id", "")
            print(f"    - [{b.get('book_id')}] {title}")
        if len(c_books) > 5:
            print(f"    ... ۽ ٻيا {len(c_books) - 5} ڪتاب")
        total += len(c_books)
    print("-" * 80)
    print(f"ڪل ڪتاب (Total Books): {total}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Scraper for Sindhi Adabi Board Online Library (http://www.sindhiadabiboard.org/)"
    )
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="Directory to save catalogues, books lists, and book files (default: ./output)",
    )
    parser.add_argument(
        "--list-catalogues",
        action="store_true",
        help="Only discover and list catalogues, then exit",
    )
    parser.add_argument(
        "--list-books",
        action="store_true",
        help="Discover catalogues first, then list all books and exit",
    )
    parser.add_argument(
        "--catalogue",
        type=str,
        default=None,
        help="Filter to a specific catalogue by Sindhi name or slug (e.g. Religion, History, دينيات)",
    )
    parser.add_argument(
        "--book-url",
        type=str,
        default=None,
        help="Scrape a single book directly by its URL (e.g. .../Book4/Book_page1.html)",
    )
    parser.add_argument(
        "--limit-catalogues",
        type=int,
        default=None,
        help="Limit the number of catalogues to process",
    )
    parser.add_argument(
        "--limit-books",
        type=int,
        default=None,
        help="Limit the number of books to scrape across catalogues",
    )
    parser.add_argument(
        "--limit-pages",
        type=int,
        default=None,
        help="Limit number of pages per book (useful for quick testing)",
    )
    parser.add_argument(
        "--format",
        choices=["txt", "md"],
        default="txt",
        help="File format for individual books (txt or md, default: txt)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Delay in seconds between HTTP requests (default: 0.2)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip books that have already been saved to disk",
    )

    args = parser.parse_args()
    print_banner()

    session = ScraperSession(delay=args.delay)
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # -------------------------------------------------------------
    # PHASE 1: Discover and List All Catalogues First
    # -------------------------------------------------------------
    print("[1/3] لائبريريءَ مان سمورا ڪئٽلاگ گڏ ڪيا پيا وڃن (Discovering catalogues)...")
    catalogues = get_all_catalogues(session)

    # Save catalogues to output directory
    cat_files = save_catalogues(catalogues, output_dir)
    print_catalogues_console(catalogues)
    print(f"✓ Catalogues saved to:\n  - {cat_files['json']}\n  - {cat_files['txt']}")

    if args.list_catalogues:
        print("\n[+] Catalogue listing completed successfully (--list-catalogues specified).")
        return

    # Filter catalogues if requested
    target_catalogues = catalogues
    if args.catalogue:
        filter_term = args.catalogue.strip().lower()
        target_catalogues = [
            c for c in catalogues
            if filter_term in c.get("slug", "").lower()
            or filter_term in c.get("name_sindhi", "").lower()
            or filter_term in c.get("name_en", "").lower()
        ]
        if not target_catalogues:
            print(f"\n[!] ڪو به ڪئٽلاگ نه مليو: '{args.catalogue}' (No catalogue matched filter).")
            print("Available catalogue slugs:")
            for c in catalogues:
                print(f"  - {c['slug']} ({c['name_sindhi']})")
            sys.exit(1)
        print(f"\nFilter applied: Processing {len(target_catalogues)} catalogue(s).")

    if args.limit_catalogues:
        target_catalogues = target_catalogues[:args.limit_catalogues]

    # -------------------------------------------------------------
    # PHASE 2: Discover and List All Books Across Catalogues
    # -------------------------------------------------------------
    print("\n[2/3] ڪئٽلاگن مان ڪتاب گڏ ڪيا پيا وڃن (Discovering books across catalogues)...")
    all_books = []
    for cat in target_catalogues:
        print(f" -> ڪئٽلاگ چيڪ ٿي رهيو آهي: {cat['name_sindhi']} ({cat['slug']})...")
        cat_books = get_books_in_catalogue(session, cat)
        all_books.extend(cat_books)

    book_files = save_books_list(all_books, output_dir)
    print_books_console(all_books)
    print(f"✓ Books list saved to:\n  - {book_files['json']}\n  - {book_files['txt']}\n  - {book_files['csv']}")

    if args.list_books:
        print("\n[+] Books listing completed successfully (--list-books specified).")
        return

    # -------------------------------------------------------------
    # PHASE 3: Download and Generate Individual Files for Books
    # -------------------------------------------------------------
    # Handle single book URL override if provided
    books_to_download = all_books
    if args.book_url:
        books_to_download = [{
            "book_id": "CustomBook",
            "catalogue_slug": "custom",
            "catalogue_name": "ڪسٽم",
            "title": "ڪتاب",
            "entry_url": args.book_url,
            "about_url": "",
        }]

    if args.limit_books:
        books_to_download = books_to_download[:args.limit_books]

    total_download = len(books_to_download)
    print(f"\n[3/3] سمورن ڪتابن جا الڳ فائل تيار ڪيا پيا وڃن (Generating individual files for {total_download} books)...")
    print(f"      Each book will contain all its contents in a single file under: {os.path.join(output_dir, 'books')}/\n")

    saved_files = []
    for idx, b_info in enumerate(books_to_download, start=1):
        b_title = b_info.get("title") or b_info.get("book_id", "Book")
        cat_slug = sanitize_filename(b_info.get("catalogue_slug", "general"))
        book_id = sanitize_filename(b_info.get("book_id", "book"))
        safe_title = sanitize_filename(b_title)
        expected_path = os.path.join(output_dir, "books", cat_slug, f"{book_id}_{safe_title}.{args.format}")

        if args.resume and os.path.exists(expected_path):
            print(f"[{idx}/{total_download}] ⏭ اڳ ۾ موجود آهي (Skipping existing): {b_title}")
            saved_files.append(expected_path)
            continue

        print(f"[{idx}/{total_download}] 📖 ڪتاب ڊائون لوڊ ٿي رهيو آهي: {b_title} ({b_info.get('entry_url')})")
        t0 = time.time()
        try:
            full_book_data = scrape_full_book(session, b_info, limit_pages=args.limit_pages)
            saved_file_path = save_individual_book_file(full_book_data, output_dir, output_format=args.format)
            elapsed = time.time() - t0
            print(f"         ✓ محفوظ ٿي ويو ({full_book_data['pages_count']} صفحا, {elapsed:.1f}s): {saved_file_path}")
            saved_files.append(saved_file_path)
        except Exception as e:
            logger.error("Failed to scrape book '%s': %s", b_title, e)

    print("\n" + "=" * 80)
    print("ڪم مڪمل ٿي ويو! (SCRAPING COMPLETED SUCCESSFULLY)")
    print("=" * 80)
    print(f"1. ڪئٽلاگن جي فهرست (Catalogues List): {cat_files['txt']}")
    print(f"2. ڪتابن جي فهرست (Books List): {book_files['txt']}")
    print(f"3. ڪتابن جا الڳ فائل (Individual Book Files): {len(saved_files)} files in {os.path.join(output_dir, 'books')}/")
    print("=" * 80)


if __name__ == "__main__":
    main()
