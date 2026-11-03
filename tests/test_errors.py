"""
Testes para categorização de erro e retry automático.
"""
import time
import unittest
from unittest.mock import MagicMock, patch, call

from core.errors import (
    ErrorType,
    ErrorRecovery,
    categorize_error,
    get_recovery_strategy,
    is_recoverable,
)


class TestErrorCategorization(unittest.TestCase):
    """Testes para categorização de erro."""

    def test_categorize_timeout(self):
        """Timeout deve ser categorizado como PROVIDER_TIMEOUT."""
        exc = TimeoutError("Request timed out")
        assert categorize_error(exc) == ErrorType.PROVIDER_TIMEOUT

    def test_categorize_rate_limit(self):
        """429 e rate limit devem ser categorizados como RATE_LIMITED."""
        exc1 = Exception("429 Too Many Requests")
        exc2 = Exception("Rate limit exceeded")
        assert categorize_error(exc1) == ErrorType.RATE_LIMITED
        assert categorize_error(exc2) == ErrorType.RATE_LIMITED

    def test_categorize_auth_error(self):
        """401/403 devem ser categorizados como AUTH_ERROR."""
        exc1 = Exception("401 Unauthorized")
        exc2 = Exception("403 Forbidden")
        assert categorize_error(exc1) == ErrorType.AUTH_ERROR
        assert categorize_error(exc2) == ErrorType.AUTH_ERROR

    def test_categorize_malformed_request(self):
        """400 e malformed devem ser categorizados como MALFORMED_REQUEST."""
        exc1 = Exception("400 Bad Request")
        exc2 = Exception("malformed JSON")
        assert categorize_error(exc1) == ErrorType.MALFORMED_REQUEST
        assert categorize_error(exc2) == ErrorType.MALFORMED_REQUEST

    def test_categorize_not_found(self):
        """404 deve ser categorizado como NOT_FOUND."""
        exc = Exception("404 Not Found")
        assert categorize_error(exc) == ErrorType.NOT_FOUND

    def test_categorize_unknown(self):
        """Erro genérico deve ser categorizado como UNKNOWN."""
        exc = Exception("Some random error")
        assert categorize_error(exc) == ErrorType.UNKNOWN


class TestRecoveryStrategy(unittest.TestCase):
    """Testes para estratégia de recuperação."""

    def test_timeout_is_retryable(self):
        """PROVIDER_TIMEOUT deve ser RETRY."""
        strategy = get_recovery_strategy(ErrorType.PROVIDER_TIMEOUT)
        assert strategy == ErrorRecovery.RETRY
        assert is_recoverable(ErrorType.PROVIDER_TIMEOUT)

    def test_rate_limit_is_retryable(self):
        """RATE_LIMITED deve ser RETRY."""
        strategy = get_recovery_strategy(ErrorType.RATE_LIMITED)
        assert strategy == ErrorRecovery.RETRY
        assert is_recoverable(ErrorType.RATE_LIMITED)

    def test_auth_error_is_fallback(self):
        """AUTH_ERROR deve ser FALLBACK."""
        strategy = get_recovery_strategy(ErrorType.AUTH_ERROR)
        assert strategy == ErrorRecovery.FALLBACK
        assert is_recoverable(ErrorType.AUTH_ERROR)

    def test_malformed_request_is_fail(self):
        """MALFORMED_REQUEST não deve ser recuperável."""
        strategy = get_recovery_strategy(ErrorType.MALFORMED_REQUEST)
        assert strategy == ErrorRecovery.FAIL
        assert not is_recoverable(ErrorType.MALFORMED_REQUEST)

    def test_not_found_is_fail(self):
        """NOT_FOUND não deve ser recuperável."""
        strategy = get_recovery_strategy(ErrorType.NOT_FOUND)
        assert strategy == ErrorRecovery.FAIL
        assert not is_recoverable(ErrorType.NOT_FOUND)

    def test_unknown_is_retryable(self):
        """UNKNOWN deve ser RETRY (otimista)."""
        strategy = get_recovery_strategy(ErrorType.UNKNOWN)
        assert strategy == ErrorRecovery.RETRY
        assert is_recoverable(ErrorType.UNKNOWN)


class TestRetryBackoff(unittest.TestCase):
    """Testes para lógica de retry com backoff."""

    @patch("agent._stream_llm")
    @patch("time.sleep")
    def test_retry_on_timeout(self, mock_sleep, mock_stream_llm):
        """Retry deve ser acionado em timeout."""
        from agent import _retry_with_backoff

        # Simular: 1º timeout, 2º sucesso
        mock_stream_llm.side_effect = [
            TimeoutError("Timeout"),
            iter([{"type": "done", "response": "Sucesso"}]),
        ]

        messages = [{"role": "user", "content": "test"}]
        cfg = {"model": "test-model"}

        results = list(_retry_with_backoff(messages, "key", 10, cfg))

        # Deve ter chamado stream_llm 2x
        assert mock_stream_llm.call_count == 2
        # Deve ter feito sleep (backoff)
        mock_sleep.assert_called()

    @patch("agent._stream_llm")
    def test_no_retry_on_malformed(self, mock_stream_llm):
        """Retry NÃO deve ser acionado em erro não-recuperável."""
        from agent import _retry_with_backoff

        mock_stream_llm.side_effect = Exception("400 Bad Request")

        messages = [{"role": "user", "content": "test"}]
        cfg = {"model": "test-model"}

        with self.assertRaises(Exception):
            list(_retry_with_backoff(messages, "key", 10, cfg))

        # Deve ter chamado apenas 1x (sem retry)
        assert mock_stream_llm.call_count == 1

    @patch("agent._stream_llm")
    @patch("time.sleep")
    def test_max_retries_exceeded(self, mock_sleep, mock_stream_llm):
        """Deve desistir após MAX_RETRIES."""
        from agent import _retry_with_backoff, MAX_RETRIES

        # Simular: sempre timeout
        mock_stream_llm.side_effect = TimeoutError("Timeout")

        messages = [{"role": "user", "content": "test"}]
        cfg = {"model": "test-model"}

        with self.assertRaises(TimeoutError):
            list(_retry_with_backoff(messages, "key", 10, cfg))

        # Deve ter tentado MAX_RETRIES vezes
        assert mock_stream_llm.call_count == MAX_RETRIES

    @patch("agent._stream_llm")
    @patch("time.sleep")
    def test_exponential_backoff(self, mock_sleep, mock_stream_llm):
        """Backoff deve ser exponencial (300ms, 600ms, 1200ms)."""
        from agent import _retry_with_backoff, RETRY_BACKOFF_MS

        mock_stream_llm.side_effect = TimeoutError("Timeout")

        messages = [{"role": "user", "content": "test"}]
        cfg = {"model": "test-model"}

        with self.assertRaises(TimeoutError):
            list(_retry_with_backoff(messages, "key", 10, cfg))

        # Deve ter chamado sleep com os backoffs corretos (N-1 chamadas)
        expected_calls = [
            call(RETRY_BACKOFF_MS[0] / 1000),  # 0.3s
            call(RETRY_BACKOFF_MS[1] / 1000),  # 0.6s
        ]
        mock_sleep.assert_has_calls(expected_calls)


if __name__ == "__main__":
    unittest.main()
