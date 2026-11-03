"""
Loader de dados: lê de Data/emporio.db (SQLite pré-compilado) se disponível,
senão faz fallback para os CSVs originais.
Usa cache em memória para não reler a cada chamada.
Políticas são lidas sob demanda do .md (tools/policy_search.py).
"""
import json
import sqlite3
from pathlib import Path

import pandas as pd

from core.utils import norm as _norm

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "Data"
DB_PATH = DATA_DIR / "emporio.db"

_cache: dict | None = None


def _load_from_sqlite() -> dict:
    """Carrega todas as tabelas do banco pré-compilado."""
    conn = sqlite3.connect(DB_PATH)
    try:
        tables = {}
        for name in ("products", "categories", "customers", "orders", "order_items", "promotions"):
            tables[name] = pd.read_sql(f"SELECT * FROM {name}", conn)
        return tables
    finally:
        conn.close()


def _specs_text(specs_raw) -> str:
    try:
        return " ".join(str(v) for v in json.loads(specs_raw or "{}").values())
    except Exception:
        return ""


def _load_from_csvs() -> dict:
    """Fallback: lê os CSVs e computa os campos enriquecidos."""
    products = pd.read_csv(DATA_DIR / "desafio_tecnico_ai_eng - products.csv")
    categories = pd.read_csv(DATA_DIR / "desafio_tecnico_ai_eng - categories.csv")
    customers = pd.read_csv(DATA_DIR / "desafio_tecnico_ai_eng - customers.csv")
    orders = pd.read_csv(DATA_DIR / "desafio_tecnico_ai_eng - orders.csv")
    order_items = pd.read_csv(DATA_DIR / "desafio_tecnico_ai_eng - order_items.csv")
    promotions = pd.read_csv(DATA_DIR / "desafio_tecnico_ai_eng - promotions.csv")

    products = products.merge(
        categories[["category_id", "name"]].rename(columns={"name": "category_name"}),
        on="category_id",
        how="left",
    )
    products["search_text"] = (
        products["name"].fillna("").apply(_norm)
        + " "
        + products["description"].fillna("").apply(_norm)
        + " "
        + products["specs"].apply(lambda x: _norm(_specs_text(x)))
    )
    return {
        "products": products,
        "categories": categories,
        "customers": customers,
        "orders": orders,
        "order_items": order_items,
        "promotions": promotions,
    }


def get_data() -> dict:
    """Retorna os dados cacheados (lê apenas uma vez por processo)."""
    global _cache
    if _cache is None:
        if DB_PATH.exists():
            _cache = _load_from_sqlite()
        else:
            _cache = _load_from_csvs()
    return _cache
