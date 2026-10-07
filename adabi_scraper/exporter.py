import csv
import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """
    Sanitizes string to be safe for filenames across Linux/Windows/macOS.
    Retains Arabic/Sindhi script characters and alphanumeric chars.
    """
    if not name:
        return "untitled"
    # Remove characters not safe in filenames: / \ ? * : " < > |
    safe = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    safe = re.sub(r"\s+", "_", safe)
    if len(safe) > max_length:
        safe = safe[:max_length]
    return safe or "untitled"


def save_catalogues(catalogues: list[dict[str, Any]], output_dir: str) -> dict[str, str]:
    """
    Saves list of all catalogues to catalogues.json and catalogues.txt
    """
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "catalogues.json")
    txt_path = os.path.join(output_dir, "catalogues.txt")

    # 1. JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(catalogues, f, ensure_ascii=False, indent=2)

    # 2. Text summary
    lines = [
        "=" * 90,
        "فهرست: سنڌي ادبي بورڊ لائبريري ڪئٽلاگ (Sindhi Adabi Board Catalogues List)",
        "=" * 90,
        f"{'نمبر':<6}{'ڪئٽلاگ (سنڌي)':<25}{'English Slug':<25}{'URL'}",
        "-" * 90,
    ]

    for i, cat in enumerate(catalogues, start=1):
        s_name = cat.get("name_sindhi", "")
        slug = cat.get("slug", "")
        url = cat.get("url", "")
        lines.append(f"{i:<6}{s_name:<25}{slug:<25}{url}")

    lines.append("=" * 90)
    lines.append(f"مجموعي ڪئٽلاگ: {len(catalogues)}")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("Saved %d catalogues to %s and %s", len(catalogues), json_path, txt_path)
    return {"json": json_path, "txt": txt_path}


def save_books_list(books: list[dict[str, Any]], output_dir: str) -> dict[str, str]:
    """
    Saves list of all discovered books to books.json, books.txt, and books.csv
    """
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "books.json")
    txt_path = os.path.join(output_dir, "books.txt")
    csv_path = os.path.join(output_dir, "books.csv")

    # 1. JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)

    # 2. Text listing grouped by catalogue
    books_by_cat: dict[str, list[dict[str, Any]]] = {}
    for b in books:
        c_name = b.get("catalogue_name") or b.get("catalogue_slug", "Unknown")
        books_by_cat.setdefault(c_name, []).append(b)

    lines = [
        "=" * 90,
        "سنڌي ادبي بورڊ: سمورن ڪتابن جي فهرست (Complete Books List)",
        "=" * 90,
    ]

    counter = 1
    for cat_name, cat_books in books_by_cat.items():
        lines.extend([
            "",
            f"--- ڪئٽلاگ: {cat_name} ({len(cat_books)} ڪتاب) ---",
            "-" * 90,
        ])
        for b in cat_books:
            title = b.get("title") or b.get("book_id", "Unknown")
            b_id = b.get("book_id", "")
            url = b.get("entry_url", "")
            lines.append(f"{counter:>4}. [{b_id}] {title:<40} -> {url}")
            counter += 1

    lines.extend([
        "",
        "=" * 90,
        f"مجموعي ڪتاب: {len(books)}",
    ])

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 3. CSV
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Index", "Book ID", "Title", "Catalogue (Sindhi)", "Catalogue Slug", "Entry URL"])
        for idx, b in enumerate(books, start=1):
            writer.writerow([
                idx,
                b.get("book_id", ""),
                b.get("title", ""),
                b.get("catalogue_name", ""),
                b.get("catalogue_slug", ""),
                b.get("entry_url", ""),
            ])

    logger.info("Saved %d books to %s, %s, and %s", len(books), json_path, txt_path, csv_path)
    return {"json": json_path, "txt": txt_path, "csv": csv_path}


def save_individual_book_file(
    book_data: dict[str, Any],
    output_dir: str,
    output_format: str = "txt"
) -> str:
    """
    Saves an individual book containing all its contents in a single file.
    """
    cat_slug = sanitize_filename(book_data.get("catalogue_slug", "general"))
    book_id = sanitize_filename(book_data.get("book_id", "book"))
    title = sanitize_filename(book_data.get("title", "book"))

    books_dir = os.path.join(output_dir, "books", cat_slug)
    os.makedirs(books_dir, exist_ok=True)

    filename_base = f"{book_id}_{title}"
    if output_format.lower() == "md":
        filename = f"{filename_base}.md"
        content = book_data["full_text"]
    else:
        filename = f"{filename_base}.txt"
        content = book_data["full_text"]

    file_path = os.path.join(books_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Saved single book file: %s (%d pages)", file_path, book_data.get("pages_count", 0))
    return file_path
