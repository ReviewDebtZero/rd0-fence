import asyncio
import time
from pathlib import Path

from playwright.async_api import async_playwright
from rec import record

HERE = Path(__file__).resolve().parent
SMOOTH = """async ([sel, off, ms]) => { document.documentElement.style.scrollBehavior = 'auto'; const el = sel === 'top' ? null : (sel.startsWith('#') ? document.querySelector(sel) : [...document.querySelectorAll('h2,h1,div')].find(e => e.textContent.trim().startsWith(sel)));
  const y1 = el ? el.getBoundingClientRect().top + scrollY - off : 0; const y0 = scrollY; const t0 = performance.now();
  await new Promise(r => { (function f(){ const p = Math.min(1, (performance.now() - t0) / ms); const e = p < .5 ? 4*p*p*p : 1 - Math.pow(-2*p + 2, 3) / 2; scrollTo(0, y0 + (y1 - y0) * e); p < 1 ? requestAnimationFrame(f) : r(); })(); }); }"""


def mk(caps):
    t0 = [None]

    def mark(txt):
        caps.append([time.time(), txt])

    return t0, mark


async def site(pg, caps):
    t0, mark = caps
    t0[0] = time.time()
    mark("Fence compares a PR with the issue it closes and flags each part the issue never asked for.")
    await pg.wait_for_timeout(3500)
    mark("Both demo runs are real: the CLI on the bundled example, and the Action on PR #5 in this repo.")
    await pg.evaluate(SMOOTH, ["#demo", 64, 1400])
    await pg.wait_for_timeout(3800)
    mark("Measured on 54,058 AIDev agent PRs. These are Fence's own flags; precision is not measured yet.")
    await pg.evaluate(SMOOTH, ["#benchmark", 64, 1400])
    await pg.wait_for_timeout(3600)
    mark("And the honest part: on PAIChecker's labels, plain PR size ranks scope creep better than Fence.")
    await pg.evaluate(SMOOTH, ["AUROC vs PAIChecker", 120, 1200])
    await pg.wait_for_timeout(3600)
    mark("Light or dark. Install: one workflow file, CPU only, no API key.")
    await pg.evaluate(SMOOTH, ["#install", 64, 1400])
    await pg.wait_for_timeout(600)
    await pg.get_by_label("Switch to the light theme").first.click()
    await pg.wait_for_timeout(2000)
    await pg.get_by_label("Switch to the dark theme").first.click()
    await pg.wait_for_timeout(1800)


async def gh(pg, caps):
    t0, mark = caps
    t0[0] = time.time()
    mark("Working demo on GitHub: the comment the Fence Action really posted on PR #5.")
    await pg.wait_for_timeout(2500)
    print(
        "gh scroll:",
        await pg.evaluate("""async () => { const all = [...document.querySelectorAll('p, li, strong, div')].filter(e => e.textContent.includes('go beyond what issue')); const el = all[all.length - 1]; if (!el) return 'none';
      const y1 = el.getBoundingClientRect().top + scrollY - 160, y0 = scrollY, t0 = performance.now();
      await new Promise(r => { (function f(){ const p = Math.min(1, (performance.now() - t0) / 2200); const e = p < .5 ? 4*p*p*p : 1 - Math.pow(-2*p + 2, 3) / 2; scrollTo(0, y0 + (y1 - y0) * e); p < 1 ? requestAnimationFrame(f) : r(); })(); }); return "ok"; }"""),
    )
    await pg.wait_for_timeout(6500)


def windows(caps, total):
    out = []
    for i, (t, txt) in enumerate(caps):
        out.append((t + 0.2, (caps[i + 1][0] if i + 1 < len(caps) else total) - 0.1, txt))
    return out


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            executable_path="/opt/.devin/google-chrome.sh",
            headless=True,
            args=["--no-sandbox", "--force-color-profile=srgb"],
        )
        for name, url, secs, fn in [
            ("site", "http://localhost:3090/", 23, site),
            ("github", "https://github.com/ReviewDebtZero/rd0-fence/pull/5", 11.5, gh),
        ]:
            caps = []
            t0, mark = mk(caps)
            holder = (t0, mark)
            # captions are filled while recording; record() reads them after the run
            n = await record(
                b,
                url,
                str(HERE / f"{name}.mp4"),
                secs,
                actions=lambda pg, h=holder, f=fn: f(pg, h),
                viewport=(1280, 720) if name == "github" else (1600, 900),
                dsf=1.5 if name == "github" else 1.2,
                captions=caps,
            )
            print(name, "frames", n, [round(c[0], 1) for c in caps])


asyncio.run(main())
