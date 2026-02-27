"""
Scraper: Steve Madden MX - Colecciones y Productos (orden real del sitio)
=========================================================================
Extrae el orden VISUAL real de los productos tal como aparecen en el sitio,
haciendo scraping del HTML de cada página de colección.

Requisitos:
    pip install requests beautifulsoup4 pandas openpyxl

Autor: Asistente Personal
"""

import time
import requests
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup

BASE_URL = "https://stevemadden.com.mx"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
}
DELAY = 1.0  # segundos entre requests


# ─────────────────────────────────────────────
# 1. Obtener todas las colecciones via API JSON
# ─────────────────────────────────────────────
def get_all_collections() -> list[dict]:
    collections = []
    page = 1
    while True:
        url = f"{BASE_URL}/collections.json"
        resp = requests.get(url, headers=HEADERS, params={"limit": 250, "page": page}, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("collections", [])
        if not data:
            break
        collections.extend(data)
        print(f"  → Página {page}: {len(data)} colecciones")
        if len(data) < 250:
            break
        page += 1
        time.sleep(DELAY)
    return collections


# ─────────────────────────────────────────────
# 2. Extraer productos del HTML (orden visual real)
# ─────────────────────────────────────────────
def get_products_from_html(handle: str) -> list[dict]:
    """
    Scrapea el HTML paginado de /collections/{handle}
    y extrae los productos en el orden visual real del sitio.
    """
    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/collections/{handle}"
        params = {"page": page}
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)

        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Steve Madden MX usa cards de producto con estos selectores comunes en Shopify
        items = (
            soup.select("div.product-item")        or
            soup.select("div.grid-product")        or
            soup.select("li.grid__item")           or
            soup.select("div.product-card")        or
            soup.select("[data-product-id]")       or
            soup.select("div.product_card")        or
            soup.select("article.product-card")
        )

        if not items:
            # Fallback genérico: buscar links que apunten a /products/
            links = soup.select("a[href*='/products/']")
            seen = {}
            for link in links:
                href = link.get("href", "")
                handle_prod = href.split("/products/")[-1].split("?")[0].strip("/")
                if handle_prod and handle_prod not in seen:
                    title = (
                        link.get("aria-label") or
                        (link.select_one("img[alt]").get("alt") if link.select_one("img[alt]") else None) or
                        link.get_text(strip=True) or
                        handle_prod.replace("-", " ").upper()
                    )
                    seen[handle_prod] = title
            items_generic = [{"handle": h, "title": t} for h, t in seen.items()]
            if items_generic:
                products.extend(items_generic)
            break

        page_found_products = False
        for item in items:
            # Título
            title_el = (
                item.select_one(".product-item__title") or
                item.select_one(".grid-product__title") or
                item.select_one(".product-card__title") or
                item.select_one("[class*='title']") or
                item.select_one("h2") or
                item.select_one("h3") or
                item.select_one("a")
            )
            title = title_el.get_text(strip=True) if title_el else "N/A"

            # Handle / URL del producto
            link_el = item.select_one("a[href*='/products/']") or item.select_one("a")
            href = link_el.get("href", "") if link_el else ""
            prod_handle = href.split("/products/")[-1].split("?")[0].strip("/") if "/products/" in href else ""

            # Precio actual
            price_el = (
                item.select_one(".price--sale .price__regular") or
                item.select_one(".price__sale") or
                item.select_one(".price") or
                item.select_one("[class*='price']")
            )
            price = price_el.get_text(strip=True) if price_el else ""

            # Precio original (antes de descuento)
            compare_el = (
                item.select_one(".price__compare") or
                item.select_one(".compare-at-price") or
                item.select_one("[class*='compare']")
            )
            compare_price = compare_el.get_text(strip=True) if compare_el else ""

            if title and title != "N/A":
                products.append({
                    "handle"        : prod_handle,
                    "title"         : title,
                    "price"         : price,
                    "compare_price" : compare_price,
                    "url"           : f"{BASE_URL}/products/{prod_handle}" if prod_handle else "",
                })
                page_found_products = True

        if not page_found_products:
            break

        # Verifica si hay página siguiente
        next_page = soup.select_one("a[href*='page=']:last-child") or soup.select_one(".pagination__next")
        if not next_page:
            break

        page += 1
        time.sleep(DELAY)

    # Elimina duplicados manteniendo orden
    seen_handles = set()
    unique = []
    for p in products:
        key = p.get("handle") or p.get("title")
        if key and key not in seen_handles:
            seen_handles.add(key)
            unique.append(p)

    return unique


# ─────────────────────────────────────────────
# 3. Pipeline principal
# ─────────────────────────────────────────────
def main():
    print("=" * 65)
    print("Steve Madden MX — Extracción VISUAL de colecciones y productos")
    print("=" * 65)

    print("\n[1/2] Obteniendo colecciones...")
    collections = get_all_collections()
    print(f"  Total colecciones: {len(collections)}")

    print("\n[2/2] Scrapeando productos por colección (orden visual real)...")
    rows = []

    for col in collections:
        col_id     = col["id"]
        col_title  = col["title"]
        col_handle = col["handle"]

        print(f"  ▶ {col_title} ({col_handle})", end=" ... ", flush=True)

        products = get_products_from_html(col_handle)
        print(f"{len(products)} productos")

        for position, product in enumerate(products, start=1):
            rows.append({
                "collection_id"    : col_id,
                "collection_title" : col_title,
                "collection_handle": col_handle,
                "position"         : position,
                "product_title"    : product.get("title", ""),
                "product_handle"   : product.get("handle", ""),
                "price"            : product.get("price", ""),
                "compare_price"    : product.get("compare_price", ""),
                "product_url"      : product.get("url", ""),
            })

        time.sleep(DELAY)

    df = pd.DataFrame(rows)
    print(f"\n✅ Total registros: {len(df):,}")
    print(df.head(10).to_string(index=False))

    output_csv  = Path("stevemadden_collections_products.csv")
    output_xlsx = Path("stevemadden_collections_products.xlsx")

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    df.to_excel(output_xlsx, index=False)

    print(f"\n💾 Archivos guardados:")
    print(f"   • {output_csv.resolve()}")
    print(f"   • {output_xlsx.resolve()}")

    summary = (
        df.groupby("collection_title")["product_title"]
        .count()
        .reset_index()
        .rename(columns={"product_title": "total_productos"})
        .sort_values("total_productos", ascending=False)
    )
    print("\n📊 Resumen por colección:")
    print(summary.to_string(index=False))

    return df


if __name__ == "__main__":
    df = main()
