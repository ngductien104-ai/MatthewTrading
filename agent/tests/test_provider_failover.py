"""Tests for moving a run onto a provider that can work.

A limit worth stating up front, and repeated in the branch's PROGRESS file:
**no second provider is configured on this machine.** Every entry but the
active one in agent/.env is a commented placeholder, so the switch below has
never carried a real run. What is verified here is the decision logic and the
refusals; what is not verified is a live handover, and no claim is made that
it has been.
"""

from __future__ import annotations

import os

import pytest

from src.providers.failover import (
    FALLBACKS_ENV,
    Candidate,
    activate,
    configured_fallbacks,
    describe,
    failover,
)
from src.providers.health import ProviderHealth


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Never let a test leave the process pointed somewhere new."""
    monkeypatch.setattr("src.providers.llm._ensure_dotenv", lambda: None)
    monkeypatch.setattr("src.providers.llm._sync_provider_env", lambda: None)
    monkeypatch.setenv("LANGCHAIN_PROVIDER", "deadprov")
    monkeypatch.setenv("LANGCHAIN_MODEL_NAME", "deadmodel")
    monkeypatch.delenv(FALLBACKS_ENV, raising=False)


class TestConfiguredFallbacks:
    def test_unset_means_no_failover(self):
        """Off by default. A chain invented here would move runs unasked."""
        assert configured_fallbacks("") == []

    def test_entries_are_parsed_in_order(self):
        chain = configured_fallbacks("groq:llama-3.3, ollama:qwen3")
        assert [str(c) for c in chain] == ["groq:llama-3.3", "ollama:qwen3"]

    def test_a_provider_without_a_model_is_dropped_rather_than_guessed(self):
        """deepseek-v4-pro does not exist on Groq; carrying it over 404s."""
        assert configured_fallbacks("groq") == []
        assert configured_fallbacks("groq:, openai:gpt-5") == [
            Candidate("openai", "gpt-5")
        ]

    def test_it_reads_the_environment_when_given_nothing(self, monkeypatch):
        monkeypatch.setenv(FALLBACKS_ENV, "zai:glm-5")
        assert configured_fallbacks() == [Candidate("zai", "glm-5")]


class TestFailoverPicksOnlyWhatWorks:
    def _health(self, monkeypatch, answers: dict[str, str]):
        seen: list[tuple[str, str]] = []

        def fake_probe(*, provider="", model="", **kwargs):
            seen.append((provider, model))
            return ProviderHealth(
                provider=provider, model=model, status=answers.get(provider, "unreachable")
            )

        monkeypatch.setattr("src.providers.failover.probe_provider", fake_probe)
        return seen

    def test_it_switches_to_the_first_healthy_candidate(self, monkeypatch):
        self._health(monkeypatch, {"good": "ready"})
        switch = failover(fallbacks=[Candidate("good", "m1")])
        assert switch.switched is True
        assert switch.from_provider == "deadprov"
        assert switch.to_provider == "good:m1"
        assert os.environ["LANGCHAIN_PROVIDER"] == "good"
        assert os.environ["LANGCHAIN_MODEL_NAME"] == "m1"

    def test_a_candidate_with_no_balance_is_skipped_not_switched_to(self, monkeypatch):
        """Otherwise the run trades one dead endpoint for another."""
        seen = self._health(monkeypatch, {"broke": "no_balance", "good": "ready"})
        switch = failover(
            fallbacks=[Candidate("broke", "m1"), Candidate("good", "m2")]
        )
        assert switch.to_provider == "good:m2"
        assert [p for p, _ in seen] == ["broke", "good"]

    def test_no_healthy_candidate_leaves_the_provider_alone(self, monkeypatch):
        self._health(monkeypatch, {"a": "no_balance", "b": "bad_credentials"})
        switch = failover(fallbacks=[Candidate("a", "m"), Candidate("b", "m")])
        assert switch.switched is False
        assert os.environ["LANGCHAIN_PROVIDER"] == "deadprov"
        assert "no configured fallback is healthy" in switch.reason

    def test_the_current_provider_is_never_probed_as_its_own_fallback(self, monkeypatch):
        seen = self._health(monkeypatch, {"deadprov": "ready"})
        switch = failover(fallbacks=[Candidate("deadprov", "deadmodel")])
        assert seen == []
        assert switch.switched is False

    def test_an_empty_chain_says_why_rather_than_failing(self):
        switch = failover(fallbacks=[])
        assert switch.switched is False
        assert FALLBACKS_ENV in switch.reason

    def test_a_probe_that_explodes_is_a_skipped_candidate_not_a_crash(self, monkeypatch):
        def boom(*, provider="", model="", **kwargs):
            if provider == "bad":
                raise RuntimeError("probe exploded")
            return ProviderHealth(provider=provider, status="ready")

        monkeypatch.setattr("src.providers.failover.probe_provider", boom)
        switch = failover(fallbacks=[Candidate("bad", "m"), Candidate("good", "m")])
        assert switch.to_provider == "good:m"
        assert any("probe exploded" in line for line in switch.probed)

    def test_every_candidate_tried_is_recorded(self, monkeypatch):
        self._health(monkeypatch, {"a": "no_balance", "b": "ready"})
        switch = failover(fallbacks=[Candidate("a", "m"), Candidate("b", "m")])
        assert "a:m no_balance" in switch.probed
        assert "a:m no_balance" in describe(switch)


class TestActivateDoesNotLeaveTheOldEndpointBehind:
    def test_the_derived_openai_variables_are_cleared(self, monkeypatch):
        """A stale base URL sends the new model to the old provider."""
        monkeypatch.setenv("OPENAI_BASE_URL", "https://old.invalid/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-old")
        activate(Candidate("newprov", "newmodel"))
        assert os.environ["LANGCHAIN_PROVIDER"] == "newprov"
        assert "OPENAI_BASE_URL" not in os.environ
        assert "OPENAI_API_KEY" not in os.environ


class TestTheProbeDoesNotMoveTheProcessWhileAsking:
    def test_probing_a_candidate_restores_the_live_configuration(self, monkeypatch):
        """A question about a provider must not be a switch to it."""
        from src.providers.health import probe_provider

        monkeypatch.setenv("OPENAI_BASE_URL", "https://live.invalid/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-live")

        class _Resp:
            status_code = 200
            text = '{"data":[]}'

        monkeypatch.setattr("requests.get", lambda *a, **k: _Resp())
        monkeypatch.setattr("requests.post", lambda *a, **k: _Resp())

        health = probe_provider(provider="candidate", model="candidate-model")
        assert health.provider == "candidate"
        assert os.environ["LANGCHAIN_PROVIDER"] == "deadprov"
        assert os.environ["LANGCHAIN_MODEL_NAME"] == "deadmodel"
        assert os.environ["OPENAI_BASE_URL"] == "https://live.invalid/v1"

    def test_a_variable_that_was_absent_stays_absent(self, monkeypatch):
        from src.providers.health import probe_provider

        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        probe_provider(provider="candidate", model="candidate-model")
        assert "OPENAI_BASE_URL" not in os.environ
        assert "OPENAI_API_KEY" not in os.environ


class TestTheRuntimeUsesIt:
    def test_the_retry_loop_tries_a_failover_before_giving_up(self):
        import inspect

        from src.swarm import runtime

        source = inspect.getsource(runtime.SwarmRuntime._run_worker_with_retries)
        assert "_failover_for_run" in source
        # A successful switch must retry, not return the failed result.
        assert "switch.switched:\n                    continue" in source

    def test_the_switch_is_emitted_as_an_event_not_only_logged(self):
        """run.json records the provider the run STARTED on."""
        import inspect

        from src.swarm import runtime

        source = inspect.getsource(runtime.SwarmRuntime._failover_for_run)
        assert '"provider_failover"' in source
        assert "provider_failover_unavailable" in source
        assert '"probed"' in source

    def test_a_broken_failover_does_not_crash_the_run(self, monkeypatch):
        from src.swarm.models import SwarmTask
        from src.swarm.runtime import SwarmRuntime
        from src.swarm.store import SwarmStore

        runtime = SwarmRuntime.__new__(SwarmRuntime)
        runtime._store = None  # type: ignore[assignment]
        monkeypatch.setattr(
            "src.providers.failover.failover",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("x")),
        )
        task = SwarmTask(id="t", agent_id="a", prompt_template="p")
        assert runtime._failover_for_run("run", task, "out of credit") is None
        assert SwarmStore is not None
