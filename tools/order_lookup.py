"""
Ferramenta de consulta de status de pedidos e rastreamento.
"""
from typing import Optional

from core.loader import get_data
from core.utils import pd_not_na


def get_order_status(
    order_id: Optional[int] = None,
    customer_name: Optional[str] = None,
) -> dict:
    """
    Consulta informações detalhadas de um pedido: status, código de rastreamento,
    data estimada de entrega e itens comprados.

    Args:
        order_id: ID numérico do pedido (ex: 1, 5, 20)
        customer_name: Nome ou parte do nome do cliente (ex: "Carlos", "Silva")

    Returns:
        Dicionário com os detalhes do pedido e itens, ou aviso de não encontrado.
    """
    data = get_data()
    orders = data["orders"]
    customers = data["customers"]
    order_items = data["order_items"]
    products = data["products"]

    matched_order = None

    if order_id is not None:
        try:
            oid = int(order_id)
            res = orders[orders["order_id"] == oid]
            if not res.empty:
                matched_order = res.iloc[0]
        except (ValueError, TypeError):
            pass

    if matched_order is None and customer_name:
        c_name = str(customer_name).lower().strip()
        matched_cust = customers[customers["name"].str.lower().str.contains(c_name, na=False)]
        if not matched_cust.empty:
            cust_ids = matched_cust["customer_id"].tolist()
            res = orders[orders["customer_id"].isin(cust_ids)]
            if not res.empty:
                matched_order = res.iloc[0]

    if matched_order is None:
        return {
            "found": False,
            "message": "Nenhum pedido encontrado com os dados informados. Por favor, confirme o número do pedido ou nome completo do titular.",
        }

    oid = int(matched_order["order_id"])
    cid = int(matched_order["customer_id"])

    # Dados do cliente
    cust_row = customers[customers["customer_id"] == cid]
    c_name_val = str(cust_row.iloc[0]["name"]) if not cust_row.empty else "Não identificado"

    # Itens do pedido
    items_df = order_items[order_items["order_id"] == oid].merge(
        products[["product_id", "name", "price_brl"]],
        on="product_id",
        how="left",
    )

    items = []
    for _, item in items_df.iterrows():
        items.append({
            "product_id": int(item["product_id"]),
            "name": str(item["name"]),
            "quantity": int(item["quantity"]),
            "unit_price_brl": float(item["price_brl"]) if pd_not_na(item["price_brl"]) else None,
        })

    return {
        "found": True,
        "order_id": oid,
        "customer_name": c_name_val,
        "order_date": str(matched_order["order_date"]),
        "status": str(matched_order["status"]),
        "total_brl": float(matched_order["total_brl"]),
        "payment_method": str(matched_order["payment_method"]),
        "tracking_code": str(matched_order["tracking_code"]) if pd_not_na(matched_order["tracking_code"]) else "Sem rastreamento disponível",
        "estimated_delivery": str(matched_order["estimated_delivery"]) if pd_not_na(matched_order["estimated_delivery"]) else "A calcular",
        "notes": str(matched_order["notes"]) if pd_not_na(matched_order["notes"]) else "",
        "items": items,
    }


