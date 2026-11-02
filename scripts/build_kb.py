#!/usr/bin/env python3
"""
Gera Data/politicas.md a partir de Data/políticas_da_loja.pdf.
Uso: python scripts/build_kb.py
"""
import re
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("ERRO: pdfplumber não instalado. pip install pdfplumber", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).parent.parent
PDF_PATH = ROOT / "Data" / "políticas_da_loja.pdf"
OUT_PATH = ROOT / "Data" / "politicas.md"

# Seções esperadas (validação) — usa o número base, sem ponto final
EXPECTED_BASES = {
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "1.1", "1.2",
    "3.1",
    "4.1", "4.2", "4.3", "4.4",
    "5.1", "5.2", "5.3",
    "6.1", "6.2",
    "7.1", "7.2", "7.3",
    "8.1", "8.2", "8.3",
}


def extract_sections(pdf_path: Path) -> dict[str, str]:
    """Extrai o PDF e retorna dict {título_da_seção: texto_completo}."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

    # Divide por seções numeradas (ex: "4.1 Direito de Arrependimento")
    # O regex captura o número + título até o próximo número ou fim
    pattern = r"(?m)^(\d+(?:\.\d+)*)\.?\s+([^\n]{3,70})$"
    matches = list(re.finditer(pattern, full_text))

    sections = {}
    for i, m in enumerate(matches):
        num = m.group(1)
        title = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        body = full_text[start:end].strip()
        sections[f"{num} {title}"] = body

    return sections


def write_markdown(sections: dict[str, str], out_path: Path) -> None:
    """Escreve o markdown com cabeçalhos ## N.N Título."""
    lines = [
        "# Manual de Políticas e Procedimentos — Empório da Música",
        "",
        "*Documento derivado automaticamente de `Data/políticas_da_loja.pdf`*",
        "*Fonte da verdade: o PDF original.*",
        "",
        "---",
        "",
    ]
    for title, body in sections.items():
        # limpa ruído de cabeçalho/rodapé repetidos
        body = re.sub(r"Empório da Música — Sua música começa aqui\.\s*", "", body)
        body = re.sub(r"Última atualização: Junho de 2025\s*", "", body)
        body = re.sub(r"Manual de Políticas e Procedimentos\s*", "", body)
        body = re.sub(r"Documento interno — Uso restrito da equipe de atendimento Empório da Música\s*", "", body)
        body = body.strip()
        lines.append(f"## {title}")
        lines.append("")
        lines.append(body)
        lines.append("")
        lines.append("---")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def validate(sections: dict[str, str]) -> bool:
    """Valida se as seções essenciais estão presentes."""
    found_nums = {s.split()[0] for s in sections.keys()}
    missing = EXPECTED_BASES - found_nums
    if missing:
        print(f"AVISO: seções esperadas não encontradas: {sorted(missing)}", file=sys.stderr)
        return False
    print(f"OK: {len(sections)} seções extraídas, todas as essenciais presentes.")
    return True


def main() -> int:
    if not PDF_PATH.exists():
        print(f"ERRO: PDF não encontrado em {PDF_PATH}", file=sys.stderr)
        return 1

    print(f"Extraindo {PDF_PATH.name}...")
    sections = extract_sections(PDF_PATH)
    print(f"  {len(sections)} seções detectadas.")

    if not validate(sections):
        return 1

    write_markdown(sections, OUT_PATH)
    print(f"Gerado {OUT_PATH.relative_to(ROOT)} ({OUT_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())