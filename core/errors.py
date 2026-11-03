"""
Categorização de erros para retry automático e logging estruturado.

Tipos de erro:
  - PROVIDER_TIMEOUT: Timeout na requisição (recuperável com retry)
  - MALFORMED_REQUEST: Argumentos inválidos para ferramenta (não recuperável)
  - NOT_FOUND: Dado não encontrado (não recuperável)
  - RATE_LIMITED: Rate limit atingido (recuperável com backoff)
  - HALLUCINATION: Resposta sem dados válidos (não recuperável)
  - UNKNOWN: Erro genérico (tenta retry)
"""
from enum import Enum


class ErrorType(Enum):
    """Tipos de erro categorizados."""
    PROVIDER_TIMEOUT = "provider_timeout"          # Timeout na API
    RATE_LIMITED = "rate_limited"                  # 429 Too Many Requests
    AUTH_ERROR = "auth_error"                      # 401/403 (não retry)
    MALFORMED_REQUEST = "malformed_request"        # 400 Bad Request (não retry)
    NOT_FOUND = "not_found"                        # 404 (não retry)
    HALLUCINATION = "hallucination"                # LLM inventou dados (não retry)
    TOOL_ERROR = "tool_error"                      # Erro ao executar ferramenta
    UNKNOWN = "unknown"                            # Erro desconhecido (tenta retry)


class ErrorRecovery(Enum):
    """Estratégia de recuperação."""
    RETRY = "retry"                                # Tentar novamente (backoff exponencial)
    FALLBACK = "fallback"                          # Trocar provider
    FAIL = "fail"                                  # Falhar graciosamente (sem retry)


# Mapa: ErrorType -> ErrorRecovery
ERROR_RECOVERY_MAP = {
    ErrorType.PROVIDER_TIMEOUT: ErrorRecovery.RETRY,
    ErrorType.RATE_LIMITED: ErrorRecovery.RETRY,
    ErrorType.AUTH_ERROR: ErrorRecovery.FALLBACK,
    ErrorType.MALFORMED_REQUEST: ErrorRecovery.FAIL,
    ErrorType.NOT_FOUND: ErrorRecovery.FAIL,
    ErrorType.HALLUCINATION: ErrorRecovery.FAIL,
    ErrorType.TOOL_ERROR: ErrorRecovery.FAIL,
    ErrorType.UNKNOWN: ErrorRecovery.RETRY,
}


def categorize_error(exception: Exception) -> ErrorType:
    """
    Categoriza uma exception em ErrorType.

    Args:
        exception: A exception a categorizar

    Returns:
        ErrorType correspondente
    """
    error_msg = str(exception).lower()
    error_type = type(exception).__name__

    # Timeout
    if "timeout" in error_msg or "timed out" in error_msg:
        return ErrorType.PROVIDER_TIMEOUT

    # Rate limit
    if "429" in error_msg or "rate" in error_msg or "quota" in error_msg:
        return ErrorType.RATE_LIMITED

    # Auth errors
    if "401" in error_msg or "403" in error_msg or "unauthorized" in error_msg or "forbidden" in error_msg:
        return ErrorType.AUTH_ERROR

    # Bad request
    if "400" in error_msg or "malformed" in error_msg or "invalid" in error_msg:
        return ErrorType.MALFORMED_REQUEST

    # Not found
    if "404" in error_msg or "not found" in error_msg:
        return ErrorType.NOT_FOUND

    # Tool errors
    if "tool" in error_type.lower():
        return ErrorType.TOOL_ERROR

    # Default: unknown (will retry)
    return ErrorType.UNKNOWN


def get_recovery_strategy(error_type: ErrorType) -> ErrorRecovery:
    """Retorna estratégia de recuperação para um tipo de erro."""
    return ERROR_RECOVERY_MAP.get(error_type, ErrorRecovery.FAIL)


def is_recoverable(error_type: ErrorType) -> bool:
    """Verifica se um erro é recuperável."""
    strategy = get_recovery_strategy(error_type)
    return strategy in (ErrorRecovery.RETRY, ErrorRecovery.FALLBACK)
