export const REPO = "https://github.com/ReviewDebtZero/rd0-fence";
export const PIP_INSTALL = "pip install rd0-fence";
export const AIDEV = "https://huggingface.co/datasets/hao-li/AIDev";
export const PAICHECKER = "https://github.com/manyiResearch/PAIChecker";
export const DEMO_PR = `${REPO}/pull/5`;
export const SIBLINGS = [
  { name: "Jinx", what: "duplicate-PR warnings", href: "https://github.com/ReviewDebtZero/rd0-jinx" },
  { name: "Trellis", what: "agent rules into checks", href: "https://github.com/ReviewDebtZero/rd0-trellis" },
];
export const LINKS = {
  benchmark: `${REPO}/tree/main/research/experiments/benchmark`,
  prevalence: `${REPO}/blob/main/research/experiments/benchmark/results/prevalence.md`,
  paichecker: `${REPO}/blob/main/research/experiments/benchmark/results/paichecker.md`,
  goldSheet: `${REPO}/tree/main/research/experiments/label_audit`,
  design: `${REPO}/blob/main/research/docs/experiment_design.md`,
  survey: `${REPO}/blob/main/research/docs/dataset_survey.md`,
  guide: `${REPO}/blob/main/docs/USERS_GUIDE.md`,
};

export const ACTION_YAML = `name: fence
on:
  pull_request_target:
    types: [opened, reopened, synchronize, edited]
permissions:
  contents: read
  pull-requests: write
  issues: write
jobs:
  fence:
    runs-on: ubuntu-latest
    steps:
      - uses: ReviewDebtZero/rd0-fence@main
        with:
          min-lines: "1"   # comment only above this many out-of-scope lines`;
