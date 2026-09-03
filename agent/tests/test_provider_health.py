"""Tests for the provider health probe.

The check this replaces reported "ready" for an account with no money in it,
which is how 31 tasks died on 402 one at a time behind a green tick. These
tests are mostly about refusing to say ready.
"""

from __future__ import annotations

import pytest

from src.core.provider_errors import classify_fatal_provider_error
from src.providers.health import ProviderHealth, _classify_response, describe, probe_provider


class _Response:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


class TestClassifyResponse:
    def test_a_completion_that_worked_is_ready(self):
        assert _classify_response(200, '{"choices":[]}')[0] == "ready"

    def test_no_balance_is_not_retryable(self):
        """Waiting does not add money. Retrying against 402 burns the budget."""
        status, _, retryable = _classify_response(402, '{"error":{"message":"Insufficient"}}')
        assert status == "no_balance"
        assert retryable is False

    @pytest.mark.parametrize("code", [401, 403])
    def test_a_rejected_key_is_not_retryable(self, code):
        status, _, retryable = _classify_response(code, "unauthorized")
        assert status == "bad_credentials"
        assert retryable is False

    def test_a_rate_limit_is_retryable(self):
        status, _, retryable = _classify_response(429, "slow down")
        assert status == "rate_limited"
        assert retryable is True

    def test_the_body_outranks_the_status_code(self):
        """The configured provider answers Insufficient Balance under a 400."""
        status, detail, retryable = _classify_response(
            400, '{"error":{"message":"Insufficient Balance","code":"invalid_request_error"}}'
        )
        assert status == "no_balance"
        assert retryable is False
        assert "Insufficient Balance" in detail

    def test_a_server_error_is_worth_retrying(self):
        assert _classify_response(503, "overloaded")[2] is True

    def test_the_shared_classifier_still_reads_worker_error_text(self):
        """Both layers ask the same question of the same provider."""
        assert classify_fatal_provider_error("Error code: 402 - insufficient balance")
        assert classify_fatal_provider_error("timed out after 300s") is None


class TestProbe:
    def _env(self, monkeypatch):
        monkeypatch.setattr("src.providers.llm._ensure_dotenv", lambda: None)
        monkeypatch.setattr("src.providers.llm._sync_provider_env", lambda: None)
        monkeypatch.setenv("LANGCHAIN_PROVIDER", "testprov")
        monkeypatch.setenv("LANGCHAIN_MODEL_NAME", "testmodel")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def test_a_valid_key_with_no_balance_is_not_ready(self, monkeypatch):
        """The exact live case: /models is 200 and the completion is 402.

        A probe that stopped at the key check would report ready here, which is
        the whole reason this module exists.
        """
        self._env(monkeypatch)
        monkeypatch.setattr(
            "requests.get", lambda *a, **k: _Response(200, '{"data":[]}')
        )
        monkeypatch.setattr(
            "requests.post", lambda *a, **k: _Response(402, "Insufficient Balance")
        )
        health = probe_provider()
        assert health.reachable is True
        assert health.credentials_ok is True
        assert health.spendable is False
        assert health.status == "no_balance"
        assert health.ok is False

    def test_a_provider_that_can_spend_is_ready(self, monkeypatch):
        self._env(monkeypatch)
        monkeypatch.setattr("requests.get", lambda *a, **k: _Response(200, '{"data":[]}'))
        monkeypatch.setattr("requests.post", lambda *a, **k: _Response(200, '{"choices":[]}'))
        health = probe_provider()
        assert health.ok is True
        assert health.spendable is True

    def test_a_rejected_key_never_reaches_the_spend_probe(self, monkeypatch):
        self._env(monkeypatch)
        monkeypatch.setattr("requests.get", lambda *a, **k: _Response(401, "bad key"))

        def explode(*args, **kwargs):
            raise AssertionError("must not spend against a rejected key")

        monkeypatch.setattr("requests.post", explode)
        health = probe_provider()
        assert health.status == "bad_credentials"
        assert health.credentials_ok is False

    def test_an_unreachable_provider_is_reported_as_retryable(self, monkeypatch):
        self._env(monkeypatch)

        def boom(*args, **kwargs):
            raise OSError("no route to host")

        monkeypatch.setattr("requests.get", boom)
        health = probe_provider()
        assert health.status == "unreachable"
        assert health.retryable is True

    def test_a_missing_configuration_is_a_result_not_a_crash(self, monkeypatch):
        monkeypatch.setattr("src.providers.llm._ensure_dotenv", lambda: None)
        monkeypatch.setattr("src.providers.llm._sync_provider_env", lambda: None)
        monkeypatch.setenv("LANGCHAIN_PROVIDER", "")
        monkeypatch.setenv("LANGCHAIN_MODEL_NAME", "")
        health = probe_provider()
        assert health.status == "not_configured"
        assert health.ok is False

    def test_the_probe_never_raises(self, monkeypatch):
        """A preflight that throws is a preflight that gets removed."""
        self._env(monkeypatch)
        monkeypatch.setattr(
            "requests.get", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
        )
        assert isinstance(probe_provider(), ProviderHealth)


class TestDescribe:
    def test_each_state_comes_with_the_action_that_fixes_it(self):
        assert "top up" in describe(ProviderHealth(status="no_balance"))
        assert "rotate it" in describe(ProviderHealth(status="bad_credentials"))
        assert "network" in describe(ProviderHealth(status="unreachable"))
        assert "transient" in describe(ProviderHealth(status="rate_limited"))

    def test_a_ready_provider_offers_no_remedy(self):
        assert "->" not in describe(ProviderHealth(status="ready", provider="p", model="m"))


class TestPreflightUsesIt:
    def test_no_balance_is_a_critical_failure_not_a_green_tick(self, monkeypatch):
        from src import preflight

        monkeypatch.setattr("src.providers.llm._ensure_dotenv", lambda: None)
        monkeypatch.setattr("src.providers.llm._sync_provider_env", lambda: None)
        monkeypatch.setenv("LANGCHAIN_PROVIDER", "testprov")
        monkeypatch.setenv("LANGCHAIN_MODEL_NAME", "testmodel")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(
            "src.providers.health.probe_provider",
            lambda **kwargs: ProviderHealth(
                provider="testprov", model="testmodel", status="no_balance", retryable=False
            ),
        )
        result = preflight._check_llm_provider()
        assert result.status == "error"
        assert result.critical is True
        assert "cannot resolve" in result.impact

    def test_a_rate_limit_is_reported_without_declaring_the_agent_dead(self, monkeypatch):
        from src import preflight

        monkeypatch.setattr("src.providers.llm._ensure_dotenv", lambda: None)
        monkeypatch.setattr("src.providers.llm._sync_provider_env", lambda: None)
        monkeypatch.setenv("LANGCHAIN_PROVIDER", "testprov")
        monkeypatch.setenv("LANGCHAIN_MODEL_NAME", "testmodel")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(
            "src.providers.health.probe_provider",
            lambda **kwargs: ProviderHealth(status="rate_limited", retryable=True),
        )
        result = preflight._check_llm_provider()
        assert result.critical is False
