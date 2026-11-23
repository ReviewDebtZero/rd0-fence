# rd0-fence

Fence flags the parts of a coding-agent pull request that go beyond what its linked issue asked for, with a
reason for each part. Pure Python standard library, CPU only, no LLM and no API key.

```bash
pip install rd0-fence
fence check --issue issue.md --diff pr.diff            # local diff vs issue (Markdown or JSON)
fence github owner/repo#123                            # a GitHub PR vs the issue it closes
fence check --issue issue.json --diff pr.diff --format json --fail-over 0.3
```

```python
from rd0_fence import Issue, check, parse_diff

rep = check(Issue.from_text(title, body), parse_diff(diff_text))
print(rep.out_fraction, [(p.path, p.reason) for p in rep.flagged])
```

Part of rd0 (review debt, to zero): https://github.com/ReviewDebtZero/rd0-fence
