# Sindhi Adabi Board Scraper (سنڌي ادبي بورڊ ڪتاب اسڪريپر)

An automated, robust web scraper for the **Sindhi Adabi Board Online Library** ([http://www.sindhiadabiboard.org/](http://www.sindhiadabiboard.org/)).

---

## 📖 English Documentation

### Overview
This tool scrapes books and publications from the official Sindhi Adabi Board online library. It works in three distinct, structured phases:
1. **Lists All Catalogues First**: Automatically extracts and saves all 29 library categories (دينيات, تاريخ, فلسفو, لوڪ ادب, ناول, شاعري, رسالا, etc.) into `catalogues.json` and `catalogues.txt`.
2. **Lists All Books**: Traverses each catalogue (including multi-page pagination like `بقايا ڪتاب`) to discover over **1,060+ books and magazines**, saving them into `books.json`, `books.txt`, and `books.csv`.
3. **Generates Individual Files for Books**: Downloads every page of a book and compiles all contents into a **single clean file per book** (`.txt` or `.md`), including metadata (Title, Author, Year, Edition, Publisher, Intro).

### Features
- **Strict Phased Execution**: Always discovers and lists all catalogues first before downloading.
- **Single-File Book Compilation**: Every page of a book is collated in numerical order into one consolidated document.
- **Metadata Extraction**: Parses author, publication year, edition, and publisher from `aboutbook.htm` and title pages.
- **Robust Networking**: Resilient retry session with exponential backoff and timeout handling to safely handle legacy web servers.
- **RTL & Unicode Cleaning**: Strips navigation banners, iframes, footers, and redundant whitespace while maintaining clean Sindhi RTL text.
- **Flexible Filters**: Scrape by category slug/name, single book URL, limit pages, or resume interrupted downloads.

### System Requirements
- Python 3.10+
- `pip` package manager
- Internet connection

### Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/sajjad22/sindhiadabiboard_scrapper.git
   cd sindhiadabiboard_scrapper
   ```
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage & Examples

#### 1. Discover & List Catalogues Only
Lists all 29 categories to console and saves to `output/catalogues.json` and `output/catalogues.txt`:
```bash
python3 scraper.py --list-catalogues
```

#### 2. Discover & List All Books Across All Categories
Scrapes categories first, then discovers all 1,060+ books and exits:
```bash
python3 scraper.py --list-books
```

#### 3. Scrape Books for a Specific Category
Scrape books in the `Dictionaries` (`لغات`) category:
```bash
python3 scraper.py --catalogue Dictionaries
```
Or by Sindhi name:
```bash
python3 scraper.py --catalogue "دينيات"
```

#### 4. Test Scrape (Limited Books & Pages)
Download 2 books, with a limit of 3 pages per book:
```bash
python3 scraper.py --catalogue Philosophy --limit-books 2 --limit-pages 3
```

#### 5. Download a Single Specific Book
Provide the book's direct URL:
```bash
python3 scraper.py --book-url "http://www.sindhiadabiboard.org/Catalogue/Religion/Book4/Book_page1.html"
```

#### 6. Resume Interrupted Download
Skips books that are already saved to disk:
```bash
python3 scraper.py --resume
```

#### 7. Change Format or Output Directory
Save books as Markdown (`.md`) in a custom folder:
```bash
python3 scraper.py --format md --output-dir ./my_books
```

### Output File Structure
```
output/
├── catalogues.json           # All 29 catalogues in JSON
├── catalogues.txt            # Formatted text table of catalogues
├── books.json                # Complete list of all books with URLs
├── books.txt                 # Text listing grouped by category
├── books.csv                 # Spreadsheet-friendly CSV list
└── books/                    # Individual book files
    ├── Religion/
    │   ├── Book1_شان_رسول.txt
    │   └── Book4_نماز_جنت_جي_ڪنجي.txt
    ├── History/
    │   └── Book1_چچ_نامو.txt
    └── Dictionaries/
        ├── Book1_پرنٽ_ٽيڪنالوجي.txt
        └── Book2_لغات_سنڌي_مخففات.txt
```

---

## 📖 سنڌي رهنمائي (Sindhi Documentation)

### تعارف
هي اسڪريپر **سنڌي ادبي بورڊ جي آن لائين لائبريري** مان ڪتاب ڊائون لوڊ ڪرڻ لاءِ ٺاهيو ويو آهي. هي ٽول ٽن اهم مرحلن ۾ ڪم ڪري ٿو:
1. **پهرين سڀني ڪئٽلاگن جي فهرست تيار ڪري ٿو**: ويب سائيٽ جي سمورن 29 ڪئٽلاگن (دينيات، تاريخ، فلسفو، لوڪ ادب، ناول، شاعري، رسالا وغيره) کي ڳولي `catalogues.json` ۽ `catalogues.txt` ۾ محفوظ ڪري ٿو.
2. **سمورن ڪتابن جي فهرست گڏ ڪري ٿو**: هر هڪ ڪئٽلاگ مان سمورن **1060+ ڪتابن ۽ رسالن** جا لنڪس ۽ نالا ڳولي `books.json`، `books.txt` ۽ `books.csv` فائلن ۾ محفوظ ڪري ٿو.
3. **هر ڪتاب جو سمورو مواد هڪ ئي فائل ۾ محفوظ ڪري ٿو**: هر ڪتاب جا سمورا صفحا ترتيب سان گڏ ڪري، مٿان ڪتاب جو نالو، ليکڪ، سال، ڇپائيندڙ ۽ تعارف لکي، **هڪ ئي مڪمل فائل** تيار ڪري ٿو.

### اهم خاصيتون
- **ڪئٽلاگ پهرين ڏيکاري ٿو**: هدايت موجب، اسڪريپر سڀ کان اڳ سمورن ڪئٽلاگن کي دريافت ڪري محفوظ ڪري ٿو.
- **هڪ ڪتاب، هڪ فائل**: ڪتاب جا سمورا صفحا (مثال طور 50 صفحا) الڳ الڳ رهڻ بدران، هڪ ئي صاف سٿري فائل ۾ گڏ ٿين ٿا.
- **معلومات (Metadata)**: ڪتاب جو نالو، مصنف، ايڊيشن، سال، صفحا ۽ تفصيل پاڻمرادو محفوظ ٿين ٿا.
- **صاف سٿري سنڌي عبارت**: پيج جا غير ضروري بٽڻ، اشتهار ۽ مينيو ڪڍي رڳو ڪتاب جو اصل سنڌي متن پيش ڪري ٿو.
- **رڪاوٽ کان پوءِ ٻيهر شروعات (--resume)**: جيڪڏهن ڪي ڪتاب اڳي ئي ڊائون لوڊ ٿيل هجن ته انهن کي ڇڏي باقي نوان ڪتاب کڻي ٿو.

### ضرورتون (Requirements)
- پائٿن (Python 3.10 يا مٿي)
- انٽرنيٽ ڪنيڪشن

### انسٽاليشن
1. ڪوڊ ڊائون لوڊ ڪريو:
   ```bash
   git clone https://github.com/sajjad22/sindhiadabiboard_scrapper.git
   cd sindhiadabiboard_scrapper
   ```
2. ضروري پئڪيجز انسٽال ڪريو:
   ```bash
   pip install -r requirements.txt
   ```

### ڪيئن استعمال ڪجي (Examples)

#### 1. رڳو ڪئٽلاگن جي لسٽ ڏسڻ ۽ محفوظ ڪرڻ:
```bash
python3 scraper.py --list-catalogues
```

#### 2. لائبريري جي سمورن ڪتابن جي فهرست تيار ڪرڻ:
```bash
python3 scraper.py --list-books
```

#### 3. ڪنهن خاص ڪئٽلاگ جا ڪتاب ڊائون لوڊ ڪرڻ:
```bash
python3 scraper.py --catalogue "تاريخ"
```
يا انگريزي نالي سان:
```bash
python3 scraper.py --catalogue History
```

#### 4. چڪاس (Test) لاءِ ٿورا ڪتاب کڻڻ:
```bash
python3 scraper.py --catalogue Philosophy --limit-books 2 --limit-pages 3
```

#### 5. رڳو هڪ خاص ڪتاب لنڪ ذريعي حاصل ڪرڻ:
```bash
python3 scraper.py --book-url "http://www.sindhiadabiboard.org/Catalogue/Religion/Book4/Book_page1.html"
```

#### 6. مارڪ ڊائون (.md) فارميٽ ۾ محفوظ ڪرڻ:
```bash
python3 scraper.py --format md
```

---

## ⚖️ اخلاقي استعمال (Ethical Scraping)
هي ٽول تحقيقي ۽ ادبي مقصدن لاءِ تعليمي مدد طور ٺاهيو ويو آهي. مھرباني ڪري سرور تي اضافي بار نه وجهو؛ اسڪريپر ۾ پاڻمرادو وقفو (`--delay`) شامل آهي.

---

## 👤 ڪوڊ ليکڪ / Author
- **GitHub**: [@sajjad22](https://github.com/sajjad22)
- **Repository**: [https://github.com/sajjad22/sindhiadabiboard_scrapper](https://github.com/sajjad22/sindhiadabiboard_scrapper)
- **Email**: sajjad224@gmail.com
