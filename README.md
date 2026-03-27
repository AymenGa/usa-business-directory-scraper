# 🏪 USA Business Directory & Marketplace Scraper

A large-scale **Python web scraping** system that builds a comprehensive business directory and marketplace database across **12 categories**, covering **250 US cities** (50 states × 5 cities each).

[![Upwork](https://img.shields.io/badge/Upwork-Freelance%20Project-6fda44?style=for-the-badge&logo=upwork&logoColor=white)](https://www.upwork.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

> 📦 Freelance project delivered on Upwork — 20,000+ data points extracted and organized into professional Excel deliverables.

---

## ⚙️ Features

- Scrapes **two websites per category** (marketplace + business directory)
- Covers **250 cities** across all 50 US states
- Extracts **20,000+ listings** with full business details
- Professional Excel output with formatted cover sheet, filters, and navigation
- Anti-bot protection bypass (CAPTCHA handling, session recovery)
- Crash recovery with checkpointing and resume support
- Global deduplication across all cities
- Two-sheet output per category: **Directory** (businesses) + **Marketplace** (products)

---

## 🏗️ Architecture

Each category follows a **two-website pattern**:

| Source | Purpose | Output |
|--------|---------|--------|
| **Website A** (Marketplace) | Scrape product listings → extract store URLs → visit each store | Marketplace sheet + Directory rows |
| **Website B** (Directory) | Search businesses per city → visit detail pages | Directory rows |

Both sources merge into one **Directory sheet** per category. The marketplace data goes into its own **Marketplace sheet**.

---

## 📊 Output

### Directory Sheet (10 columns)

| State | City | Business Name | Address | Phone | Star Rating | Website | Profile URL | Business Image URL | Source |
|-------|------|---------------|---------|-------|-------------|---------|-------------|-------------------|--------|

### Marketplace Sheet (8 columns)

| State | City | Store Name | Item Description | Price | Star Rating | Product URL | Product Photo URL |
|-------|------|------------|-----------------|-------|-------------|-------------|------------------|

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **Selenium / undetected-chromedriver** — stealth browser automation
- **BeautifulSoup4** — HTML parsing and data extraction
- **OpenPyXL** — professional Excel generation with formatting
- **Pandas** — data processing and deduplication

---

## 🚀 Installation

```bash
git clone https://github.com/AymenGa/usa-business-directory-scraper.git
cd usa-business-directory-scraper
pip install -r scraper/requirements.txt
```

---

## 🧩 Usage

```bash
# Test mode (1 state, quick validation)
python scraper/fashion/etsy_products.py --test

# Full run (all 250 cities)
python scraper/fashion/etsy_products.py
```

Each category has its own scraper folder with separate scripts for marketplace and directory extraction.

---

## 📁 Project Structure

```
scraper/
├── build_excel.py               ← builds results.xlsx (cover + 2 sheets per category)
├── requirements.txt
├── YELP_REFERENCE.md            ← Yelp-specific scraping patterns
├── fashion/                     ← Fashion / Accessories
│   ├── etsy_products.py         ← marketplace items from Etsy
│   ├── etsy_shops.py            ← store profiles → directory rows
│   └── yelp.py                  ← directory businesses from Yelp
├── electronics/                 ← Electronics / Gadgets
│   └── ...
└── ...                          ← one folder per category
```

---

## 🔧 Anti-Bot Techniques

- **undetected-chromedriver** with stealth Chrome options
- Random delays between requests (variable intervals)
- CAPTCHA detection and automatic retry with session refresh
- Crash recovery: driver health checks, per-target error handling
- Checkpoint system: saves progress every N targets, resumes on restart
- Fresh browser sessions after repeated blocks

---

## 📋 Categories (12 Milestones)

1. Fashion / Accessories ✅
2. Electronics / Gadgets
3. Home and Garden
4. Toys and Games
5. Health and Beauty
6. Digital Products
7. Automotive
8. Food and Groceries
9. Sports and Outdoors
10. Books and Media
11. Arts and Crafts
12. Professional Services

---

## 👤 Author

**Aymen Gacem**

[![Upwork](https://img.shields.io/badge/Upwork-Profile-6fda44?style=flat&logo=upwork)](https://www.upwork.com)
[![GitHub](https://img.shields.io/badge/GitHub-AymenGa-181717?style=flat&logo=github)](https://github.com/AymenGa)

---

## 📄 License

This project is **not open source**. See [LICENSE](LICENSE) for details.
Viewing and learning permitted — commercial use and redistribution prohibited.
