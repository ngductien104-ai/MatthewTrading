"""Tests for run provenance.

A run that names its provider and model still cannot separate two runs a
commit apart, so a quality change has nothing to be attributed to. These check
that the answer is either true or absent, never invented.
"""

from __future__ import annotations

import subprocess

import pytest

from src.core.provenance import current_git_commit


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture()
def repo(tmp_path):
    """A real one-commit repository, since that is the contract under test."""
    if not subprocess.run(["git", "--version"], capture_output=True).returncode == 0:
        pytest.skip("git is not available")
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@example.com"], tmp_path)
    _git(["config", "user.name", "T"], tmp_path)
    (tmp_path / "a.txt").write_text("one", encoding="utf-8")
    _git(["add", "."], tmp_path)
    _git(["commit", "-qm", "first"], tmp_path)
    return tmp_path


def test_a_clean_tree_reports_a_bare_commit(repo):
    sha = current_git_commit(repo)
    assert len(sha) == 40
    assert not sha.endswith("-dirty")


def test_a_modified_tree_is_marked_dirty(repo):
    """Most work here runs on an uncommitted tree.

    A bare hash would claim the run is reproducible from that commit when the
    code it actually ran was never committed anywhere.
    """
    (repo / "a.txt").write_text("two", encoding="utf-8")
    assert current_git_commit(repo).endswith("-dirty")


def test_an_untracked_file_also_counts_as_dirty(repo):
    (repo / "b.txt").write_text("new", encoding="utf-8")
    assert current_git_commit(repo).endswith("-dirty")


def test_a_directory_that_is_not_a_repository_reports_nothing(tmp_path):
    """A hash invented here would look like provenance and be worse than none."""
    plain = tmp_path / "not_a_repo"
    plain.mkdir()
    assert current_git_commit(plain) == ""


def test_a_missing_directory_reports_nothing(tmp_path):
    assert current_git_commit(tmp_path / "gone") == ""


def test_the_default_reads_the_repository_whose_code_is_running():
    """Empty is acceptable off a checkout; a wrong-length string never is."""
    result = current_git_commit()
    assert result == "" or len(result.removesuffix("-dirty")) == 40


class TestSwarmRunCarriesIt:
    def test_the_four_reproducibility_fields_exist_and_default_to_unknown(self):
        from src.swarm.models import SwarmRun

        run = SwarmRun(id="r1", preset_name="p", created_at="2026-09-03T00:00:00Z")
        assert run.git_commit == ""
        assert run.seed is None
        assert run.temperature is None
        assert run.playbook_version == ""

    def test_temperature_is_none_rather_than_zero_when_unset(self):
        """0.0 would claim the run was deterministic when nobody said so."""
        from src.swarm.models import SwarmRun

        run = SwarmRun(id="r1", preset_name="p", created_at="2026-09-03T00:00:00Z")
        assert run.temperature is None
        assert run.temperature != 0.0

    def test_they_survive_a_round_trip_through_json(self, tmp_path):
        from src.swarm.models import SwarmRun

        run = SwarmRun(
            id="r1",
            preset_name="p",
            created_at="2026-09-03T00:00:00Z",
            git_commit="abc123-dirty",
            seed=7,
            temperature=0.2,
            playbook_version="v3",
        )
        restored = SwarmRun.model_validate_json(run.model_dump_json())
        assert restored.git_commit == "abc123-dirty"
        assert restored.seed == 7
        assert restored.temperature == 0.2
        assert restored.playbook_version == "v3"

    def test_an_older_run_json_without_the_fields_still_loads(self):
        """Runs already on disk predate these fields."""
        from src.swarm.models import SwarmRun

        legacy = '{"id":"r0","preset_name":"p","created_at":"2026-06-01T00:00:00Z"}'
        run = SwarmRun.model_validate_json(legacy)
        assert run.git_commit == ""
        assert run.seed is None
