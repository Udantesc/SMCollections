"""
Scraper: Steve Madden MX - Colecciones y Productos
=====================================================
Extrae todas las colecciones visibles del sitio stevemadden.com.mx
junto con el título de cada producto y su posición dentro de cada colección.

Usa la API JSON pública que Shopify expone por defecto:
  /collections.json  → lista de colecciones
  /collections/{handle}/products.json → productos por colección

Requisitos:
    pip install requests pandas

Autor: Asistente Personal
"""

import time
import requests
import pandas as pd
from pathlib import Path

BASE_URL = "https://stevemadden.com.mx"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; ScraperBot/1.0)"}
DELAY    = 0.5   # segundos entre requests (cortesía con el servidor)


# ─────────────────────────────────────────────
# 1. Obtener todas las colecciones
# ─────────────────────────────────────────────
def get_all_collections() -> list[dict]:
    """Paginación automática sobre /collections.json"""
    collections = []
    page = 1

    while True:
        url = f"{BASE_URL}/collections.json"
        params = {"limit": 250, "page": page}

        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()

        data = resp.json().get("collections", [])
        if not data:
            break

        collections.extend(data)
        print(f"  → Página {page}: {len(data)} colecciones encontradas")

        if len(data) < 250:
            break
        page += 1
        time.sleep(DELAY)

    return collections


# ─────────────────────────────────────────────
# 2. Obtener productos de una colección
# ─────────────────────────────────────────────
def get_products_in_collection(handle: str) -> list[dict]:
    """Paginación automática sobre /collections/{handle}/products.json"""
    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/collections/{handle}/products.json"
        params = {"limit": 250, "page": page}

        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)

        # Algunas colecciones pueden estar protegidas o no existir
        if resp.status_code != 200:
            break

        data = resp.json().get("products", [])
        if not data:
            break

        products.extend(data)

        if len(data) < 250:
            break
        page += 1
        time.sleep(DELAY)

    return products


# ─────────────────────────────────────────────
# 3. Pipeline principal
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Steve Madden MX — Extracción de colecciones y productos")
    print("=" * 60)

    # ── Colecciones ──────────────────────────
    print("\n[1/2] Obteniendo colecciones...")
    collections = get_all_collections()
    print(f"  Total colecciones: {len(collections)}")

    # ── Productos por colección ───────────────
    print("\n[2/2] Obteniendo productos por colección...")
    rows = []

    for col in collections:
        col_id     = col["id"]
        col_title  = col["title"]
        col_handle = col["handle"]

        print(f"  ▶ {col_title} ({col_handle})")

        products = get_products_in_collection(col_handle)

        for position, product in enumerate(products, start=1):
            rows.append({
                "collection_id"    : col_id,
                "collection_title" : col_title,
                "collection_handle": col_handle,
                "position"         : position,
                "product_id"       : product["id"],
                "product_title"    : product["title"],
                "product_handle"   : product["handle"],
                "product_type"     : product.get("product_type", ""),
                "vendor"           : product.get("vendor", ""),
                "tags"             : ", ".join(product.get("tags", [])),
            })

        time.sleep(DELAY)

    # ── DataFrame y exportación ───────────────
    df = pd.DataFrame(rows)
    print(f"\n✅ Total registros: {len(df):,}")
    print(df.head(10).to_string(index=False))

    output_csv = Path("stevemadden_collections_products.csv")
    output_xlsx = Path("stevemadden_collections_products.xlsx")

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    df.to_excel(output_xlsx, index=False)

    print(f"\n💾 Archivos guardados:")
    print(f"   • {output_csv.resolve()}")
    print(f"   • {output_xlsx.resolve()}")

    # ── Resumen por colección ─────────────────
    summary = (
        df.groupby(["collection_title"])["product_title"]
        .count()
        .reset_index()
        .rename(columns={"product_title": "total_productos"})
        .sort_values("total_productos", ascending=False)
    )
    print("\n📊 Resumen por colección:")
    print(summary.to_string(index=False))

    return df


# ─────────────────────────────────────────────
if __name__ == "__main__":
    df = main()
