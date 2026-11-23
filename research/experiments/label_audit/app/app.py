"""Fence human labeling app: which files in this agent PR go beyond what the linked issue asked for?

Each annotator picks a name; answers are appended to answers/<name>.jsonl, one JSON object per line
{id, unresolvable, out_of_scope, cant_tell, note}. Unchecked files count as in scope. Re-open the app to resume;
the last save for a PR wins. Fence's verdicts (human/key_do_not_open.csv) are never loaded or shown.
"""

import html
import json
import pathlib

import gradio as gr

HERE = pathlib.Path(__file__).resolve().parent
TASKS = [json.loads(line) for line in (HERE / "tasks.jsonl").read_text().splitlines()]
ANSWERS = HERE / "answers"
ANSWERS.mkdir(exist_ok=True)

GUIDE = """For each PR, read the linked issue, then the changed files, and judge each file as a reviewer would:

- **Out of scope**: the file's change is not needed for what the issue asks, e.g. an unrequested refactor,
  an unrelated fix, a CI or dependency change the issue never mentions, or formatting churn in an untouched area.
- **Can't tell**: you cannot judge this file even after reading the patch (truncated patch, generated blob, ...).
- Leave a file unchecked if it is **in scope**: it implements, tests, documents or wires up what the issue asks.
- Tick **scope unresolvable** when the issue is too vague to say what is in scope at all (e.g. "improve the app").
  File checkboxes are then ignored.

Judge the issue against the diff, not the PR description. Open the links when a patch is truncated.
"""

UNRESOLVABLE = "Scope unresolvable: the issue is too vague to say what is in scope"


def answers_path(name):
    safe = "".join(c for c in name if c.isalnum() or c in "-_").lower() or "anon"
    return ANSWERS / f"{safe}.jsonl"


def load_answers(name):
    path = answers_path(name)
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["id"]] = row
    return out


def save_answer(name, task_id, unresolvable, out_of_scope, cant_tell, note):
    row = {
        "id": task_id,
        "unresolvable": bool(unresolvable),
        "out_of_scope": list(out_of_scope or []),
        "cant_tell": list(cant_tell or []),
        "note": note,
    }
    with answers_path(name).open("a") as f:
        f.write(json.dumps(row) + "\n")


def esc(text):
    return html.escape(text or "", quote=False)


def progress(name):
    return f"**{len(load_answers(name))} / {len(TASKS)}** PRs labeled"


def files_md(task):
    out = []
    for f in task["files"]:
        out.append(
            f"#### `{esc(f['path'])}` ({esc(f['status'])}, +{f['additions']} / -{f['deletions']})\n\n"
            f"<pre>{html.escape(f['patch'] or '(no patch text)')}</pre>"
        )
    return "\n\n".join(out)


def render_task(name, idx):
    if not name:
        return [gr.update()] * 10
    done = load_answers(name)
    task = TASKS[idx]
    prev = done.get(task["id"], {})
    paths = [f["path"] for f in task["files"]]
    header = f"### PR {idx + 1} of {len(TASKS)} · id {task['id']} · `{esc(task['repo'])}`" + (
        "  ·  already labeled" if prev else ""
    )
    links = f"[PR]({task['pr_url']})  ·  " + "  ·  ".join(f"[Issue]({u})" for u in task["issue_urls"] if u)
    issue = f"**PR title:** {esc(task['pr_title'])}\n\n" + esc(task["issue"])
    return [
        header,
        links,
        issue,
        files_md(task),
        gr.update(value=bool(prev.get("unresolvable", False))),
        gr.update(choices=paths, value=[p for p in prev.get("out_of_scope", []) if p in paths]),
        gr.update(choices=paths, value=[p for p in prev.get("cant_tell", []) if p in paths]),
        prev.get("note", ""),
        progress(name),
        idx,
    ]


def first_unlabeled(name):
    done = load_answers(name)
    for i, t in enumerate(TASKS):
        if t["id"] not in done:
            return i
    return 0


def start(name):
    return render_task(name, first_unlabeled(name))


def step(name, idx, delta):
    return render_task(name, max(0, min(len(TASKS) - 1, idx + delta)))


def jump(name, target):
    return render_task(name, max(0, min(len(TASKS) - 1, int(target or 1) - 1)))


def submit(name, idx, unresolvable, out_of_scope, cant_tell, note):
    if not name:
        gr.Warning("Enter your annotator name first.")
        return render_task(name, idx)
    both = set(out_of_scope or []) & set(cant_tell or [])
    if both and not unresolvable:
        gr.Warning("A file cannot be both out of scope and can't tell: " + ", ".join(sorted(both)))
        return render_task(name, idx)
    save_answer(name, TASKS[idx]["id"], unresolvable, out_of_scope, cant_tell, note or "")
    gr.Info(f"Saved PR {idx + 1}.")
    return render_task(name, min(len(TASKS) - 1, idx + 1))


def export(name):
    path = answers_path(name)
    return str(path) if path.exists() else None


with gr.Blocks(title="Fence scope labeling") as demo:
    gr.Markdown(
        f"# Fence: did the agent do more than the issue asked?\nYou will see {len(TASKS)} agent PRs with their linked "
        "issues.\n\n" + GUIDE
    )
    name = gr.Textbox(label="Your annotator name (e.g. A or B)", placeholder="A", max_lines=1)
    start_btn = gr.Button("Start / resume", variant="primary")
    gr.Markdown("---")
    progress_md = gr.Markdown()
    header = gr.Markdown()
    links = gr.Markdown()
    with gr.Accordion("Linked issue", open=True):
        issue = gr.Markdown()
    with gr.Accordion("Changed files", open=True):
        diff = gr.Markdown()
    unresolvable = gr.Checkbox(label=UNRESOLVABLE)
    out_of_scope = gr.CheckboxGroup([], label="Files that go beyond the issue (out of scope)")
    cant_tell = gr.CheckboxGroup([], label="Files you can't judge")
    note = gr.Textbox(label="Note (optional)", max_lines=2)
    with gr.Row():
        prev_btn = gr.Button("Previous")
        submit_btn = gr.Button("Save & next", variant="primary")
        next_btn = gr.Button("Skip")
    with gr.Row():
        jump_num = gr.Number(label="Jump to PR #", precision=0, minimum=1)
        export_btn = gr.Button("Get my answers file")
        export_file = gr.File(interactive=False)
    idx_state = gr.State(0)

    outs = [header, links, issue, diff, unresolvable, out_of_scope, cant_tell, note, progress_md, idx_state]
    start_btn.click(start, name, outs)
    name.submit(start, name, outs)
    prev_btn.click(step, [name, idx_state, gr.State(-1)], outs)
    next_btn.click(step, [name, idx_state, gr.State(1)], outs)
    jump_num.submit(jump, [name, jump_num], outs)
    submit_btn.click(submit, [name, idx_state, unresolvable, out_of_scope, cant_tell, note], outs)
    export_btn.click(export, name, export_file)

if __name__ == "__main__":
    demo.launch()
