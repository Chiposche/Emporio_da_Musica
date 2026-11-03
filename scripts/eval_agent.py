#!/usr/bin/env python3
"""
Deterministic evaluation of the tool layer against real data.

Runs ~15 scenarios, validates output structure and expected values.
No LLM API keys required — tests the full CSV→SQLite→DataFrame→tool pipeline.

Usage: python scripts/eval_agent.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.order_lookup import get_order_status
from tools.policy_search import search_policies
from tools.product_search import search_products
from tools.promotion_check import check_promotions

SCENARIOS = [
    {
        "id": "product_search_violao",
        "tool": search_products,
        "args": {"query": "violão"},
        "checks": [
            ("returns non-empty list", lambda r: len(r) > 0),
            ("results have 'name' key", lambda r: all("name" in item for item in r)),
        ],
    },
    {
        "id": "product_search_max_price",
        "tool": search_products,
        "args": {"query": "violão", "max_price": 500},
        "checks": [
            ("all prices <= 500", lambda r: all(item["price_brl"] <= 500 for item in r)),
        ],
    },
    {
        "id": "product_search_yamaha",
        "tool": search_products,
        "args": {"query": "yamaha"},
        "checks": [
            ("finds yamaha products", lambda r: any("yamaha" in item["name"].lower() for item in r)),
        ],
    },
    {
        "id": "product_search_in_stock",
        "tool": search_products,
        "args": {"in_stock_only": True},
        "checks": [
            ("all results in stock", lambda r: all(item["stock_quantity"] > 0 for item in r)),
        ],
    },
    {
        "id": "product_search_no_match",
        "tool": search_products,
        "args": {"query": "xyznotaproduct"},
        "checks": [
            ("returns empty list", lambda r: r == []),
        ],
    },
    {
        "id": "order_found_by_id",
        "tool": get_order_status,
        "args": {"order_id": 1},
        "checks": [
            ("found is True", lambda r: r["found"] is True),
            ("has order_id", lambda r: "order_id" in r),
            ("has status", lambda r: "status" in r),
            ("has items list", lambda r: isinstance(r.get("items"), list)),
        ],
    },
    {
        "id": "order_found_by_name",
        "tool": get_order_status,
        "args": {"customer_name": "Pedro"},
        "checks": [
            ("found is True", lambda r: r["found"] is True),
        ],
    },
    {
        "id": "order_not_found",
        "tool": get_order_status,
        "args": {"order_id": 99999},
        "checks": [
            ("found is False", lambda r: r["found"] is False),
        ],
    },
    {
        "id": "promotions_list_all",
        "tool": check_promotions,
        "args": {},
        "checks": [
            ("returns a list", lambda r: isinstance(r, list)),
            ("items have discount_percent", lambda r: all("discount_percent" in p for p in r)),
            ("items have product_name", lambda r: all("product_name" in p for p in r)),
        ],
    },
    {
        "id": "promotions_by_product_id",
        "tool": check_promotions,
        "args": {"product_id": 1},
        "checks": [
            ("returns a list", lambda r: isinstance(r, list)),
        ],
    },
    {
        "id": "promotions_by_name",
        "tool": check_promotions,
        "args": {"product_name": "violão"},
        "checks": [
            ("returns a list", lambda r: isinstance(r, list)),
        ],
    },
    {
        "id": "policy_devolucao",
        "tool": search_policies,
        "args": {"topic": "devolução"},
        "checks": [
            ("found is True", lambda r: r["found"] is True),
            ("has sections", lambda r: len(r.get("sections", [])) > 0),
        ],
    },
    {
        "id": "policy_horario",
        "tool": search_policies,
        "args": {"topic": "horário"},
        "checks": [
            ("found is True", lambda r: r["found"] is True),
        ],
    },
    {
        "id": "policy_garantia",
        "tool": search_policies,
        "args": {"topic": "garantia"},
        "checks": [
            ("found is True", lambda r: r["found"] is True),
        ],
    },
    {
        "id": "policy_empty_topic",
        "tool": search_policies,
        "args": {"topic": ""},
        "checks": [
            ("found is False", lambda r: r["found"] is False),
        ],
    },
    {
        "id": "guardrail_pix_warning",
        "tool": check_promotions,
        "args": {},
        "checks": [
            ("promo items have aviso_pix field", lambda r: all("aviso_pix" in p for p in r) if r else True),
        ],
    },
    {
        "id": "guardrail_no_accessory",
        "tool": search_products,
        "args": {"query": "cordas palheta cabo pedal"},
        "checks": [
            ("no accessories in catalog", lambda r: not any(
                any(w in item["name"].lower() for w in ["corda", "palheta", "cabo", "pedal"])
                for item in r
            )),
        ],
    },
    {
        "id": "policy_parcelamento",
        "tool": search_policies,
        "args": {"topic": "parcelamento pagamento"},
        "checks": [
            ("found is True", lambda r: r["found"] is True),
        ],
    },
]


def main():
    passed = 0
    failed = 0
    errors = []

    for scenario in SCENARIOS:
        sid = scenario["id"]
        try:
            result = scenario["tool"](**scenario["args"])
        except Exception as e:
            print(f"  ERROR  {sid} — exception: {e}")
            failed += 1
            errors.append(sid)
            continue

        all_ok = True
        for desc, check in scenario["checks"]:
            try:
                ok = check(result)
            except Exception:
                ok = False
            if not ok:
                print(f"  FAIL   {sid} — {desc}")
                all_ok = False

        if all_ok:
            print(f"  PASS   {sid}")
            passed += 1
        else:
            failed += 1
            errors.append(sid)

    total = passed + failed
    print(f"\n{'=' * 50}")
    print(f"Results: {passed}/{total} passed")
    if errors:
        print(f"Failed:  {', '.join(errors)}")
    print(f"{'=' * 50}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
