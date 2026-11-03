from tools.order_lookup import get_order_status


def test_lookup_by_order_id():
    result = get_order_status(order_id=1)
    assert result["found"] is True
    assert result["order_id"] == 1
    assert result["customer_name"] == "Carlos Silva"
    assert len(result["items"]) == 1


def test_lookup_by_customer_name():
    result = get_order_status(customer_name="Ana")
    assert result["found"] is True
    assert result["order_id"] == 2


def test_not_found_by_id():
    result = get_order_status(order_id=999)
    assert result["found"] is False


def test_not_found_by_name():
    result = get_order_status(customer_name="Inexistente")
    assert result["found"] is False


def test_tracking_code_present():
    result = get_order_status(order_id=1)
    assert result["tracking_code"] == "BR123456789"


def test_items_structure():
    result = get_order_status(order_id=2)
    item = result["items"][0]
    assert "product_id" in item
    assert "name" in item
    assert "quantity" in item
