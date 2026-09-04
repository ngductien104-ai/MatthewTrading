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


class _CodexToken:
    account_id = "acct-test"
    access = "token-test"

    def __init__(self, expires_in_hours=51.0):
        import time

        self.expires = (time.time() + expires_in_hours * 3600) * 1000.0


class _FakeStream:
    """Stands in for the httpx streaming response the OAuth probe reads."""

    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self._text = text

    def read(self):
        return self._text.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeClient:
    def __init__(self, response):
        self._response = response

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def stream(self, *args, **kwargs):
        return self._response


class TestOAuthProbe:
    """The OAuth path had no probe at all, and said ready on a token file.

    Measured 2026-09-04: the stored token existed, carried an account id, and
    answered 401 token_revoked. Every test here is about refusing to call that
    configured, or ready.
    """

    def _env(self, monkeypatch):
        monkeypatch.setattr("src.providers.llm._ensure_dotenv", lambda: None)
        monkeypatch.setattr("src.providers.llm._sync_provider_env", lambda: None)
        monkeypatch.setenv("LANGCHAIN_PROVIDER", "openai-codex")
        monkeypatch.setenv("LANGCHAIN_MODEL_NAME", "openai-codex/gpt-5.6-terra")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.delenv("OPENAI_API_BASE", raising=False)
        monkeypatch.setattr(
            "src.providers.openai_codex._get_codex_token", lambda: _CodexToken()
        )
        monkeypatch.setattr(
            "src.providers.openai_codex.get_openai_codex_login_status",
            lambda: _CodexToken(),
        )

    def test_a_missing_api_key_does_not_make_an_oauth_provider_unconfigured(
        self, monkeypatch
    ):
        """The bug this fixes: no OPENAI_API_KEY, so the key-shaped check gave up.

        It reported ``not_configured`` -- pointing at env vars -- for a
        provider that was configured and whose real fault was a dead token.
        """
        self._env(monkeypatch)
        monkeypatch.setattr("httpx.Client", _FakeClient(_FakeStream(200)))
        assert probe_provider().status != "not_configured"

    def test_an_expired_token_is_bad_credentials_not_ready(self, monkeypatch):
        """A stale credential. Logging in again is the fix, and it is offered."""
        self._env(monkeypatch)
        monkeypatch.setattr(
            "src.providers.openai_codex.get_openai_codex_login_status",
            lambda: _CodexToken(expires_in_hours=-1.0),
        )
        monkeypatch.setattr(
            "httpx.Client",
            _FakeClient(
                _FakeStream(401, '{"error":{"code":"token_revoked"}}')
            ),
        )
        health = probe_provider()
        assert health.status == "bad_credentials"
        assert health.ok is False
        assert health.credentials_ok is False
        assert health.spendable is False
        assert "token_revoked" in health.detail

    def test_a_live_token_refused_anyway_is_not_sent_to_log_in_again(
        self, monkeypatch
    ):
        """The live case on 2026-09-04, and the loop it would have started.

        The token was 4 minutes old with 51 hours left and still came back
        token_revoked, under both originators, while the official Codex CLI
        worked on the same account. Telling the reader to log in again would
        send them round a loop that cannot terminate -- the same defect as
        pointing at a key file that holds no key.
        """
        self._env(monkeypatch)
        monkeypatch.setattr(
            "httpx.Client",
            _FakeClient(_FakeStream(401, '{"error":{"code":"token_revoked"}}')),
        )
        health = probe_provider()
        assert health.status == "client_rejected"
        assert health.ok is False
        line = describe(health)
        assert "will not change it" in line
        assert "provider login" not in line

    def test_a_token_that_can_spend_is_ready(self, monkeypatch):
        self._env(monkeypatch)
        monkeypatch.setattr("httpx.Client", _FakeClient(_FakeStream(200)))
        health = probe_provider()
        assert health.ok is True
        assert health.spendable is True
        assert health.credentials_ok is True

    def test_no_usable_token_is_not_logged_in(self, monkeypatch):
        self._env(monkeypatch)

        def unauthenticated():
            raise RuntimeError("OpenAI Codex is not logged in.")

        monkeypatch.setattr(
            "src.providers.openai_codex._get_codex_token", unauthenticated
        )

        def explode(*args, **kwargs):
            raise AssertionError("must not call the endpoint without a token")

        monkeypatch.setattr("httpx.Client", explode)
        health = probe_provider()
        assert health.status == "not_logged_in"
        assert health.ok is False

    def test_an_exhausted_oauth_account_is_told_apart_from_a_dead_token(
        self, monkeypatch
    ):
        """Billing and authentication have different owners and different fixes."""
        self._env(monkeypatch)
        monkeypatch.setattr(
            "httpx.Client", _FakeClient(_FakeStream(402, "Insufficient Balance"))
        )
        health = probe_provider()
        assert health.status == "no_balance"
        assert health.credentials_ok is True

    def test_the_oauth_probe_never_raises(self, monkeypatch):
        self._env(monkeypatch)

        def boom(*args, **kwargs):
            raise OSError("no route to host")

        monkeypatch.setattr("httpx.Client", boom)
        health = probe_provider()
        assert isinstance(health, ProviderHealth)
        assert health.status == "unreachable"
        assert health.retryable is True


class TestDescribe:
    def test_each_state_comes_with_the_action_that_fixes_it(self):
        assert "top up" in describe(ProviderHealth(status="no_balance"))
        assert "rotate it" in describe(ProviderHealth(status="bad_credentials"))
        assert "network" in describe(ProviderHealth(status="unreachable"))
        assert "transient" in describe(ProviderHealth(status="rate_limited"))

    def test_an_oauth_failure_is_not_sent_to_rotate_a_key_that_does_not_exist(self):
        """There is no key in agent/.env for an OAuth provider to rotate."""
        for status in ("bad_credentials", "not_logged_in"):
            line = describe(ProviderHealth(status=status, provider="openai-codex"))
            assert "provider login openai-codex" in line
            assert "agent/.env" not in line

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

    def test_a_revoked_oauth_token_is_no_longer_a_green_tick(self, monkeypatch):
        """The regression that motivated this: ready, on a dead provider.

        The old branch returned ready whenever a token file existed. It never
        asked the endpoint anything, so a revoked token passed preflight and
        every task behind it died one at a time.
        """
        from src import preflight

        monkeypatch.setattr("src.providers.llm._ensure_dotenv", lambda: None)
        monkeypatch.setattr("src.providers.llm._sync_provider_env", lambda: None)
        monkeypatch.setenv("LANGCHAIN_PROVIDER", "openai-codex")
        monkeypatch.setenv("LANGCHAIN_MODEL_NAME", "openai-codex/gpt-5.6-terra")
        monkeypatch.setattr(
            "src.providers.health.probe_provider",
            lambda **kwargs: ProviderHealth(
                provider="openai-codex",
                model="openai-codex/gpt-5.6-terra",
                status="bad_credentials",
                detail='HTTP 401: {"code":"token_revoked"}',
                retryable=False,
            ),
        )
        result = preflight._check_llm_provider()
        assert result.status == "error"
        assert result.critical is True
        assert "provider login openai-codex" in result.message

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
