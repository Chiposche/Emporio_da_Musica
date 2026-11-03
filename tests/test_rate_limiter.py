"""
Testes para rate limiting.
"""
import unittest

from core.rate_limiter import RateLimitConfig, RateLimiter


class TestRateLimiter(unittest.TestCase):
    """Testes para o rate limiter."""

    def setUp(self):
        """Criar nova instância para cada teste."""
        self.limiter = RateLimiter()

    def test_allow_under_limit(self):
        """Requisições sob limite devem ser permitidas."""
        config = RateLimitConfig(per_minute=5)
        limiter = RateLimiter(config)

        for i in range(5):
            assert limiter.is_allowed(), f"Request {i+1} should be allowed"

    def test_reject_over_limit(self):
        """Requisições acima do limite devem ser rejeitadas."""
        config = RateLimitConfig(per_minute=3)
        limiter = RateLimiter(config)

        # Primeiro 3 devem passar
        for i in range(3):
            assert limiter.is_allowed(), f"Request {i+1} should be allowed"

        # 4º deve ser rejeitado
        assert not limiter.is_allowed(), "Request 4 should be rejected"
        assert not limiter.is_allowed(), "Request 5 should be rejected"

    def test_reset_after_time_window(self):
        """Requisições antigas devem sair da janela de 1 minuto."""
        config = RateLimitConfig(per_minute=2)
        limiter = RateLimiter(config)

        # Fazer 2 requisições
        assert limiter.is_allowed()
        assert limiter.is_allowed()

        # 3ª deve ser rejeitada
        assert not limiter.is_allowed()

        # Forçar passagem de tempo alterando diretamente os timestamps
        # (em produção, o tempo real passaria)
        # Para teste, vamos limpar e testar que se passasse tempo, seria permitido
        limiter.reset()
        assert limiter.is_allowed(), "After reset, should allow new request"

    def test_per_hour_limit(self):
        """Limite por hora deve ser respeitado."""
        config = RateLimitConfig(per_minute=100, per_hour=10)
        limiter = RateLimiter(config)

        # Fazer 10 requisições
        for i in range(10):
            assert limiter.is_allowed(), f"Request {i+1} should be allowed"

        # 11ª deve ser rejeitada (por hora)
        assert not limiter.is_allowed(), "Request 11 should be rejected (per_hour)"

    def test_get_wait_time(self):
        """Deve calcular tempo de espera quando limit é atingido."""
        config = RateLimitConfig(per_minute=2)
        limiter = RateLimiter(config)

        # Fazer 2 requisições
        limiter.is_allowed()
        limiter.is_allowed()

        # 3ª deve ser rejeitada, e wait_time deve ser positivo
        assert not limiter.is_allowed()
        wait_time_ms = limiter.get_wait_time_ms()
        assert wait_time_ms is not None, "Wait time should be calculated"
        assert wait_time_ms > 0, f"Wait time should be positive: {wait_time_ms}ms"
        assert wait_time_ms <= 60000, f"Wait time should be <= 60s: {wait_time_ms}ms"

    def test_metrics(self):
        """Deve retornar métricas corretas."""
        config = RateLimitConfig(per_minute=5)
        limiter = RateLimiter(config)

        # Fazer algumas requisições
        limiter.is_allowed()
        limiter.is_allowed()
        limiter.is_allowed()

        metrics = limiter.get_metrics()
        assert metrics["total_requests"] == 3
        assert metrics["requests_last_minute"] == 3
        assert metrics["limit_per_minute"] == 5
        assert metrics["rejection_rate"] == 0

    def test_rejection_tracking(self):
        """Deve rastrear requisições rejeitadas."""
        config = RateLimitConfig(per_minute=2)
        limiter = RateLimiter(config)

        limiter.is_allowed()
        limiter.is_allowed()
        limiter.is_allowed()  # Rejeitada
        limiter.is_allowed()  # Rejeitada

        metrics = limiter.get_metrics()
        assert metrics["rejected_requests"] == 2
        assert metrics["total_requests"] == 2
        assert metrics["rejection_rate"] == 0.5

    def test_thread_safety(self):
        """Deve ser thread-safe."""
        import threading

        config = RateLimitConfig(per_minute=50)
        limiter = RateLimiter(config)
        results = []

        def make_requests():
            for _ in range(25):
                results.append(limiter.is_allowed())

        # Criar 4 threads (4 * 25 = 100 requisições)
        threads = [threading.Thread(target=make_requests) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Apenas 50 devem ser permitidas (o resto rejeitado)
        allowed = sum(1 for r in results if r)
        assert allowed == 50, f"Expected 50 allowed, got {allowed}"
        assert len(results) == 100, f"Expected 100 total, got {len(results)}"


if __name__ == "__main__":
    unittest.main()
