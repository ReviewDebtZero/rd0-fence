import { AIDEV, LINKS, PIP_INSTALL, REPO, SIBLINGS } from "@/data/site";
import { CopyLine } from "./CopyLine";

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto w-full max-w-6xl px-5 py-14">
        <div className="grid gap-10 lg:grid-cols-[1.4fr_1fr_1fr]">
          <div className="min-w-0">
            <p className="font-mono text-[17px] font-bold tracking-tight">
              <span className="text-accent">rd0</span>
              <span className="text-fg-faint">/</span>fence
            </p>
            <p className="mt-3 max-w-sm text-[13px] leading-relaxed text-fg-dim">
              <span className="text-fg">rd0</span> is a toolkit for review debt — the reviewer time a
              team owes but has not paid. <span className="text-fg">Fence</span> is its third tool: it
              points at the parts of a pull request its issue never asked for. Free, MIT licensed, and
              it runs on the CI machine&rsquo;s CPU.
            </p>
            <div className="mt-4 max-w-sm">
              <CopyLine command={PIP_INSTALL} />
            </div>
          </div>

          <div>
            <p className="font-mono text-[12.5px] text-fg-faint">project</p>
            <ul className="mt-3 space-y-2 font-mono text-[13px] text-fg-dim">
              <li>
                <a href={REPO} className="hover:text-accent">
                  GitHub
                </a>
              </li>
              <li>
                <a href={LINKS.guide} className="hover:text-accent">
                  User guide
                </a>
              </li>
              <li>
                <a href={`${REPO}/blob/main/LICENSE`} className="hover:text-accent">
                  MIT license
                </a>
              </li>
              {SIBLINGS.map((s) => (
                <li key={s.name}>
                  <a href={s.href} className="hover:text-accent">
                    {s.name} <span className="text-fg-faint">· {s.what}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="font-mono text-[12.5px] text-fg-faint">research</p>
            <ul className="mt-3 space-y-2 font-mono text-[13px] text-fg-dim">
              <li>
                <a href={LINKS.benchmark} className="hover:text-accent">
                  Benchmark
                </a>
              </li>
              <li>
                <a href={LINKS.design} className="hover:text-accent">
                  Experiment design
                </a>
              </li>
              <li>
                <a href={LINKS.survey} className="hover:text-accent">
                  Dataset survey
                </a>
              </li>
              <li>
                <a href={AIDEV} className="hover:text-accent">
                  AIDev dataset
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-wrap items-baseline justify-between gap-3 border-t border-line pt-5 font-mono text-[12.5px] text-fg-faint">
          <p>Harshul Jain</p>
          <p>
            Benchmark derived from{" "}
            <a href={AIDEV} className="hover:text-accent">
              AIDev
            </a>{" "}
            (CC BY 4.0)
          </p>
        </div>
      </div>
    </footer>
  );
}
