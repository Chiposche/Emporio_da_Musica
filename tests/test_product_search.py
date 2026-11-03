from tools.product_search import search_products


def test_search_by_query():
    results = search_products(query="violao")
    assert len(results) >= 1
    assert "Violão" in results[0]["name"] or "Yamaha" in results[0]["name"]


def test_synonym_expansion():
    results = search_products(query="violao")
    names = [r["name"] for r in results]
    assert any("Yamaha" in n for n in names)


def test_max_price_filter():
    results = search_products(max_price=1000)
    assert all(r["price_brl"] <= 1000 for r in results)
    assert len(results) == 1


def test_in_stock_only():
    results = search_products(in_stock_only=True)
    assert all(r["stock_quantity"] > 0 for r in results)
    assert len(results) == 2


def test_category_filter():
    results = search_products(category="Teclas")
    assert len(results) == 1
    assert results[0]["name"] == "Teclado Casio CT-S200"


def test_empty_results():
    results = search_products(query="bateria")
    assert results == []


def test_no_filters_returns_all():
    results = search_products()
    assert len(results) == 3
