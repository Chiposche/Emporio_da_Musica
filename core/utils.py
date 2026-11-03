import re
import unicodedata


def norm(s: str) -> str:
    """Remove acentos, converte para minúsculas e colapsa espaços."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def pd_not_na(val) -> bool:
    """Verifica se um valor pandas não é NaN/None."""
    import pandas as pd
    return bool(pd.notna(val) and str(val).strip().lower() != "nan")
