# Demo video

`web/public/fence_demo.mp4` (1920×1080, 30 fps, about 72 s, captions, no audio) is served at
<https://rd0-fence.netlify.app/fence_demo.mp4>. `assets/demo_preview.gif` is its first 12 seconds, used in the README.

Every scene is a real recording or animated HTML, with no mock-ups:

| Scene | Source | What it shows |
|---|---|---|
| intro | `scenes/intro.html` | Animated: an issue and the files its PR changed, in scope and not |
| term | `gen_term.py` → `term.html` | Typed replay of real output: `pip.txt` (`pip install ./packages/rd0-fence`, trimmed to four lines), `issue.txt` (the example issue) and `check.txt` (`fence check` on `packages/rd0-fence/examples`) |
| github | `rec_site.py` | Live capture of the comment the Fence Action posted on [PR #5](https://github.com/ReviewDebtZero/rd0-fence/pull/5) |
| site | `rec_site.py` | Live capture of the website: demo, benchmark, install, theme switch |
| chart | `scenes/chart.html` | Animated AUROC comparison on PAIChecker's labels, numbers from `research/experiments/benchmark/results/paichecker.json` |
| outro | `scenes/outro.html` | End card |

## Rebuild

Needs Python with `playwright` and `Pillow`, Chrome, and `ffmpeg`. Set the Chrome path in `rec_one.py` and `rec_site.py`.

```bash
cd assets/video/src
python3 gen_term.py                       # writes term.html from pip.txt + issue.txt + check.txt
python3 rec_one.py intro scenes/intro.html 11.5
python3 rec_one.py term  term.html 15
python3 rec_one.py chart scenes/chart.html 8
python3 rec_one.py outro scenes/outro.html 5
(cd ../../../web && npm run build && python3 -m http.server 3090 --directory out) &   # site on :3090
python3 rec_site.py                       # site.mp4 + github.mp4
python3 compose.py                        # crossfades → fence_demo.mp4
cp fence_demo.mp4 ../../../web/public/
ffmpeg -t 12 -i fence_demo.mp4 -vf "fps=10,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5" ../../demo_preview.gif
```

The intermediate `*.mp4` and `term.html` files are build output and are not committed.
