import pandas as pd
import pytest

PRODUCTS = pd.DataFrame([
    {"product_id": 1, "name": "Violão Yamaha C40", "description": "Violão clássico nylon iniciante",
     "price_brl": 899.90, "stock_quantity": 5, "status": "ativo", "category_id": 1,
     "category_name": "Cordas", "search_text": "violao yamaha c40 violao classico nylon iniciante",
     "specs": "{}"},
    {"product_id": 2, "name": "Teclado Casio CT-S200", "description": "Teclado portátil 61 teclas",
     "price_brl": 1299.00, "stock_quantity": 0, "status": "ativo", "category_id": 2,
     "category_name": "Teclas", "search_text": "teclado casio ct-s200 teclado portatil 61 teclas",
     "specs": "{}"},
    {"product_id": 3, "name": "Guitarra Fender Strat", "description": "Guitarra elétrica stratocaster",
     "price_brl": 5499.00, "stock_quantity": 3, "status": "ativo", "category_id": 1,
     "category_name": "Cordas", "search_text": "guitarra fender strat guitarra eletrica stratocaster",
     "specs": "{}"},
])

CATEGORIES = pd.DataFrame([
    {"category_id": 1, "name": "Cordas"},
    {"category_id": 2, "name": "Teclas"},
])

CUSTOMERS = pd.DataFrame([
    {"customer_id": 1, "name": "Carlos Silva"},
    {"customer_id": 2, "name": "Ana Oliveira"},
])

ORDERS = pd.DataFrame([
    {"order_id": 1, "customer_id": 1, "order_date": "2025-06-01", "status": "Entregue",
     "total_brl": 899.90, "payment_method": "PIX", "tracking_code": "BR123456789",
     "estimated_delivery": "2025-06-10", "notes": ""},
    {"order_id": 2, "customer_id": 2, "order_date": "2025-06-15", "status": "Em trânsito",
     "total_brl": 1299.00, "payment_method": "Cartão", "tracking_code": "BR987654321",
     "estimated_delivery": "2025-06-25", "notes": "Presente"},
])

ORDER_ITEMS = pd.DataFrame([
    {"order_id": 1, "product_id": 1, "quantity": 1},
    {"order_id": 2, "product_id": 2, "quantity": 1},
])

PROMOTIONS = pd.DataFrame([
    {"promotion_id": 1, "product_id": 1, "discount_percent": 10.0,
     "description": "Promoção Violão Yamaha", "is_active": True},
    {"promotion_id": 2, "product_id": 3, "discount_percent": 5.0,
     "description": "Promoção Guitarra", "is_active": False},
])

POLICY_SECTIONS = {
    "4.1 Direito de Arrependimento": "O consumidor pode desistir da compra em até 7 dias corridos.",
    "5.1 Horários de Atendimento": "Segunda a sexta das 9h às 18h, sábado das 9h às 13h.",
    "6.1 Frete e Entrega": "Frete grátis para compras acima de R$500. Prazo de 5 a 10 dias úteis.",
    "7.1 Formas de Pagamento": "Aceitamos PIX, cartão de crédito e boleto. Desconto de 5% no PIX.",
    "8.1 Garantia": "Todos os instrumentos possuem garantia de 12 meses contra defeitos.",
}


@pytest.fixture(autouse=True)
def mock_data(monkeypatch):
    data = {
        "products": PRODUCTS.copy(),
        "categories": CATEGORIES.copy(),
        "customers": CUSTOMERS.copy(),
        "orders": ORDERS.copy(),
        "order_items": ORDER_ITEMS.copy(),
        "promotions": PROMOTIONS.copy(),
    }
    monkeypatch.setattr("core.loader._cache", data)
    monkeypatch.setattr("core.loader.get_data", lambda: data)

    import tools.policy_search as ps
    monkeypatch.setattr(ps, "_md_cache", POLICY_SECTIONS.copy())

    yield data

    monkeypatch.setattr("core.loader._cache", None)
    monkeypatch.setattr(ps, "_md_cache", None)
