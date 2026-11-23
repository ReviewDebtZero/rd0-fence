# Fence user guide

## What it checks
Given an issue (title and body) and a PR diff, Fence labels each changed file, and each formatting-only hunk inside
an in-scope file, as in or out of the issue's scope. Each out-of-scope part gets a reason and a severity:
`high` for unrelated code, CI and dependency changes; `low` for docs, unrelated tests and formatting.

**Scope reach** = changed lines in out-of-scope parts / all changed lines (generated and vendored files are not
counted).

## CLI
```
fence check --diff FILE (--issue FILE | --title T --body B) [--format text|json|markdown] [--fail-over X]
fence github OWNER/REPO#N [--issue-number N] [--format ...] [--fail-over X]
```
- `--diff`: a unified diff (`git diff`, `gh pr diff`), `-` for stdin, or JSON `{"files": [{"filename", "patch",
  "status"}]}` as returned by the GitHub API.
- `--issue`: JSON `{"title", "body", "number"}` or Markdown whose first line is the title.
- `--fail-over X`: exit 1 when scope reach is above X (for CI gates; off by default).
- `fence github` reads `GITHUB_TOKEN` or `GH_TOKEN` if set. The linked issues come from closing keywords
  (`Fixes #12`, `Closes owner/repo#3`) or issue URLs in the PR body.

## Action inputs
| Input | Default | Meaning |
|---|---|---|
| `github-token` | `${{ github.token }}` | reads the PR and issue, writes one comment |
| `issue` | empty | issue number to compare against; empty = the issues the PR closes |
| `min-lines` | `1` | comment only when at least this many changed lines are out of scope |

The Action skips PRs that link no issue. It updates its own comment on each push (marker
`<!-- rd0_fence:v1 -->`) and edits it to "no out-of-scope parts now" when a later push fixes things.

## Limits
- It compares against the issue text only. Scope agreed in comments or a PR discussion is not seen.
- Vague issues ("it is slow") give no anchors; Fence then reports scope as unknown and judges only CI,
  dependency and formatting parts.
- Matching is lexical (paths, names, terms). Precision on a labelled gold set is the next milestone.
