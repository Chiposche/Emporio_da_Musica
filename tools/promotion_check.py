"""
Ferramenta de verificação de promoções ativas da loja.
"""
from typing import Optional
from core.loader import get_data
from core.utils import pd_not_na


def check_promotions(
    product_id: Optional[int] = None,
    product_name: Optional[str] = None,
) -> list[dict]:
    """
    Verifica promoções vigentes e ativas para um produto ou lista todas as promoções ativas.

    Args:
        product_id: ID do produto para consulta
        product_name: Nome ou termo do produto

    Returns:
        Lista com promoções ativas encontradas, descontos em % e descrição.
    """
    data = get_data()
    promos = data["promotions"]
    products = data["products"]

    # Filtra apenas promoções ativas
    # 'is_active' pode ser booleano ou string 'true'/'1'
    active_promos = promos[promos["is_active"].isin([True, 1, "True", "true", "1", "TRUE"])].copy()

    # Junta com nome do produto
    merged = active_promos.merge(
        products[["product_id", "name", "price_brl"]],
        on="product_id",
        how="left",
    )

    if product_id is not None:
        try:
            pid = int(product_id)
            merged = merged[merged["product_id"] == pid]
        except (ValueError, TypeError):
            pass
    elif product_name:
        p_lower = str(product_name).lower().strip()
        merged = merged[merged["name"].str.lower().str.contains(p_lower, na=False)]

    results = []
    for _, row in merged.iterrows():
        base_price = float(row["price_brl"]) if pd_not_na(row["price_brl"]) else 0.0
        discount = float(row["discount_percent"])
        discounted_price = round(base_price * (1.0 - discount / 100.0), 2) if base_price > 0 else None

        results.append({
            "promotion_id": int(row["promotion_id"]),
            "product_id": int(row["product_id"]),
            "product_name": str(row["name"]),
            "original_price_brl": base_price,
            "discount_percent": discount,
            "discounted_price_brl": discounted_price,
            "description": str(row["description"]),
        })

    return results


