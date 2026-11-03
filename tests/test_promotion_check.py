from tools.promotion_check import check_promotions


def test_all_active_promotions():
    results = check_promotions()
    assert len(results) == 1
    assert results[0]["promotion_id"] == 1


def test_filter_by_product_id():
    results = check_promotions(product_id=1)
    assert len(results) == 1
    assert results[0]["discount_percent"] == 10.0


def test_inactive_excluded():
    results = check_promotions(product_id=3)
    assert results == []


def test_filter_by_product_name():
    results = check_promotions(product_name="Violão")
    assert len(results) == 1


def test_discounted_price_calculation():
    results = check_promotions(product_id=1)
    assert results[0]["discounted_price_brl"] == round(899.90 * 0.9, 2)


def test_nonexistent_product():
    results = check_promotions(product_id=999)
    assert results == []
