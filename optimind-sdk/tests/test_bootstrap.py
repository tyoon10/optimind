"""
Unit tests for the journal bootstrap (Task 3).

`plan_bootstrap` is pure and fully covered. `ensure_journal` is exercised with
the git operations monkeypatched (no real network/clone), asserting the
idempotent env-setting behaviour for each action.
"""

import os

import pytest

from src import bootstrap


# --- plan_bootstrap (pure) ---

@pytest.mark.parametrize("journal_path,repo_url,path_exists,is_git,expected", [
    ("/j", "url", False, False, "clone"),    # set, missing, has url
    ("/j", None,  False, False, "missing"),  # set, missing, no url
    ("/j", "url", True,  True,  "pull"),     # set, exists, git
    ("/j", "url", True,  False, "ready"),    # set, exists, non-git (bind mount)
    (None,  "url", True,  True,  "pull"),    # unset → default exists & git
    (None,  "url", True,  False, "ready"),   # unset → default exists, non-git
    (None,  "url", False, False, "clone"),   # unset → default missing, has url
    (None,  None,  False, False, "noop"),    # unset, nothing to do
])
def test_plan_bootstrap(journal_path, repo_url, path_exists, is_git, expected):
    assert bootstrap.plan_bootstrap(
        journal_path, repo_url, path_exists=path_exists, is_git=is_git) == expected


def test_default_journal_path_honors_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OPTIMIND_JOURNAL_HOME", str(tmp_path / "jh"))
    assert bootstrap.default_journal_path() == str(tmp_path / "jh")


def test_authed_url_injects_pat():
    assert bootstrap._authed_url("https://github.com/u/r.git", "ghp_x") == \
        "https://ghp_x@github.com/u/r.git"
    # already has credentials or non-https → untouched
    assert bootstrap._authed_url("https://tok@github.com/u/r.git", "ghp_x") == \
        "https://tok@github.com/u/r.git"
    assert bootstrap._authed_url("git@github.com:u/r.git", "ghp_x") == "git@github.com:u/r.git"


# --- ensure_journal (git monkeypatched) ---

@pytest.fixture()
def no_git(monkeypatch):
    """Replace git ops with recorders; clone creates the dir so isdir() passes."""
    calls = {"clone": [], "pull": []}
    monkeypatch.setattr(bootstrap, "_git_pull", lambda t: calls["pull"].append(t))

    def fake_clone(url, target):
        calls["clone"].append((url, target))
        os.makedirs(target, exist_ok=True)

    monkeypatch.setattr(bootstrap, "_git_clone", fake_clone)
    return calls


def test_ensure_ready_existing_non_git(monkeypatch, tmp_path, no_git):
    monkeypatch.setenv("OPTIMIND_JOURNAL_PATH", str(tmp_path))
    monkeypatch.delenv("JOURNAL_REPO_URL", raising=False)
    assert bootstrap.ensure_journal() == str(tmp_path)
    assert os.environ["OPTIMIND_JOURNAL_PATH"] == str(tmp_path)
    assert no_git["clone"] == [] and no_git["pull"] == []  # nothing fetched


def test_ensure_pull_existing_git(monkeypatch, tmp_path, no_git):
    (tmp_path / ".git").mkdir()
    monkeypatch.setenv("OPTIMIND_JOURNAL_PATH", str(tmp_path))
    assert bootstrap.ensure_journal() == str(tmp_path)
    assert no_git["pull"] == [str(tmp_path)]


def test_ensure_clone_when_unset_with_url(monkeypatch, tmp_path, no_git):
    target = tmp_path / "cloned"
    monkeypatch.delenv("OPTIMIND_JOURNAL_PATH", raising=False)
    monkeypatch.setenv("OPTIMIND_JOURNAL_HOME", str(target))
    monkeypatch.setenv("JOURNAL_REPO_URL", "https://github.com/u/r.git")
    monkeypatch.setenv("GITHUB_PAT", "ghp_x")
    assert bootstrap.ensure_journal() == str(target)
    assert os.environ["OPTIMIND_JOURNAL_PATH"] == str(target)
    assert no_git["clone"][0][0] == "https://ghp_x@github.com/u/r.git"


def test_ensure_noop_unset_no_url(monkeypatch, tmp_path, no_git):
    monkeypatch.delenv("OPTIMIND_JOURNAL_PATH", raising=False)
    monkeypatch.delenv("JOURNAL_REPO_URL", raising=False)
    monkeypatch.setenv("OPTIMIND_JOURNAL_HOME", str(tmp_path / "absent"))
    assert bootstrap.ensure_journal() is None
    assert "OPTIMIND_JOURNAL_PATH" not in os.environ
    assert no_git["clone"] == [] and no_git["pull"] == []


def test_ensure_missing_set_path_no_url(monkeypatch, tmp_path, no_git):
    gone = tmp_path / "gone"
    monkeypatch.setenv("OPTIMIND_JOURNAL_PATH", str(gone))
    monkeypatch.delenv("JOURNAL_REPO_URL", raising=False)
    assert bootstrap.ensure_journal() == str(gone)  # returns the set value
    assert not gone.exists()  # never created it
    assert no_git["clone"] == [] and no_git["pull"] == []
