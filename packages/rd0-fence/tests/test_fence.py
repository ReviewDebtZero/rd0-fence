import json
from pathlib import Path

from rd0_fence import Issue, check, parse_diff
from rd0_fence.cli import main
from rd0_fence.diff import files_from_patches
from rd0_fence.github import linked_issues
from rd0_fence.render import MARKER, markdown
from rd0_fence.scope import kind_of

HERE = Path(__file__).parent
EX = HERE.parent / "examples"
FIX = HERE / "fixtures"


def _example():
    issue = Issue.from_text(*EX.joinpath("issue.md").read_text().split("\n", 1))
    return check(issue, parse_diff(EX.joinpath("pr.diff").read_text()))


def _flagged(rep):
    return {(p.path, p.hunk) for p in rep.flagged}


def test_issue_extracts_paths_names_and_intents():
    it = Issue.from_text("`slugify` drops letters", "See `utils/text.py::slugify`. Please add a test.")
    assert "utils/text.py" in it.paths
    assert "slugify" in it.names
    assert it.wants_tests and not it.wants_ci and not it.wants_deps


def test_parse_diff_files_hunks_and_status():
    files = parse_diff(EX.joinpath("pr.diff").read_text())
    assert [f.path for f in files][:2] == ["utils/text.py", "tests/test_text.py"]
    text = files[0]
    assert len(text.hunks) == 2 and text.hunks[1].whitespace_only() and not text.hunks[0].whitespace_only()
    assert "slugify" in text.hunks[0].symbols() or "slugify" in text.hunks[0].identifiers()


def test_example_flags_only_the_extras():
    rep = _example()
    assert _flagged(rep) == {
        ("utils/text.py", "@@ +23 def truncate(value, n):"),
        ("utils/dates.py", None),
        (".github/workflows/ci.yml", None),
        ("requirements.txt", None),
    }
    assert all(p.reason for p in rep.flagged)
    assert rep.anchored and 0 < rep.out_fraction < 1


def test_tests_for_in_scope_file_are_in_scope():
    rep = _example()
    assert next(p for p in rep.parts if p.path == "tests/test_text.py").in_scope


def test_vague_issue_does_not_flag_plain_code():
    rep = check(
        Issue.from_text("It is slow", "Things are slow sometimes."), parse_diff(EX.joinpath("pr.diff").read_text())
    )
    assert not rep.anchored
    assert {p.path for p in rep.flagged} <= {".github/workflows/ci.yml", "requirements.txt", "utils/text.py"}


def test_ci_in_scope_when_issue_asks():
    files = parse_diff(EX.joinpath("pr.diff").read_text())
    rep = check(Issue.from_text("Add Python 3.12 to the CI matrix", "Update `.github/workflows/ci.yml`."), files)
    assert ".github/workflows/ci.yml" not in {p.path for p in rep.flagged}


def test_kind_of():
    assert kind_of(".github/workflows/x.yml") == "ci"
    assert kind_of("web/package-lock.json") == "lockfile"
    assert kind_of("pyproject.toml") == "manifest"
    assert kind_of("src/a/test_b.py") == "test"
    assert kind_of("docs/index.md") == "docs"
    assert kind_of("src/app.ts") == "code"


def test_files_from_github_patches():
    files = files_from_patches([{"filename": "a.py", "status": "added", "patch": "@@ -0,0 +1,2 @@\n+x = 1\n+y = 2"}])
    assert files[0].status == "added" and files[0].added == 2


def test_linked_issues():
    body = "Fixes #12 and closes octo/lib#3. See https://github.com/o/r/issues/9"
    assert linked_issues(body, "o/r") == [("o/r", 12), ("octo/lib", 3), ("o/r", 9)]


def test_markdown_has_marker_and_reasons():
    md = markdown(_example(), "issue #1")
    assert md.startswith(MARKER) and "issue #1" in md and "`requirements.txt`" in md


def test_cli_json(capsys):
    code = main(["check", "--issue", str(EX / "issue.md"), "--diff", str(EX / "pr.diff"), "--format", "json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["total_lines"] == 22 and len(out["flagged"]) == 4


def test_cli_fail_over(capsys):
    code = main(["check", "--issue", str(EX / "issue.md"), "--diff", str(EX / "pr.diff"), "--fail-over", "0.1"])
    assert code == 1 and "outside the issue's scope" in capsys.readouterr().out


def _fixture(name):
    d = FIX / name
    i = json.loads((d / "issue.json").read_text())
    return check(Issue.from_text(i["title"], i["body"], i["number"]), parse_diff((d / "pr.diff").read_text()))


def test_aidev_fixture_tests_fix_stays_in_scope():
    assert not _fixture("aidev_4164885376").flagged


def test_aidev_fixture_json_fix_flags_ci_deps_and_unrelated_test():
    assert {p.path for p in _fixture("aidev_4078493051").flagged} == {
        ".github/workflows/ci.yml",
        "package.json",
        "tests/docker-tasking.test.js",
    }


def test_aidev_fixture_windows_ci_fix_in_scope():
    assert not _fixture("aidev_4087484391").flagged


def test_plain_diff_u_and_header_like_content():
    d = "--- a.py\t2026-01-01\n+++ a.py\t2026-01-02\n@@ -1,2 +1,2 @@\n--- x\n+++ y\n ctx\n"
    files = parse_diff(d)
    assert [f.path for f in files] == ["a.py"]
    assert files[0].hunks[0].removed == ["-- x"] and files[0].hunks[0].added == ["++ y"]


def test_space_change_inside_string_is_not_formatting():
    d = 'diff --git a/a.py b/a.py\n@@ -1,1 +1,1 @@\n-x = "a b"\n+x = "a  b"\n'
    assert not parse_diff(d)[0].hunks[0].whitespace_only()
    d2 = 'diff --git a/a.py b/a.py\n@@ -1,1 +1,1 @@\n-x = f( 1 )\n+x = f(1)\n'
    assert parse_diff(d2)[0].hunks[0].whitespace_only()


def test_file_path_does_not_add_parent_dir_anchor():
    it = Issue.from_text("Bug", "Crash in src/core/login.py; see also docs/guides/ folder")
    assert "src/core" not in it.dirs and "docs/guides" in it.dirs


def test_missing_patch_keeps_github_line_counts():
    fc = files_from_patches([{"filename": "big.py", "status": "modified", "additions": 40, "deletions": 2, "changes": 42}])[0]
    assert fc.changed == 42 and not fc.binary


def test_mentioning_a_module_in_text_is_not_wiring():
    iss = Issue.from_text("Fix tokenize crash", "`src/tokenizer.py` crashes on empty input")
    d = (
        "diff --git a/src/tokenizer.py b/src/tokenizer.py\n@@ -1,1 +1,2 @@\n x = 1\n+y = 2\n"
        "diff --git a/src/billing.py b/src/billing.py\n@@ -1,1 +1,2 @@\n a = 1\n+log('tokenizer ready')\n"
        "diff --git a/src/app.py b/src/app.py\n@@ -1,1 +1,2 @@\n a = 1\n+from src.tokenizer import tokenize\n"
    )
    flagged = {p.path for p in check(iss, parse_diff(d)).flagged}
    assert "src/billing.py" in flagged and "src/app.py" not in flagged


def test_issue_naming_a_file_flags_unrelated_only_changes():
    iss = Issue.from_text("Bug", "Crash in `src/login.py` on empty password")
    d = "diff --git a/src/billing.py b/src/billing.py\n@@ -1,1 +1,2 @@\n a = 1\n+b = 2\n"
    rep = check(iss, parse_diff(d))
    assert rep.anchored and [p.path for p in rep.flagged] == ["src/billing.py"]
