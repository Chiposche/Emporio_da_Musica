from tools.policy_search import search_policies
from tools.product_search import search_products
from tools.promotion_check import check_promotions


def test_promotion_has_pix_warning():
    results = check_promotions()
    assert len(results) > 0
    assert all("aviso_pix" in r for r in results)


def test_no_pix_warning_when_empty():
    results = check_promotions(product_id=999)
    assert results == []


def test_product_search_no_results():
    results = search_products(query="harpa paraguaia xyznotfound")
    assert results == []


def test_policy_search_garantia():
    result = search_policies(topic="garantia")
    assert result["found"] is True
    assert len(result["sections"]) > 0


def test_policy_search_devolucao_has_content():
    result = search_policies(topic="devolução")
    assert result["found"] is True
    for section in result["sections"]:
        assert len(section["content"]) > 0


def test_promotion_pix_warning_text():
    results = check_promotions(product_id=1)
    if results:
        assert "NÃO se aplica" in results[0]["aviso_pix"]
