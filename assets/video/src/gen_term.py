import json
from pathlib import Path

pip = [ln for ln in Path("pip.txt").read_text().splitlines() if ln]
chk = Path("check.txt").read_text().rstrip("\n").splitlines()
issue = Path("issue.txt").read_text().rstrip("\n").splitlines()
cmd1 = "pip install ./packages/rd0-fence"
cmd0 = "cat examples/issue.md"
cmd2 = "fence check --issue examples/issue.md --diff examples/pr.diff"
steps = [["cmd", cmd1]] + [["out", ln, "#94a3b8"] for ln in pip] + [["gap", 600], ["cmd", cmd0]]
steps += [["out", ln, "#cbd5e1"] for ln in issue] + [["gap", 700], ["cmd", cmd2]]
for ln in chk:
    c = "#e2e8f0"
    if "[high]" in ln:
        c = "#fca5a5"
    elif "[low]" in ln:
        c = "#fde68a"
    steps.append(["out", ln, c])
page = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="scenes/base.css"><style>
.hd{position:absolute;left:120px;top:70px;font-size:46px;font-weight:800}.hd2{position:absolute;left:120px;top:135px;font-size:27px;color:#cbd5e1}
.win{position:absolute;left:120px;right:120px;top:200px;bottom:70px;background:#0b1220;border:2px solid #334155;border-radius:20px;box-shadow:0 30px 70px rgba(0,0,0,.55);overflow:hidden}
.bar{height:52px;background:#111827;border-bottom:1px solid #1f2937;display:flex;align-items:center;gap:12px;padding-left:22px}.bar i{width:16px;height:16px;border-radius:50%}
.bar span{margin-left:20px;color:#64748b;font-size:20px}
#t{padding:24px 30px;font-size:19px;line-height:1.55;white-space:pre-wrap}
.p{color:#60a5fa}.cur{display:inline-block;width:13px;height:28px;background:#e2e8f0;vertical-align:-5px;animation:bl 1s steps(1) infinite}@keyframes bl{50%{opacity:0}}
</style></head><body><div class="bg"></div><div class="dots"></div>
<div class="hd a" style="animation:up .6s .1s forwards">Working demo: <span class="grad">install, then check a PR against its issue</span></div>
<div class="hd2 a" style="animation:up .6s .3s forwards">Real output &middot; the example issue and PR diff bundled in packages/rd0-fence/examples</div>
<div class="win a" style="animation:pop .6s .4s forwards"><div class="bar"><i style="background:#ef4444"></i><i style="background:#f59e0b"></i><i style="background:#22c55e"></i><span class="mono">~/demo &mdash; bash</span></div><div id="t" class="mono"></div></div>
<script>
const S=__STEPS__;const t=document.getElementById('t');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{await sleep(1100);for(const s of S){if(s[0]==='gap'){await sleep(s[1]);continue}
 if(s[0]==='cmd'){const line=document.createElement('div');line.innerHTML='<span class="p">$ </span><span class="c"></span><span class="cur"></span>';t.appendChild(line);const c=line.querySelector('.c');
  for(const ch of s[1]){c.textContent+=ch;await sleep(28)}await sleep(350);line.querySelector('.cur').remove();await sleep(250)}
 else{const d=document.createElement('div');d.style.color=s[2];d.textContent=s[1]||' ';t.appendChild(d);await sleep(s[1].includes('[high]')?600:150)}}
 const line=document.createElement('div');line.innerHTML='<span class="p">$ </span><span class="cur"></span>';t.appendChild(line)})();
</script></body></html>"""
Path("term.html").write_text(page.replace("__STEPS__", json.dumps(steps)))
print(len(steps), "steps")
