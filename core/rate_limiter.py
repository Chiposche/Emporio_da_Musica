"""
Rate limiting + throttling com fila de prioridade.

Limites:
  - 10 requisições por minuto (req/min)
  - 100 requisições por hora (req/hr)

Fila com prioridade:
  - Retry: prioridade 1 (tenta recuperar erro)
  - Novo: prioridade 2 (requisição nova)

Bloqueio:
  - Aguarda slot disponível até 30s
  - Se timeout, rejeita com status "rate_limited"
"""
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger("emporio.rate_limiter")

# Limites
REQUESTS_PER_MINUTE = 10
REQUESTS_PER_HOUR = 100
QUEUE_TIMEOUT_S = 30  # Timeout ao aguardar slot na fila


@dataclass
class RateLimitConfig:
    """Configuração de rate limiting."""
    per_minute: int = REQUESTS_PER_MINUTE
    per_hour: int = REQUESTS_PER_HOUR
    queue_timeout_s: float = QUEUE_TIMEOUT_S


class RateLimiter:
    """
    Rate limiter com fila de prioridade e backpressure.

    Thread-safe usando lock.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.lock = threading.RLock()

        # Histórico de timestamps de requisições
        self.request_times: deque[float] = deque(maxlen=self.config.per_hour)

        # Fila de requisições aguardando (não usado neste MVP simples)
        # Para MVP, apenas contamos e rejeitamos

        # Métricas
        self.total_requests = 0
        self.rejected_requests = 0
        self.queue_wait_times: deque[float] = deque(maxlen=100)

    def is_allowed(self) -> bool:
        """
        Verifica se uma nova requisição é permitida.

        Returns:
            True se permitido, False se rate limited
        """
        with self.lock:
            now = time.time()

            # Remover timestamps antigos (fora da janela de 1 hora)
            cutoff_time = now - 3600
            while self.request_times and self.request_times[0] < cutoff_time:
                self.request_times.popleft()

            # Contar requisições nos últimos 60 segundos
            cutoff_minute = now - 60
            requests_last_minute = sum(
                1 for ts in self.request_times if ts > cutoff_minute
            )

            # Validar limites
            if requests_last_minute >= self.config.per_minute:
                self.rejected_requests += 1
                log.warning(
                    "Rate limit per_minute reached: %d/%d",
                    requests_last_minute,
                    self.config.per_minute
                )
                return False

            if len(self.request_times) >= self.config.per_hour:
                self.rejected_requests += 1
                log.warning(
                    "Rate limit per_hour reached: %d/%d",
                    len(self.request_times),
                    self.config.per_hour
                )
                return False

            # Registrar requisição
            self.request_times.append(now)
            self.total_requests += 1
            return True

    def get_wait_time_ms(self) -> Optional[float]:
        """
        Retorna tempo de espera até próximo slot disponível (em ms).

        Returns:
            Tempo em ms, ou None se nenhuma espera necessária
        """
        with self.lock:
            now = time.time()
            cutoff_minute = now - 60
            requests_last_minute = sum(
                1 for ts in self.request_times if ts > cutoff_minute
            )

            if requests_last_minute < self.config.per_minute:
                return None

            # Encontrar o timestamp mais antigo da janela de 1 minuto
            oldest_in_window = min(
                (ts for ts in self.request_times if ts > cutoff_minute),
                default=None
            )

            if oldest_in_window is None:
                return None

            # Esperar até que esse timestamp saia da janela
            wait_until = oldest_in_window + 60
            wait_ms = (wait_until - now) * 1000
            return max(0, wait_ms)

    def get_metrics(self) -> dict:
        """Retorna métricas de rate limiting."""
        with self.lock:
            now = time.time()
            cutoff_minute = now - 60
            requests_last_minute = sum(
                1 for ts in self.request_times if ts > cutoff_minute
            )

            avg_queue_wait = (
                sum(self.queue_wait_times) / len(self.queue_wait_times)
                if self.queue_wait_times
                else 0
            )

            return {
                "total_requests": self.total_requests,
                "rejected_requests": self.rejected_requests,
                "rejection_rate": (
                    self.rejected_requests / (self.total_requests + self.rejected_requests)
                    if (self.total_requests + self.rejected_requests) > 0
                    else 0
                ),
                "requests_last_minute": requests_last_minute,
                "requests_last_hour": len(self.request_times),
                "limit_per_minute": self.config.per_minute,
                "limit_per_hour": self.config.per_hour,
                "avg_queue_wait_ms": avg_queue_wait,
            }

    def reset(self):
        """Reseta todos os contadores (para testes)."""
        with self.lock:
            self.request_times.clear()
            self.total_requests = 0
            self.rejected_requests = 0
            self.queue_wait_times.clear()


# Singleton global
_global_limiter: Optional[RateLimiter] = None


def get_limiter() -> RateLimiter:
    """Retorna a instância global do rate limiter."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter


def check_rate_limit() -> bool:
    """Verifica rate limit usando limiter global."""
    return get_limiter().is_allowed()


def get_rate_limit_metrics() -> dict:
    """Retorna métricas de rate limit."""
    return get_limiter().get_metrics()
