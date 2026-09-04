"""Ask the provider the question a run will ask, before the run asks it.

The preflight this replaces made an *unauthenticated* GET against the base URL
and reported "ready" if anything answered. That check passes for a provider
with a revoked key and for one with no money in it, which is how 31 tasks came
to die on 402 one at a time behind a green tick.

Measured on this machine, 2026-09-03, against the configured provider:

* ``GET /models`` **with a valid key** returns ``200`` and a model list.
* ``POST /chat/completions`` returns ``402 Insufficient Balance``.

So credential validity and *spendability* are different properties, and only
the second one predicts whether work will run. A key check alone would have
reported ready here too. The probe therefore ends with a one-token completion:
it costs approximately nothing and is the only question whose answer matches
what a real task will get.

The three states are kept apart on purpose. "Cannot reach the provider" is a
network problem, "key rejected" is a configuration problem, and "no balance" is
a billing problem; they have different owners and different fixes, and
collapsing them into one boolean is what made the failure take a day to find.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

#: Seconds to wait on each probe request.
PROBE_TIMEOUT_SEC = 20.0

#: Tokens requested by the spend probe. One, because the point is to learn
#: whether the account may spend at all, not to generate anything.
PROBE_MAX_TOKENS = 1

#: Providers whose credential is an OAuth token rather than an API key. They
#: need their own probe: there is no ``OPENAI_API_KEY`` to find and no
#: ``/models`` to ask, so the key-shaped check reports ``not_configured`` for a
#: provider that is configured. Their remedy is a login, not a key rotation.
OAUTH_PROVIDERS = {"openai-codex", "openai_codex"}


@dataclass
class ProviderHealth:
    """What a provider will actually do when asked to work.

    Attributes:
        provider: Configured provider name.
        model: Configured model name.
        reachable: The endpoint answered at all.
        credentials_ok: The key was accepted.
        spendable: A real completion was allowed. This is the only field that
            predicts whether a run will produce anything.
        status: ``ready``, ``no_balance``, ``bad_credentials``, ``unreachable``,
            ``rate_limited``, ``not_logged_in``, ``client_rejected`` or
            ``not_configured``.
        detail: Human-readable specifics, provider text included where short.
        retryable: Whether waiting could change the answer. A rate limit is
            retryable; an empty balance is not, and burning a retry budget
            against one is exactly the waste this module exists to stop.
    """

    provider: str = ""
    model: str = ""
    reachable: bool = False
    credentials_ok: bool = False
    spendable: bool = False
    status: str = "not_configured"
    detail: str = ""
    retryable: bool = False

    @property
    def ok(self) -> bool:
        """Whether a run launched now can be expected to work."""
        return self.status == "ready"


def _classify_response(status_code: int, body: str) -> tuple[str, str, bool]:
    """Map an HTTP response onto ``(status, detail, retryable)``."""
    from src.core.provider_errors import classify_fatal_provider_error

    snippet = body.strip()[:200]
    if status_code == 200:
        return "ready", "", False
    if status_code in (401, 403):
        return "bad_credentials", f"HTTP {status_code}: {snippet}", False
    if status_code == 402:
        return "no_balance", f"HTTP {status_code}: {snippet}", False
    if status_code == 429:
        return "rate_limited", f"HTTP {status_code}: {snippet}", True
    # Some providers return 400 with the real reason in the body -- the
    # configured one answers "Insufficient Balance" under an
    # invalid_request_error code, so the text is authoritative over the number.
    reason = classify_fatal_provider_error(snippet)
    if reason:
        kind = "no_balance" if "credit" in reason or "402" in reason else "bad_credentials"
        return kind, f"HTTP {status_code}: {reason} -- {snippet}", False
    return "unreachable", f"HTTP {status_code}: {snippet}", status_code >= 500


def probe_provider(
    *,
    timeout: float = PROBE_TIMEOUT_SEC,
    provider: str = "",
    model: str = "",
) -> ProviderHealth:
    """Return what a provider will actually do.

    Args:
        timeout: Seconds to wait on each request.
        provider: Provider to ask about instead of the configured one. Used by
            failover to test a candidate *before* switching to it, so a run
            never moves onto a provider that is just as dead as the one it
            left.
        model: Model to ask about, required with *provider*. A provider name
            alone is not enough: a model that exists on one provider will
            usually 404 on another, and a probe that reused the old model name
            would report the candidate broken for the wrong reason.

    Returns:
        The health. Never raises: a preflight that throws is a preflight that
        gets removed.
    """
    health = ProviderHealth()
    restore: dict[str, str | None] = {}
    try:
        from src.providers.llm import _ensure_dotenv, _sync_provider_env

        _ensure_dotenv()
        if provider:
            # Ask about the candidate without leaving the process pointed at
            # it. A probe that mutated the live configuration would move every
            # concurrent worker onto an untested provider as a side effect of
            # asking a question about it.
            for name, value in (
                ("LANGCHAIN_PROVIDER", provider),
                ("LANGCHAIN_MODEL_NAME", model),
                ("OPENAI_API_KEY", None),
                ("OPENAI_BASE_URL", None),
                ("OPENAI_API_BASE", None),
            ):
                restore[name] = os.environ.get(name)
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
        _sync_provider_env()
    except Exception as exc:  # noqa: BLE001 - config problems are a result, not a crash
        health.detail = f"could not load provider config: {exc}"
        _restore_env(restore)
        return health

    try:
        return _probe_current(health, timeout=timeout)
    finally:
        _restore_env(restore)


def _restore_env(saved: dict[str, str | None]) -> None:
    """Put back exactly what was there, including what was absent."""
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def _probe_current(health: ProviderHealth, *, timeout: float) -> ProviderHealth:
    """Probe whatever the environment currently points at."""
    health.provider = (os.getenv("LANGCHAIN_PROVIDER") or "").strip()
    health.model = (os.getenv("LANGCHAIN_MODEL_NAME") or "").strip()
    base_url = (os.getenv("OPENAI_BASE_URL", "") or os.getenv("OPENAI_API_BASE", "")).rstrip("/")
    key = os.getenv("OPENAI_API_KEY", "")

    if not health.provider or not health.model:
        health.detail = "LANGCHAIN_PROVIDER or LANGCHAIN_MODEL_NAME is not set"
        return health
    if health.provider.lower() in OAUTH_PROVIDERS:
        return _probe_oauth(health, timeout=timeout)
    if not base_url or not key:
        health.detail = f"base URL or API key not set for {health.provider}"
        return health

    try:
        import requests
    except ImportError:  # pragma: no cover - requests is a hard dependency
        health.detail = "requests is not installed"
        return health

    headers = {"Authorization": f"Bearer {key}"}
    try:
        listed = requests.get(f"{base_url}/models", headers=headers, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - a dead network is a result
        health.status = "unreachable"
        health.detail = f"{type(exc).__name__}: {exc}"
        health.retryable = True
        return health

    health.reachable = True
    status, detail, retryable = _classify_response(listed.status_code, listed.text)
    if status != "ready":
        health.status, health.detail, health.retryable = status, detail, retryable
        return health
    health.credentials_ok = True

    # The question that matters. A 200 from /models means the key is real; it
    # says nothing about whether the account may spend, and spending is what a
    # task does.
    try:
        spent = requests.post(
            f"{base_url}/chat/completions",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "model": health.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": PROBE_MAX_TOKENS,
            },
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001
        health.status = "unreachable"
        health.detail = f"credentials accepted but completion failed: {exc}"
        health.retryable = True
        return health

    health.status, health.detail, health.retryable = _classify_response(
        spent.status_code, spent.text
    )
    health.spendable = health.status == "ready"
    return health


def _probe_oauth(health: ProviderHealth, *, timeout: float) -> ProviderHealth:
    """Probe a provider whose credential is an OAuth token.

    The presence of a token is not the question. Measured on this machine on
    2026-09-04: the stored ChatGPT token existed, carried an account id, and
    answered ``401 token_revoked`` to a real request. A check that stopped at
    the token file would have called that ready -- the same green tick over a
    dead provider this module was written to remove, still standing in the one
    path that has no API key to check.

    So this asks the endpoint a run asks, with the body a run sends, and reads
    the status code the run would read.
    """
    try:
        import httpx

        from src.providers.openai_codex import (
            OpenAICodexLLM,
            get_openai_codex_login_status,
        )
    except ImportError as exc:  # pragma: no cover - both are hard dependencies
        health.detail = f"OAuth provider support is unavailable: {exc}"
        return health

    try:
        llm = OpenAICodexLLM(model=health.model, timeout=int(timeout))
        headers = llm._headers()
        token = get_openai_codex_login_status()
    except Exception as exc:  # noqa: BLE001 - "no usable token" is a result
        health.status = "not_logged_in"
        health.detail = str(exc)
        return health

    body = llm._body([{"role": "user", "content": "ping"}], stream=True)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, trust_env=True) as client:
            with client.stream("POST", llm.codex_url, headers=headers, json=body) as response:
                code = response.status_code
                text = "" if code == 200 else response.read().decode("utf-8", "ignore")
    except Exception as exc:  # noqa: BLE001 - a dead network is a result
        health.status = "unreachable"
        health.detail = f"{type(exc).__name__}: {exc}"
        health.retryable = True
        return health

    health.reachable = True
    health.status, health.detail, health.retryable = _classify_response(code, text)
    # A rejected token never proved anything about the account; an empty
    # balance and a rate limit both did. Kept explicit rather than inferred
    # from ``spendable``, because they are separate questions with separate
    # owners.
    health.credentials_ok = health.status in {"ready", "no_balance", "rate_limited"}
    health.spendable = health.status == "ready"
    if health.status == "bad_credentials" and _token_is_live(token):
        # A token minted minutes ago, still inside its own validity window, and
        # refused anyway. Measured 2026-09-04: a token 4 minutes old with 51
        # hours left came back ``token_revoked`` under both the vibe-trading
        # and codex_cli_rs originators, while the official Codex CLI succeeded
        # on the same account from the same machine. So the endpoint is
        # refusing tokens minted by *this* OAuth client, and telling the reader
        # to log in again sends them round a loop that cannot terminate. That
        # is the same defect as pointing at a key file with no key in it.
        health.status = "client_rejected"
    return health


def _token_is_live(token: Any) -> bool:
    """Whether an OAuth token is inside its own validity window.

    A stale token and a refused-on-principle token both answer 401, and only
    the first one is fixed by logging in again.
    """
    import time

    expires = getattr(token, "expires", None)
    if expires is None:
        return False
    try:
        # The store keeps epoch milliseconds.
        return float(expires) / 1000.0 > time.time()
    except (TypeError, ValueError):
        return False


def describe(health: ProviderHealth) -> str:
    """Return a one-line summary, and what to do about it."""
    remedies = {
        "ready": "",
        "no_balance": "top up the provider account, or switch LANGCHAIN_PROVIDER",
        "bad_credentials": "the API key is rejected; rotate it in agent/.env",
        "unreachable": "check network access to the provider",
        "rate_limited": "wait and retry; this one is transient",
        "not_logged_in": "no usable OAuth token; run: vibe-trading provider login",
        "client_rejected": (
            "the provider refuses tokens minted by this OAuth client; logging "
            "in again will not change it -- switch LANGCHAIN_PROVIDER"
        ),
        "not_configured": "set LANGCHAIN_PROVIDER, LANGCHAIN_MODEL_NAME and the key",
    }
    label = f"{health.provider or 'provider'} / {health.model or 'model'}: {health.status}"
    remedy = remedies.get(health.status, "")
    # An OAuth provider has no key in agent/.env to rotate, so the generic
    # credential remedy sends the reader to a file that cannot fix it.
    if health.provider.lower() in OAUTH_PROVIDERS and health.status in {
        "bad_credentials",
        "not_logged_in",
    }:
        remedy = f"run: vibe-trading provider login {health.provider}"
    parts: list[Any] = [label]
    if health.detail:
        parts.append(health.detail)
    if remedy:
        parts.append(f"-> {remedy}")
    return " | ".join(str(part) for part in parts)
