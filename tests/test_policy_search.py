from tools.policy_search import search_policies


def test_keyword_match_arrependimento():
    result = search_policies(topic="arrependimento")
    assert result["found"] is True
    assert len(result["sections"]) >= 1
    assert any("Arrependimento" in s["title"] for s in result["sections"])


def test_keyword_match_horario():
    result = search_policies(topic="horário")
    assert result["found"] is True
    assert any("Horário" in s["title"] or "Atendimento" in s["title"] for s in result["sections"])


def test_keyword_match_garantia():
    result = search_policies(topic="garantia")
    assert result["found"] is True


def test_empty_topic():
    result = search_policies(topic="")
    assert result["found"] is False


def test_fallback_to_overview():
    result = search_policies(topic="xyzinexistente")
    assert result["found"] is True
    assert "note" in result


def test_multiple_sections_returned():
    result = search_policies(topic="pagamento pix")
    assert result["found"] is True
    assert len(result["sections"]) >= 1
