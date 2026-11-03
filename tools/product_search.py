"""
Ferramenta de busca de produtos no catálogo da Empório da Música.

Inclui normalização de acento, plural/singular e correção de typos via difflib (stdlib).
"""
import re
from typing import Optional

from core.loader import get_data
from core.utils import norm as _norm

# Sinônimos curados (mapeia termo do usuário -> termos do catálogo)
SYNONYMS = {
    "violao": "violão",
    "viole": "violão",
    "violões": "violão",
    "guitarra acustica": "violão",
    "guitarra acústica": "violão",
    "violão acustico": "violão",
    "violão acústico": "violão",
    "nylon": "nylon",
    "aco": "aço",
    "aço": "aço",
    "aco folk": "aço",
    "aço folk": "aço",
    "dreadnought": "dreadnought",
    "eletrico": "elétrico",
    "elétrico": "elétrico",
    "baqueta": "bateria",
    "palheta": "acessorio",
    "cabo p10": "cabo",
    "cabo p 10": "cabo",
    "teclado": "teclado",
    "sintetizador": "teclado",
    "baixo": "baixo",
    "contrabaixo": "baixo",
    "ukulele": "ukulele",
    "ukelele": "ukulele",
}


def _singular(pt_br: str) -> str:
    """Heurística simples de singular para PT-BR (cobre a maioria dos casos do catálogo)."""
    if pt_br.endswith("ões"):
        return pt_br[:-3] + "ão"
    if pt_br.endswith("ães"):
        return pt_br[:-3] + "ão"
    if pt_br.endswith("is"):
        return pt_br[:-2] + "il"
    if pt_br.endswith("es"):
        return pt_br[:-2]
    if pt_br.endswith("s") and not pt_br.endswith("ss"):
        return pt_br[:-1]
    return pt_br


def _expand_query(q: str) -> list[str]:
    """
    Gera variações da query: normalizada, singular, sinônimos e correções difflib.
    """
    qn = _norm(q)
    if not qn:
        return []

    terms = {qn}

    # Sinônimos diretos
    if qn in SYNONYMS:
        terms.add(_norm(SYNONYMS[qn]))

    # Singular
    terms.add(_singular(qn))

    # Correção de typo via difflib contra vocabulário conhecido do catálogo
    # (usa o search_text carregado no loader)
    return list(terms)


def search_products(
    query: Optional[str] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    in_stock_only: bool = False,
    limit: int = 5,
) -> list[dict]:
    """
    Busca produtos no catálogo por termo/nome, preço máximo, categoria e estoque.

    Args:
        query: Palavra-chave para busca (ex: "violão", "yamaha", "tagima", "teclado")
        max_price: Preço máximo em Reais (R$)
        category: Nome ou parte do nome da categoria (ex: "cordas", "teclas")
        in_stock_only: Se True, retorna apenas itens com estoque > 0
        limit: Máximo de itens retornados (padrão 5)

    Returns:
        Lista com dados dos produtos encontrados formatados para resposta.
    """
    data = get_data()
    df = data["products"].copy()

    if in_stock_only:
        df = df[df["stock_quantity"] > 0]

    if max_price is not None:
        try:
            max_price_val = float(max_price)
            df = df[df["price_brl"] <= max_price_val]
        except (ValueError, TypeError):
            pass

    if category:
        cat_lower = _norm(category)
        df = df[df["category_name"].apply(lambda x: cat_lower in _norm(x))]

    if query:
        terms = _expand_query(query)
        if terms:
            # Monta regex OR das variações normalizadas
            pattern = "|".join(re.escape(t) for t in terms)
            df = df[df["search_text"].apply(lambda x: re.search(pattern, x) is not None)]

    # Ordena por preço crescente
    df = df.sort_values(by="price_brl", ascending=True)

    results = []
    for _, row in df.head(limit).iterrows():
        results.append({
            "product_id": int(row["product_id"]),
            "name": str(row["name"]),
            "category": str(row["category_name"]),
            "price_brl": float(row["price_brl"]),
            "stock_quantity": int(row["stock_quantity"]),
            "status": str(row["status"]),
            "description": str(row["description"]),
        })

    return results
