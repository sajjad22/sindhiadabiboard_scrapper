import csv
import html
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


def generate_book_html(book_data: dict[str, Any]) -> str:
    """
    Generates a clean, standalone, responsive RTL HTML5 document for the book.
    """
    title = book_data.get("title", "ڪتاب")
    author = book_data.get("author", "سنڌي ادبي بورڊ")
    cat_name = book_data.get("catalogue_name", "")
    cat_slug = book_data.get("catalogue_slug", "")
    entry_url = book_data.get("entry_url", "")
    metadata = book_data.get("metadata", {})
    pages = book_data.get("pages", [])
    intro = metadata.get("intro", "")

    # Build metadata items
    meta_items_html = [
        f'<div class="meta-item"><span class="meta-label">ڪتاب جو نالو:</span> <span class="meta-val">{title}</span></div>',
        f'<div class="meta-item"><span class="meta-label">مصنف / مرتب:</span> <span class="meta-val">{author}</span></div>',
        f'<div class="meta-item"><span class="meta-label">ڪئٽلاگ:</span> <span class="meta-val">{cat_name} ({cat_slug})</span></div>',
    ]
    if metadata.get("edition"):
        meta_items_html.append(f'<div class="meta-item"><span class="meta-label">ايڊيشن:</span> <span class="meta-val">{metadata["edition"]}</span></div>')
    if metadata.get("year"):
        meta_items_html.append(f'<div class="meta-item"><span class="meta-label">سال:</span> <span class="meta-val">{metadata["year"]}</span></div>')
    if metadata.get("publisher"):
        meta_items_html.append(f'<div class="meta-item"><span class="meta-label">ڇپائيندڙ:</span> <span class="meta-val">{metadata["publisher"]}</span></div>')
    meta_items_html.append(f'<div class="meta-item"><span class="meta-label">ڊائون لوڊ ٿيل صفحا:</span> <span class="meta-val">{len(pages)}</span></div>')

    # Build intro block
    intro_html = ""
    if intro:
        intro_html = f'''
        <div class="intro-box">
          <div class="intro-title">ڪتاب جو تعارف</div>
          <p>{intro}</p>
        </div>'''

    # Build TOC page badges
    toc_badges = []
    for p in pages:
        p_num = p.get("page_number", 1)
        toc_badges.append(f'<a class="page-badge" href="#page-{p_num}">{p_num}</a>')
    toc_html = "".join(toc_badges)

    # Build pages content
    pages_html = []
    for p in pages:
        p_num = p.get("page_number", 1)
        p_hdr = p.get("header_meta", "")
        blocks = p.get("blocks")
        if not blocks:
            raw_content = p.get("content", "")
            blocks = [b.strip() for b in raw_content.split("\n\n") if b.strip()]

        elements_html = []
        for block in blocks:
            if " | " in block:
                rows = [r.split(" | ") for r in block.split("\n") if r.strip()]
                grid_rows = "".join(f"<tr>{''.join(f'<td>{html.escape(cell.strip())}</td>' for cell in row)}</tr>" for row in rows)
                elements_html.append(f'<table class="data-grid">{grid_rows}</table>')
            else:
                lines = [html.escape(line.strip()) for line in block.split("\n") if line.strip()]
                if lines:
                    inner = "<br>\n".join(lines)
                    elements_html.append(f"<p>{inner}</p>")

        page_body = "\n".join(elements_html)

        hdr_meta_span = f'<span class="page-section-meta">{p_hdr}</span>' if p_hdr else ""

        pages_html.append(f'''
      <article class="book-page" id="page-{p_num}">
        <div class="page-header">
          <span class="page-badge-label">صفحو : {p_num}</span>
          {hdr_meta_span}
        </div>
        <div class="page-content">
          {page_body}
        </div>
      </article>''')

    all_pages_body = "\n".join(pages_html)

    html_template = f'''<!DOCTYPE html>
<html lang="sd" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - سنڌي ادبي بورڊ</title>
  <style>
    :root {{
      --primary-color: #1a5276;
      --accent-color: #2980b9;
      --bg-color: #f8fafc;
      --card-bg: #ffffff;
      --text-color: #2c3e50;
      --border-color: #e2e8f0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: 'Noto Sans Arabic', 'Lateef', 'Scheherazade New', 'Adabi', 'Traditional Arabic', serif;
      background-color: var(--bg-color);
      color: var(--text-color);
      line-height: 2.2;
      font-size: 1.25rem;
      margin: 0;
      padding: 25px 15px;
      direction: rtl;
      text-align: right;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
      background: var(--card-bg);
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.06);
      padding: 35px 30px;
    }}
    header.book-header {{
      border-bottom: 3px double var(--border-color);
      padding-bottom: 25px;
      margin-bottom: 30px;
    }}
    h1.book-title {{
      font-size: 2.2rem;
      color: var(--primary-color);
      margin: 0 0 15px 0;
      line-height: 1.4;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      background: #f1f5f9;
      padding: 16px;
      border-radius: 8px;
      font-size: 1.05rem;
    }}
    .meta-item {{ display: flex; gap: 8px; }}
    .meta-label {{ font-weight: bold; color: #475569; }}
    .meta-val {{ color: #0f172a; }}
    .intro-box {{
      background: #eff6ff;
      border-right: 4px solid var(--accent-color);
      padding: 18px;
      margin: 25px 0;
      border-radius: 6px;
      font-size: 1.15rem;
    }}
    .intro-title {{
      font-weight: bold;
      color: var(--primary-color);
      margin-bottom: 8px;
    }}
    .toc-nav {{
      background: #fafafa;
      border: 1px solid var(--border-color);
      padding: 15px;
      border-radius: 8px;
      margin-bottom: 35px;
    }}
    .toc-title {{
      font-weight: bold;
      margin-bottom: 10px;
      color: #334155;
      font-size: 1.1rem;
    }}
    .page-badges {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      max-height: 160px;
      overflow-y: auto;
      padding: 4px;
    }}
    .page-badge {{
      display: inline-block;
      padding: 3px 10px;
      background: #e2e8f0;
      color: #1e293b;
      text-decoration: none;
      border-radius: 4px;
      font-size: 0.95rem;
      transition: background 0.2s;
    }}
    .page-badge:hover {{ background: var(--accent-color); color: #fff; }}
    article.book-page {{
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 25px;
      margin-bottom: 30px;
      background: #ffffff;
      box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }}
    .page-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #edf2f7;
      padding-bottom: 10px;
      margin-bottom: 20px;
    }}
    .page-badge-label {{
      background: var(--primary-color);
      color: #ffffff;
      padding: 2px 14px;
      border-radius: 14px;
      font-size: 0.95rem;
      font-weight: bold;
    }}
    .page-section-meta {{
      font-size: 0.95rem;
      color: #64748b;
    }}
    .page-content p {{
      margin: 0 0 1.2em 0;
      text-align: justify;
      line-height: 2.2;
    }}
    .data-grid {{
      margin: 20px auto;
      border-collapse: collapse;
      text-align: center;
      width: 100%;
      max-width: 650px;
    }}
    .data-grid td {{
      border: 1px solid var(--border-color);
      padding: 6px 12px;
      font-size: 1.15rem;
    }}
    footer.book-footer {{
      border-top: 2px solid var(--border-color);
      padding-top: 20px;
      margin-top: 40px;
      text-align: center;
      font-size: 0.95rem;
      color: #64748b;
    }}
    @media print {{
      body {{ background: #fff; padding: 0; font-size: 12pt; }}
      .container {{ box-shadow: none; padding: 0; max-width: 100%; }}
      .toc-nav {{ display: none; }}
      article.book-page {{ page-break-after: always; border: none; box-shadow: none; padding: 10px 0; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header class="book-header">
      <h1 class="book-title">{title}</h1>
      <div class="meta-grid">
        {"".join(meta_items_html)}
      </div>
      {intro_html}
    </header>

    <nav class="toc-nav">
      <div class="toc-title">صفحن جي فهرست (Jump to Page):</div>
      <div class="page-badges">
        {toc_html}
      </div>
    </nav>

    <main class="book-content">
{all_pages_body}
    </main>

    <footer class="book-footer">
      <p>اصل ماخذ: <a href="{entry_url}" target="_blank" rel="noopener noreferrer">{entry_url}</a></p>
      <p>© Sindhi Adabi Board, Jamshoro | سنڌي ادبي بورڊ، ڄامشورو</p>
    </footer>
  </div>
</body>
</html>'''
    return html_template


def save_individual_book_file(
    book_data: dict[str, Any],
    output_dir: str,
    output_format: str = "txt"
) -> list[str]:
    """
    Saves an individual book containing all its contents in a single file.
    Supports output_format: 'txt', 'html', 'md', or 'all'
    Returns list of saved file paths.
    """
    cat_slug = sanitize_filename(book_data.get("catalogue_slug", "general"))
    book_id = sanitize_filename(book_data.get("book_id", "book"))
    title = sanitize_filename(book_data.get("title", "book"))

    books_dir = os.path.join(output_dir, "books", cat_slug)
    os.makedirs(books_dir, exist_ok=True)

    filename_base = f"{book_id}_{title}"
    saved_paths = []
    fmt = output_format.lower().strip()

    # Determine formats to output
    save_txt = fmt in ("txt", "all", "both")
    save_html = fmt in ("html", "all", "both")
    save_md = fmt in ("md",)

    if save_txt:
        txt_path = os.path.join(books_dir, f"{filename_base}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(book_data["full_text"])
        saved_paths.append(txt_path)
        logger.info("Saved single book file (TXT): %s (%d pages)", txt_path, book_data.get("pages_count", 0))

    if save_html:
        html_path = os.path.join(books_dir, f"{filename_base}.html")
        html_content = generate_book_html(book_data)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        saved_paths.append(html_path)
        logger.info("Saved single book file (HTML): %s (%d pages)", html_path, book_data.get("pages_count", 0))

    if save_md:
        md_path = os.path.join(books_dir, f"{filename_base}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(book_data["full_text"])
        saved_paths.append(md_path)
        logger.info("Saved single book file (MD): %s (%d pages)", md_path, book_data.get("pages_count", 0))

    return saved_paths
