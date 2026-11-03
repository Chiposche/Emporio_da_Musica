#!/usr/bin/env python3
"""
Gera Data/politicas.md (do PDF) e Data/emporio.db (dos CSVs).
Uso: python scripts/build_kb.py
"""
import json
import re
import sqlite3
import sys
import unicodedata
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


DB_PATH = ROOT / "Data" / "emporio.db"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def _specs_text(specs_raw) -> str:
    try:
        return " ".join(str(v) for v in json.loads(specs_raw or "{}").values())
    except Exception:
        return ""


def build_sqlite(data_dir: Path, db_path: Path) -> int:
    """Compila os CSVs em Data/ para um banco SQLite com search_text pré-calculado."""
    try:
        import pandas as pd
    except ImportError:
        print("ERRO: pandas não instalado. pip install pandas", file=sys.stderr)
        return 1

    csvs = {
        "products": "desafio_tecnico_ai_eng - products.csv",
        "categories": "desafio_tecnico_ai_eng - categories.csv",
        "customers": "desafio_tecnico_ai_eng - customers.csv",
        "orders": "desafio_tecnico_ai_eng - orders.csv",
        "order_items": "desafio_tecnico_ai_eng - order_items.csv",
        "promotions": "desafio_tecnico_ai_eng - promotions.csv",
    }

    for name, fname in csvs.items():
        if not (data_dir / fname).exists():
            print(f"ERRO: CSV não encontrado: {fname}", file=sys.stderr)
            return 1

    tables = {name: pd.read_csv(data_dir / fname) for name, fname in csvs.items()}

    # Enriquece produtos
    products = tables["products"].merge(
        tables["categories"][["category_id", "name"]].rename(columns={"name": "category_name"}),
        on="category_id",
        how="left",
    )
    products["search_text"] = (
        products["name"].fillna("").apply(_norm)
        + " "
        + products["description"].fillna("").apply(_norm)
        + " "
        + products["specs"].apply(lambda x: _norm(_specs_text(x)))
    )
    tables["products"] = products

    conn = sqlite3.connect(db_path)
    try:
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=False)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_products_search ON products(search_text)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_id ON orders(order_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)")
        conn.commit()
    finally:
        conn.close()

    size = db_path.stat().st_size
    print(f"Gerado {db_path.relative_to(ROOT)} ({size:,} bytes, {len(tables)} tabelas)")
    return 0


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

    print("Compilando CSVs em SQLite...")
    rc = build_sqlite(ROOT / "Data", DB_PATH)
    if rc != 0:
        return rc

    return 0


if __name__ == "__main__":
    sys.exit(main())