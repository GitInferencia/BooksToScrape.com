
#!/usr/bin/env python3
"""
============================================================
  Proyecto 1 — Sitio Books.toscrape.com
============================================================
  Voy por la información de nombres, precios y ratings de los libros que estan
  en este sitio estatico de prueba

  Lenguaje: python
   
============================================================
"""

import requests
from lxml import html
from collections import Counter
import time
import os

# ─────────────────────────────────────────────────────────────────
# configuracion
# ─────────────────────────────────────────────────────────────────
BASE_URL        = 'https://books.toscrape.com/'
INDEX_URL       = 'https://books.toscrape.com/index.html'
CATEGORIES_FILE = 'BookCategorie.txt'
BOOKS_FILE      = 'Books.txt'
DELAY           = 0.4         
CATEGORY_LIMIT  = 5     # Dejar en blanco si quieres obtener todas las categorías

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}

RATING_MAP = {
    'One':   1,
    'Two':   2,
    'Three': 3,
    'Four':  4,
    'Five':  5
}

# ─────────────────────────────────────────────────────────────────
# Funciones de apoyo
# ─────────────────────────────────────────────────────────────────
def get_page(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return html.fromstring(response.content)
    except requests.RequestException as e:
        print(f'  ⚠️  Error fetching {url}: {e}')
        return None
def clean(text):
    return text.strip() if text else ''

def get_rating(article):
    el = article.xpath('.//p[contains(@class, "star-rating")]')
    if el:
        for cls in el[0].get('class', '').split():
            if cls in RATING_MAP:
                return RATING_MAP[cls]
    return 0

def get_next_url(tree, current_url):
    nxt = tree.xpath('.//li[@class="next"]/a')
    if nxt:
        href = nxt[0].get('href', '')
        base = current_url.rsplit('/', 1)[0]
        return base + '/' + href
    return None


# ─────────────────────────────────────────────────────────────────
# Paso 1 — Obtengo categorias
# ─────────────────────────────────────────────────────────────────
def scrape_categories():
    print('🔍 Fetching main page to extract categories...')
    tree = get_page(INDEX_URL)
    if tree is None:
        print('❌ Could not load main page.')
        return []

    items = tree.xpath(
        '//*[@id="default"]/div/div/div/aside/div[2]/ul/li/ul/li'
    )

    categories = []
    for idx, li in enumerate(items, start=1):
        a = li.xpath('.//a')
        if a:
            categories.append({
                'id'  : idx,
                'name': clean(a[0].text_content()),
                'url' : BASE_URL + a[0].get('href', '')
            })

    print(f'✅ Found {len(categories)} categories')
    return categories


def save_categories(categories, filepath=CATEGORIES_FILE):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('id|name\n')
        f.write('-' * 40 + '\n')
        for cat in categories:
            f.write(f"{cat['id']}|{cat['name']}\n")
    print(f'✅ Saved {len(categories)} categories → "{filepath}"')


# ─────────────────────────────────────────────────────────────────
# Paso 2— SCRAPE los libros de cada categoria incluyendo la paginacion
# ─────────────────────────────────────────────────────────────────
def scrape_books_from_page(tree):
    books    = []
    articles = tree.xpath(
        '//*[@id="default"]/div/div/div/div/section/div[2]/ol/li/article'
    )

    for article in articles:
        # Name — prefer 'title' attribute (full, non-truncated)
        name_el = article.xpath('.//h3/a')
        name    = (name_el[0].get('title') or
                   clean(name_el[0].text_content())) if name_el else 'N/A'

        # Price
        price_el = article.xpath('.//div[contains(@class,"product_price")]/p[1]')
        if price_el:
            price = clean(price_el[0].text_content())
        else:
            fallback = article.xpath('.//p[contains(text(),"£")]')
            price    = clean(fallback[0].text_content()) if fallback else 'N/A'

        # Rating
        rating = get_rating(article)
        stars  = '★' * rating + '☆' * (5 - rating)

        books.append({
            'name'  : name,
            'price' : price,
            'rating': rating,
            'stars' : stars
        })

    return books


def scrape_category_books(category):
    all_books = []
    page_url  = category['url']
    page_num  = 1

    while page_url:
        tree = get_page(page_url)
        if tree is None:
            break

        page_books = scrape_books_from_page(tree)
        all_books.extend(page_books)
        print(f'    Page {page_num}: {len(page_books)} books', end='')

        nxt = get_next_url(tree, page_url)
        if nxt:
            print(f' → next page')
            page_url = nxt
            page_num += 1
            time.sleep(DELAY)
        else:
            print(' (last page)')
            break

    for book in all_books:
        book['category_id'] = category['id']

    return all_books


def scrape_all_books(categories):
    all_books = []
    total     = len(categories)

    for i, cat in enumerate(categories, start=1):
        print(f'\n[{i:>2}/{total}] 📂 {cat["name"]}')
        books = scrape_category_books(cat)
        all_books.extend(books)
        print(f'         ✔ {len(books)} books collected')
        time.sleep(DELAY)

    print(f'\n🎉 Done! Total books collected: {len(all_books)}')
    return all_books


def save_books(all_books, categories, filepath=BOOKS_FILE):
    cat_lookup = {cat['id']: cat['name'] for cat in categories}

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('category_id|category_name|book_name|price|rating|stars\n')
        f.write('-' * 90 + '\n')
        for book in all_books:
            cat_id   = book.get('category_id', 0)
            cat_name = cat_lookup.get(cat_id, 'Unknown')
            f.write(
                f"{cat_id}|{cat_name}|{book['name']}|"
                f"{book['price']}|{book['rating']}|{book['stars']}\n"
            )

    print(f'✅ Saved {len(all_books)} books → "{filepath}"')


# ─────────────────────────────────────────────────────────────────
# Paso 3 — Estadisticas
# ─────────────────────────────────────────────────────────────────
def print_stats(all_books):

    def to_float(p):
        try:
            return float(p.replace('£', '').replace('£', '').strip())
        except Exception:
            return 0.0

    print('\n' + '=' * 55)
    print('  📊  SCRAPING SUMMARY')
    print('=' * 55)
    print(f'  Total books : {len(all_books)}')

    # Rating
    rc = Counter(b['rating'] for b in all_books)
    print('\n  ⭐ Rating distribution:')
    for s in range(5, 0, -1):
        bar = '█' * (rc[s] // 5)
        print(f'    {s}★  {rc[s]:>4} books  {bar}')

    # Los 5 mas caros
    sb = sorted(all_books, key=lambda b: to_float(b['price']), reverse=True)
    print('\n  💰 Top 5 most expensive:')
    for b in sb[:5]:
        print(f"    {b['price']:>8}  {b['name'][:50]}")

    # Los 5 mas baratos
    sc = sorted(all_books, key=lambda b: to_float(b['price']))
    print('\n  🏷️  Top 5 cheapest:')
    for b in sc[:5]:
        print(f"    {b['price']:>8}  {b['name'][:50]}")

    print('=' * 55)
    print(f'  Files saved:')
    print(f'    📁 {CATEGORIES_FILE}')
    print(f'    📁 {BOOKS_FILE}')
    print('=' * 55)


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
def main():
    print('=' * 55)
    print('  📚  Books.toscrape.com Scraper')
    print('=' * 55)


    categories = scrape_categories()
    if not categories:
        return

    target = categories[:CATEGORY_LIMIT] if CATEGORY_LIMIT else categories
    print(f'   Scraping {len(target)} of {len(categories)} categories\n')

    save_categories(target)

    all_books = scrape_all_books(target)
    save_books(all_books, target)

    print_stats(all_books)


if __name__ == '__main__':
    main()