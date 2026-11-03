"""
Ferramenta de busca nas políticas institucionais da loja (carregadas do .md derivado).

Busca por seção (## N.N Título) — muito mais preciso e barato que o PDF inteiro.
Inclui normalização de acento/plural para capturar variações naturais.
"""
import re
import unicodedata
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
MD_PATH = ROOT / "Data" / "politicas.md"


def _norm(s: str) -> str:
    """Remove acentos, minúsculas, colapsa espaços."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


# Cache do markdown parseado
_md_cache: Optional[dict] = None  # {titulo: conteudo}


def _load_sections() -> dict[str, str]:
    """Lê e parseia o .md uma vez: retorna {título: corpo}."""
    global _md_cache
    if _md_cache is not None:
        return _md_cache

    if not MD_PATH.exists():
        _md_cache = {}
        return _md_cache

    text = MD_PATH.read_text(encoding="utf-8")
    # Divide por "## N.N Título" — mantém o título como chave
    parts = re.split(r"\n##\s+", text)[1:]  # pula cabeçalho antes do primeiro ##
    sections = {}
    for part in parts:
        first_nl = part.find("\n")
        if first_nl == -1:
            continue
        title = part[:first_nl].strip()
        body = part[first_nl:].strip()
        if body.startswith("---"):
            body = body[3:].strip()
        sections[title] = body
    _md_cache = sections
    return sections


def search_policies(topic: str) -> dict:
    """
    Busca seções relevantes nas políticas da loja.

    Args:
        topic: Assunto (ex: "devolução", "horário", "frete", "pagamento", "garantia", "arrependimento")

    Returns:
        Dict com seções encontradas (cada uma ~150-300 tokens), não o documento inteiro.
    """
    sections = _load_sections()
    if not sections:
        return {
            "found": False,
            "message": "Documento de políticas não encontrado. Rode `python scripts/build_kb.py`.",
        }

    q_norm = _norm(topic)
    if not q_norm:
        return {
            "found": False,
            "message": "Tópico vazio.",
        }

    # Palavras-chave normalizadas (ignora stopwords curtas)
    keywords = [w for w in re.split(r"\W+", q_norm) if len(w) > 2]

    scored = []
    for title, body in sections.items():
        t_norm = _norm(title)
        b_norm = _norm(body)
        score = sum(3 for kw in keywords if kw in t_norm)  # título pesa 3x
        score += sum(1 for kw in keywords if kw in b_norm)
        if score > 0:
            scored.append((score, title, body))

    scored.sort(key=lambda x: x[0], reverse=True)

    if scored:
        best = [{"title": t, "content": c} for _, t, c in scored[:3]]
        return {
            "found": True,
            "topic": topic,
            "sections": best,
        }

    # Fallback: devolve as seções principais (sumário)
    main = [{"title": t, "content": c} for t, c in list(sections.items())[:5]]
    return {
        "found": True,
        "topic": topic,
        "note": "Nenhuma seção pontuou alto; exibindo visão geral das políticas.",
        "sections": main,
    }