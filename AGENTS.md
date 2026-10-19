# AGENTS.md: LugandaGPT Engineering Instructions

This file is the persistent instruction set for any agent (human or AI)
working in this repository. Read it before doing any work here.

LugandaGPT is an early-stage research project. **No trained LugandaGPT
model currently exists.** Treat every statement about models, data, or
results accordingly.

---

## 1. Working rules

- **Inspect before editing.** Read the relevant files and check `git status`
  before changing anything. Preserve unrelated work; do not overwrite useful
  content without reviewing it first.
- **Explain purpose before implementing.** State what a task is for, what it
  will change, and what it will not change, before doing it.
- **Prefer small, testable changes.** One concern per change where practical.
- **Preserve the approved project structure** (`src/`, `configs/`,
  `tokenizer/`, `data/`, `docs/`, `tests/`, `reports/`, `checkpoints/`)
  unless a documented reason justifies changing it. Record such reasons in
  `docs/DECISIONS.md`.
- **Stop and report** when requirements are ambiguous, when a task exceeds
  the approved scope, or when a decision requires project-director approval.

## 2. Honesty and evidence rules

- **Never invent** test results, benchmark scores, data provenance, or
  training outcomes.
- **Never claim** that a model was trained or evaluated unless it actually was.
- **Clearly separate** measured results, assumptions, and proposals. Label
  each as such.
- Do not present AI-generated judgments about Luganda quality as ground
  truth. Native-speaker evaluation is the reference standard.

## 3. Cost, compute, and API rules

- **Never download large models or datasets without approval.**
- **Never start paid GPU jobs** without explicit project-director approval.
- **Never make API calls that spend money** until the provider, model, task,
  and intended budget are understood and approved.
- Record budget and approval status for every experiment (see
  `docs/EXPERIMENT_LOG.md`).

## 4. Secrets and data-handling rules

- **Never place API keys, passwords, tokens, or credentials** in source code,
  logs, Git commits, documentation, or chat transcripts.
- Do not upload private datasets or model weights to GitHub.
- Follow `data/README.md` governance rules for any dataset touched by the
  project. Publicly accessible text is not automatically licensed for
  training or redistribution.

## 5. Engineering practices

- **Write tests** for important functionality.
- **Record reproducible experiment configurations and results** using the
  template in `docs/EXPERIMENT_LOG.md`.
- **Do not change the model architecture, parameter count, or training
  strategy** without documenting the rationale in `docs/DECISIONS.md` and
  obtaining approval.
- **Do not treat the existence of Pearl Chat or any other competitor** as
  proof of what our model can achieve. Competitor behavior is not evidence
  about our system.
- Use **Python** for ML and data tooling unless a documented reason supports
  another language. Avoid unnecessary dependencies.
- The local development machine has roughly **8 GB RAM and limited free
  disk space**. Local work should focus on code, small samples, tests, and
  evaluation tooling, not large-scale training.

## 6. Roles

- **Project Director** (human owner): product direction, approval of major
  decisions, spending control, authorization of expensive experiments.
- **ChatGPT**: architecture review, research planning, experimental design,
  interpretation of results, critical review.
- **DeepSeek**: primary engineering agent, responsible for implementation,
  debugging, tests, data-processing tools, and training infrastructure.
- **Human Luganda Evaluators**: assessment of naturalness, grammar, meaning,
  cultural context, and usefulness.

## 7. Approval gates

Work must pause for project-director approval before:

- Any dataset acquisition, scraping, or licensing commitment.
- Any paid API usage or paid compute.
- Any training or fine-tuning run beyond trivial smoke tests on tiny samples.
- Any change to architecture, parameter count, or training strategy.
- Any deployment or public release.

## 8. Writing and formatting standards

### Punctuation

- Do not use em dashes (U+2014) in newly written project documentation,
  source-code comments, commit messages, generated reports, or user-facing
  text. ASCII punctuation also avoids encoding problems like the UTF-16
  README this repository started with.
- Rewrite the sentence using commas, periods, colons, parentheses, or
  semicolons where they fit naturally. Do not swap an em dash for another
  mark mechanically.
- Prefer direct, natural, concise language. Avoid unnecessary punctuation
  and elaborate phrasing.
- Review new text for em dashes before finishing a task.

### Prose

- Avoid formulaic AI-generated explanations, repetitive headings, and
  generic filler.
- Keep documentation specific to this project: name the files, rules, and
  decisions that actually apply here.
- Keep headings distinct and useful rather than repeating the same phrasing
  across sections.

### Comments

- Write comments that explain why something exists or why a decision was
  made, not comments that restate the code.
- When the code already says what it does, add no comment.

### Code and clarity

- Follow the formatting conventions of the language and framework in use.
- Do not make code harder to read just to make it look less AI-generated.
- Prefer simple, maintainable implementations over abstract ones.
- Do not reformat unrelated code or rewrite unrelated files for style alone.
- Formatting standards never override technical precision: when a rewrite
  would lose meaning or ambiguity, keep the precise wording.
