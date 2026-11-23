import data from "@/data/fence.json";
import { ACTION_YAML, AIDEV, DEMO_PR, LINKS, PAICHECKER, PIP_INSTALL, REPO } from "@/data/site";
import { CopyLine } from "./CopyLine";
import { Frame, Heading, Pill, Section } from "./ui";

const fmt = (n: number) => n.toLocaleString("en-US");
const ci = (c: number[]) => `[${c[0]}, ${c[1]}]`;

const CLI_RUN = `$ fence check --issue examples/issue.md --diff examples/pr.diff
fence: 4 part(s) outside the issue's scope, 13/22 changed lines (59%)
  [low] utils/text.py @@ +23 def truncate(value, n): (+/-4): formatting-only edit (same tokens, new whitespace)
  [high] utils/dates.py (+/-6): edits a code file (changes \`parse\`) that no path, name or term in the issue points to
  [high] .github/workflows/ci.yml (+/-2): changes CI or workflow config; the issue never mentions CI
  [high] requirements.txt (+/-1): changes dependencies or package metadata; the issue does not ask for that`;

export function Hero() {
  return (
    <section id="top" className="mx-auto w-full max-w-6xl px-5 pb-16 pt-16 sm:pt-24">
      <div className="flex flex-wrap gap-2">
        <Pill tone="accent">GitHub Action + CLI</Pill>
        <Pill>CPU only</Pill>
        <Pill>no LLM, no API key</Pill>
        <Pill>MIT</Pill>
      </div>
      <h1 className="mt-6 max-w-4xl text-balance text-4xl font-bold leading-[1.08] tracking-tight sm:text-6xl">
        Did the agent do <span className="text-accent">more than it was asked?</span>
      </h1>
      <p className="mt-6 max-w-2xl text-[17px] leading-relaxed text-fg-dim">
        Fence compares a pull request with the issue it closes. It comments on each changed part that
        no path, name or term in the issue points to — an unrelated file, a CI tweak, a new
        dependency, a formatting sweep — and says why, so the reviewer does not have to diff the issue
        against the PR by hand.
      </p>
      <div className="mt-8 flex max-w-xl flex-col gap-3">
        <CopyLine command={PIP_INSTALL} />
      </div>
      <div className="mt-6 flex flex-wrap gap-4 font-mono text-[13px]">
        <a href="#demo" className="text-accent hover:underline">
          see it on a real PR →
        </a>
        <a href={REPO} className="text-fg-dim hover:text-fg">
          GitHub
        </a>
      </div>
    </section>
  );
}

export function Problem() {
  return (
    <Section index="00" label="why this exists">
      <Heading lead="Helpful extras" accent="still cost a review." />
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-fg-dim">
        Coding agents often fix the issue and then keep going: they bump a dependency, touch CI, or
        tidy a file nobody asked about. Each extra is one more thing the reviewer has to read, judge
        and maybe revert. Today the check is manual: open the issue, open the diff, compare.
      </p>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-fg-dim">
        Fence does that first pass. It is a hint for the reviewer, not a verdict: a flagged part may
        well be needed, and the comment asks the author to say why.
      </p>
    </Section>
  );
}

export function Demo() {
  return (
    <Section id="demo" index="01" label="see it work">
      <Heading lead="One issue, one PR," accent="one comment." />
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-fg-dim">
        Both runs below are real. On the left, the CLI on the bundled example. On the right, the
        Fence Action commenting on{" "}
        <a href={DEMO_PR} className="text-accent hover:underline">
          a demo PR in this repo
        </a>{" "}
        that does what its issue asked and three things it did not.
      </p>
      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        <Frame title="terminal · fence check">
          <pre
            tabIndex={0}
            role="region"
            aria-label="Fence CLI output"
            className="overflow-x-auto px-3 py-3 font-mono text-[12px] leading-relaxed text-fg-dim"
          >
            {CLI_RUN}
          </pre>
        </Frame>
        <Frame title="github · Fence Action comment">
          <a href={DEMO_PR}>
            {/* eslint-disable-next-line @next/next/no-img-element -- static export, no image optimizer */}
            <img
              src="/action_comment.png"
              alt="A Fence comment on a pull request listing three out-of-scope parts with a reason for each"
              className="w-full"
            />
          </a>
        </Frame>
      </div>
      <p className="mt-6 font-mono text-[12.5px] text-fg-faint">
        Watch the whole run:{" "}
        <a href="/fence_demo.mp4" className="text-accent hover:underline">
          fence_demo.mp4
        </a>
      </p>
    </Section>
  );
}

export function Benchmark() {
  const top = data.agents[0];
  return (
    <Section id="benchmark" index="02" label="measured on real agent PRs">
      <Heading lead="What Fence flags in the wild," accent="and where it falls short." />
      <p className="mt-4 max-w-3xl text-[15px] leading-relaxed text-fg-dim">
        We ran Fence on {fmt(data.corpus_prs)} PRs from{" "}
        <a href={AIDEV} className="text-accent hover:underline">
          AIDev
        </a>{" "}
        that close an issue and come with their diffs. These are <b className="text-fg">Fence&rsquo;s
        own flags</b>, not human-checked findings: nobody has labelled the gold sheet yet, so there is
        no precision number. Brackets are 95% confidence intervals.
      </p>
      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {[
          { v: `${data.reaches.pct}%`, k: `of anchored PRs have at least one flagged part ${ci(data.reaches.ci95)}` },
          { v: `${data.reaches_high.pct}%`, k: `have a high-severity flag ${ci(data.reaches_high.ci95)}` },
          { v: `${data.unresolvable.pct}%`, k: `name nothing concrete, so Fence marks scope unresolvable (${fmt(data.unresolvable.k)} PRs)` },
        ].map((s) => (
          <div key={s.k} className="border border-line bg-panel p-4">
            <p className="font-mono text-4xl font-bold tracking-tight text-note">{s.v}</p>
            <p className="mt-2 text-[13px] leading-relaxed text-fg-dim">{s.k}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        <Frame title="share of PRs Fence flags, by agent">
          <table className="w-full font-mono text-[12.5px]">
            <tbody className="text-fg-dim">
              {data.agents.map((a) => (
                <tr key={a.name} className="border-b border-line last:border-0">
                  <td className="px-3 py-2 text-fg">{a.name}</td>
                  <td className="px-3 py-2 text-right">{fmt(a.prs)} PRs</td>
                  <td className="px-3 py-2 text-right text-note">{a.pct}%</td>
                  <td className="px-3 py-2 text-right text-fg-faint">{ci(a.ci95)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="border-t border-line px-3 py-2 text-[12.5px] leading-relaxed text-fg-faint">
            {top.name}&rsquo;s PRs touch more files than the others&rsquo;, and Fence flags more on
            bigger PRs, so do not read this as a ranking of agents.
          </p>
        </Frame>
        <Frame title={`AUROC vs PAIChecker scope-creep labels (${fmt(data.paichecker.instances)} patches)`}>
          <table className="w-full font-mono text-[12.5px]">
            <tbody className="text-fg-dim">
              {data.paichecker.auroc.map((r) => (
                <tr key={r.name} className="border-b border-line last:border-0">
                  <td className={`px-3 py-2 ${r.ours ? "text-accent" : "text-fg"}`}>{r.name}</td>
                  <td className="px-3 py-2 text-right">{r.auc.toFixed(3)}</td>
                  <td className="px-3 py-2 text-right text-fg-faint">{ci(r.ci95)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="border-t border-line px-3 py-2 text-[12.5px] leading-relaxed text-fg-faint">
            On{" "}
            <a href={PAICHECKER} className="hover:text-accent">
              PAIChecker
            </a>
            &rsquo;s human labels, plain PR size ranks scope-creep patches better than Fence does.
            Those labels are per PR and the patches are human-written, so they test a different
            thing than Fence&rsquo;s per-file flags — but the gap is real.
          </p>
        </Frame>
      </div>
      {/* eslint-disable-next-line @next/next/no-img-element -- static export, no image optimizer */}
      <img
        src="/fig_benchmark.png"
        alt="Left: share of AIDev PRs Fence flags, by agent. Right: AUROC against PAIChecker labels, where PR size is highest."
        className="mt-8 w-full border border-line bg-white"
      />
      <p className="mt-4 font-mono text-[12.5px] text-fg-faint">
        Full tables:{" "}
        <a href={LINKS.prevalence} className="text-accent hover:underline">
          prevalence.md
        </a>{" "}
        ·{" "}
        <a href={LINKS.paichecker} className="text-accent hover:underline">
          paichecker.md
        </a>
      </p>
    </Section>
  );
}

const STEPS = [
  ["read the issue", "Collect file paths, code names and terms from the issue title and body."],
  ["split the diff", "Label each changed file, and each formatting-only hunk inside an in-scope file."],
  ["anchor each part", "A file is in scope if a path, name or term from the issue points to it. A test is in scope if it covers an in-scope file or the issue asks for tests."],
  ["explain the rest", "Everything else gets a category (unrelated code, CI, dependencies, docs, tests, formatting), a severity and a one-line reason."],
];

export function HowItWorks() {
  return (
    <Section index="03" label="how it works">
      <Heading lead="Path matching and a light parse." accent="No model in the loop." />
      <ol className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map(([k, v], i) => (
          <li key={k} className="border border-line bg-panel p-4">
            <p className="font-mono text-[12.5px] text-accent">{`0${i + 1} · ${k}`}</p>
            <p className="mt-2 text-[13px] leading-relaxed text-fg-dim">{v}</p>
          </li>
        ))}
      </ol>
      <p className="mt-4 max-w-3xl text-[13px] leading-relaxed text-fg-faint">
        If the issue names nothing concrete, Fence marks the scope unresolvable and judges only CI, dependency and formatting parts.
        Scope reach is the share of changed lines in out-of-scope parts; generated and vendored files are not counted.
      </p>
    </Section>
  );
}

export function Install() {
  return (
    <Section id="install" index="04" label="add it to your repo">
      <Heading lead="One workflow file." accent="One comment per PR." />
      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        <div className="min-w-0">
          <p className="font-mono text-[12.5px] text-fg-dim">1 · as a GitHub Action</p>
          <p className="mt-2 text-[13px] leading-relaxed text-fg-dim">
            Drop this in <code className="text-fg">.github/workflows/fence.yml</code>. Fence compares
            the PR with the issues its body closes (<code className="text-fg">Fixes #N</code>) and
            keeps a single comment up to date as the PR changes.
          </p>
          <Frame className="mt-3" title=".github/workflows/fence.yml">
            <pre
              tabIndex={0}
              role="region"
              aria-label="GitHub Action workflow"
              className="overflow-x-auto px-3 py-3 font-mono text-[12.5px] leading-relaxed text-fg-dim"
            >
              {ACTION_YAML}
            </pre>
          </Frame>
          <p className="mt-3 text-[13px] leading-relaxed text-fg-faint">
            <code className="text-fg-dim">pull_request_target</code> is safe here: Fence reads the PR
            and issue through the GitHub API and never checks out or runs the PR&rsquo;s code. It only
            looks up issues in the PR&rsquo;s own repository.
          </p>
        </div>
        <div className="min-w-0">
          <p className="font-mono text-[12.5px] text-fg-dim">2 · or from the command line</p>
          <div className="mt-3 space-y-2">
            <CopyLine command={PIP_INSTALL} />
            <CopyLine command="fence check --issue issue.md --diff pr.diff" />
            <CopyLine command="fence github owner/repo#123" />
          </div>
          <div className="mt-4 border border-line">
            <div className="border-b border-line bg-panel-2 px-3 py-1.5 font-mono text-[12.5px] text-fg-faint">
              flags
            </div>
            <table className="w-full font-mono text-[12.5px]">
              <tbody className="text-fg-dim">
                {[
                  ["--format json|markdown", "machine-readable or comment-ready output"],
                  ["--fail-over X", "exit 1 if the out-of-scope share is above X"],
                  ["--issue-number N", "compare against issue N instead of the closed ones"],
                ].map(([f, d]) => (
                  <tr key={f} className="border-b border-line last:border-0">
                    <td className="px-3 py-2 text-fg">{f}</td>
                    <td className="px-3 py-2">{d}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Section>
  );
}

export function Limits() {
  return (
    <Section index="05" label="limits">
      <Heading lead="What Fence does not know" accent="yet." />
      <ul className="mt-6 max-w-3xl list-disc space-y-2 pl-5 text-[14px] leading-relaxed text-fg-dim">
        <li>Its precision is not measured. The prevalence numbers above are its own flags.</li>
        <li>On PAIChecker&rsquo;s labels, PR size alone ranks scope creep better than Fence.</li>
        <li>
          It only knows what the issue says. A change the issue implies but never names (a needed
          refactor, a renamed caller) gets flagged.
        </li>
        <li>Matching is lexical (paths, names, terms). Scope agreed in comments or PR discussion is not seen.</li>
      </ul>
    </Section>
  );
}

export function Research() {
  return (
    <Section id="research" index="06" label="research">
      <Heading lead="Open data," accent="open labels." />
      <p className="mt-4 max-w-3xl text-[15px] leading-relaxed text-fg-dim">
        The benchmark, baselines and a {data.gold.prs}-PR gold sheet ({data.gold.per_agent} per agent,{" "}
        {fmt(data.gold.files)} files) with a labeling app are in the repo. Human labels from the gold
        sheet will give Fence its first precision number.
      </p>
      <div className="mt-6 flex flex-wrap gap-4 font-mono text-[13px]">
        <a href={LINKS.benchmark} className="text-accent hover:underline">
          benchmark →
        </a>
        <a href={LINKS.goldSheet} className="text-accent hover:underline">
          gold sheet + labeling app →
        </a>
        <a href={LINKS.survey} className="text-accent hover:underline">
          dataset survey →
        </a>
      </div>
    </Section>
  );
}
