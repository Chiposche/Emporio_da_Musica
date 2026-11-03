"""
Detecção e mascaramento de PII (Personally Identifiable Information).

Tipos detectados:
  - CUSTOMER_NAME: Nomes de clientes (via banco de dados)
  - CPF: Cadastro de Pessoa Física
  - EMAIL: Endereço de email
  - PHONE: Número de telefone
  - ORDER_ID: Número de pedido

Estratégia:
  1. Detectar PII em mensagens de entrada
  2. Mascarar antes de enviar para LLM ([CUSTOMER_NAME], [CPF], etc)
  3. Desmascarar na resposta final
  4. Log: registrar quais tipos foram detectados
"""
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.loader import get_data

log = logging.getLogger("emporio.pii_mask")


@dataclass
class PII:
    """Representação de um PII detectado."""
    type: str          # CUSTOMER_NAME, CPF, EMAIL, PHONE, ORDER_ID
    value: str         # Valor original
    mask: str          # Token de mascara, ex: [CUSTOMER_NAME_0]
    start: int         # Posição no texto original
    end: int           # Posição no texto original


class PIIMasker:
    """Detecta e mascara PII em textos."""

    def __init__(self):
        self.customer_names: set[str] = set()
        self.order_ids: set[str] = set()
        self._load_data()

    def _load_data(self):
        """Carrega nomes de clientes e IDs de pedido do banco de dados."""
        try:
            data = get_data()
            # Extrair nomes únicos de clientes
            if "customers" in data:
                self.customer_names = set(
                    name.strip() for name in data["customers"].get("name", [])
                    if isinstance(name, str) and name.strip()
                )
            # Extrair IDs de pedido
            if "orders" in data:
                self.order_ids = set(
                    str(oid).strip() for oid in data["orders"].get("id", [])
                    if oid is not None
                )
        except Exception as e:
            log.warning("Failed to load PII data: %s", e)

    def detect(self, text: str) -> List[PII]:
        """
        Detecta todos os PIIs em um texto.

        Args:
            text: Texto a analisar

        Returns:
            Lista de PIIs encontrados
        """
        detected: List[PII] = []

        # 1. CPF (padrão: 123.456.789-00 ou 12345678900)
        cpf_pattern = r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}"
        for match in re.finditer(cpf_pattern, text):
            detected.append(PII(
                type="CPF",
                value=match.group(),
                mask="[CPF]",
                start=match.start(),
                end=match.end(),
            ))

        # 2. EMAIL (padrão: xxx@xxx.xxx)
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        for match in re.finditer(email_pattern, text):
            detected.append(PII(
                type="EMAIL",
                value=match.group(),
                mask="[EMAIL]",
                start=match.start(),
                end=match.end(),
            ))

        # 3. PHONE (padrão: (67) 98765-4321, 67 98765 4321, etc)
        phone_pattern = r"\(?[0-9]{2}\)?[\s-]?9?[0-9]{4}[\s-]?[0-9]{4}"
        for match in re.finditer(phone_pattern, text):
            detected.append(PII(
                type="PHONE",
                value=match.group(),
                mask="[PHONE]",
                start=match.start(),
                end=match.end(),
            ))

        # 4. CUSTOMER_NAME (match contra lista do banco)
        for name in self.customer_names:
            pattern = re.compile(re.escape(name), re.IGNORECASE)
            for match in pattern.finditer(text):
                detected.append(PII(
                    type="CUSTOMER_NAME",
                    value=match.group(),
                    mask="[CUSTOMER_NAME]",
                    start=match.start(),
                    end=match.end(),
                ))

        # 5. ORDER_ID (match contra lista de pedidos)
        for oid in self.order_ids:
            pattern = re.compile(r"\b" + re.escape(oid) + r"\b")
            for match in pattern.finditer(text):
                # Evitar confundir com outros números
                context_start = max(0, match.start() - 5)
                context_end = min(len(text), match.end() + 5)
                context = text[context_start:context_end].lower()
                if any(kw in context for kw in ["pedido", "order", "pedido ", "#", "id"]):
                    detected.append(PII(
                        type="ORDER_ID",
                        value=match.group(),
                        mask="[ORDER_ID]",
                        start=match.start(),
                        end=match.end(),
                    ))

        # Remover duplicatas (overlapping) - manter o mais específico
        detected = self._resolve_overlaps(detected)
        return detected

    def _resolve_overlaps(self, piis: List[PII]) -> List[PII]:
        """Remove PIIs sobrepostos, mantendo os de tipo mais específico."""
        if not piis:
            return []

        # Ordenar por start, depois por length (descendente)
        piis_sorted = sorted(piis, key=lambda p: (p.start, -(p.end - p.start)))

        result = []
        last_end = -1
        for pii in piis_sorted:
            if pii.start >= last_end:
                result.append(pii)
                last_end = pii.end

        return result

    def mask_text(self, text: str) -> Tuple[str, List[PII], Dict[str, int]]:
        """
        Mascara todos os PIIs em um texto.

        Args:
            text: Texto original

        Returns:
            (texto_mascarado, lista_de_piis, mapa_tipos_detectados)
        """
        piis = self.detect(text)
        masked_text = text
        type_counts: Dict[str, int] = defaultdict(int)

        # Aplicar mascaramento em ordem reversa (para manter indices)
        for pii in sorted(piis, key=lambda p: p.start, reverse=True):
            masked_text = masked_text[:pii.start] + pii.mask + masked_text[pii.end:]
            type_counts[pii.type] += 1

        return masked_text, piis, dict(type_counts)

    def unmask_text(self, masked_text: str, piis: List[PII]) -> str:
        """
        Desmaşara os PIIs em um texto.

        Args:
            masked_text: Texto mascarado
            piis: Lista original de PIIs

        Returns:
            Texto com valores originais restaurados
        """
        # Mapear masks → valores originais
        mask_to_value = {}
        for pii in piis:
            if pii.mask not in mask_to_value:
                mask_to_value[pii.mask] = []
            mask_to_value[pii.mask].append(pii.value)

        result = masked_text
        for mask, values in mask_to_value.items():
            # Substituir a primeira ocorrência do mask
            if mask in result and values:
                result = result.replace(mask, values[0], 1)

        return result


# Singleton global
_global_masker: Optional[PIIMasker] = None


def get_masker() -> PIIMasker:
    """Retorna a instância global do masker."""
    global _global_masker
    if _global_masker is None:
        _global_masker = PIIMasker()
    return _global_masker


def mask_message(text: str) -> Tuple[str, List[PII], Dict[str, int]]:
    """Mascara PIIs em uma mensagem usando masker global."""
    return get_masker().mask_text(text)


def unmask_message(masked_text: str, piis: List[PII]) -> str:
    """Desmaşara PIIs em uma mensagem usando masker global."""
    return get_masker().unmask_text(masked_text, piis)
