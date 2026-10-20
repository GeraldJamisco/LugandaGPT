# Phase 1: Resource Validation, Benchmark Specification, and Baseline Shortlist

**Status:** Working draft for project-director review. This document is
research input, not an approved plan. It does not claim that any model was
run, that any dataset was acquired, or that any Luganda output was reviewed.

This revision replaces the earlier Phase 1 working draft at the same path
and is still a draft. It is not an approval record.

**Scope:** Phase 1 of `docs/ROADMAP.md` (research and baseline). This file
contains the documentation audit, the validation of five named resources, a
proposed benchmark specification, a four-model baseline shortlist, the
Phase 1 readiness checklist, and the exit-criteria mapping.

**Companion specification:** `docs/BENCHMARK-SPECIFICATION.md` (version
0.1-draft). It is also a draft and is not approved. This research document
records evidence and rationale; the companion document is the reviewable
operational benchmark specification.

**Date checked:** 2026-10-20. All primary-source fetches cited below were
performed on this date unless stated otherwise.

**What this review did not do:** no model was downloaded or run; no full
corpus was downloaded; no paid API was called; no prompt was written; no
native-speaker review took place; no training or fine-tuning was started.
Only metadata, documentation, a loading script, licence files, and a 27 KB
model evaluation JSON file were fetched. No model weights and no dataset
rows were downloaded.

---

## 1. How to read this document

Each factual statement carries one of these labels:

- **Verified:** read directly from a fetched primary source during this
  review, with the source named.
- **Source claim:** the publisher states the fact, but it was not
  independently reproduced. Self-reported BLEU, chrF, size, and quality
  claims are normally source claims.
- **Inferred:** a conclusion reasoned from verified facts. It is labelled
  and is not presented as a measurement.
- **Unverified:** could not be confirmed, usually because a card or file is
  gated, or because no primary source was available.
- **Excluded:** checked, and the resource does not provide verified Luganda
  coverage or is unsuitable for the current scope.

Numbers described as **estimate** are arithmetic from file sizes or typical
model behaviour. They are not measured memory use. No estimate in this
document should be quoted as a benchmark result.

The four resource classifications used in Task A are:

- **Verified candidate:** Luganda presence and the stated licence were
  confirmed from primary sources. Conditions and gated access may still
  apply. Classification is not approval.
- **Candidate requiring licensing or provenance review:** Luganda presence
  is credible, but the licence claim, upstream rights, or alignment quality
  is unresolved.
- **Unsuitable for current use:** checked and rejected for this phase, for
  example because Luganda is absent or the domain is out of scope.
- **Insufficient evidence:** Luganda coverage or terms could not be
  established from available sources.

---

## 2. Documentation audit

### 2.1 Documents inspected

- `docs/VISION.md`
- `docs/ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/EXPERIMENT_LOG.md`
- `docs/EVALUATION_PLAN.md`
- `data/README.md`
- `AGENTS.md`
- `README.md`

### 2.2 Settled decisions

These are accepted and are not reopened here:

- **D-001:** Luganda-native model, not a translation app or a wrapper around
  another provider's chatbot API.
- **D-002:** initial scope is text-only.
- **D-003:** DeepSeek is the engineering agent, not the model foundation.
- **D-004:** native-speaker evaluation is required; automated metrics and AI
  judgments are supporting evidence only.
- **D-006:** separation of responsibilities between the project director,
  DeepSeek, ChatGPT, and native Luganda speakers.

### 2.3 Open decision

**D-005** remains open: model architecture, parameter count, and training
strategy are unselected. `docs/ARCHITECTURE.md` also leaves tokenizer,
corpus size, training method, and compute provider undecided.

The model shortlist in section 6 is an evaluation proposal. It does not
select a LugandaGPT architecture and does not reopen D-005.

### 2.4 Existing benchmark design

`docs/EVALUATION_PLAN.md` already defines:

- approximately 50 prompts;
- nine categories: Formal Luganda, Everyday Luganda, Colloquial language,
  Luganda-English code-switching, Instruction following, Multi-turn context,
  Explanation and reasoning, Cultural and linguistic interpretation,
  Factuality and appropriate uncertainty;
- seven scoring dimensions: Semantic correctness, Grammar and naturalness,
  Instruction compliance, Relevance, Context retention, Factual reliability,
  Appropriate register;
- a mandatory native-speaker component under D-004;
- contamination control and reporting rules.

It also states that the concrete scoring scale, weights, exact category
distribution, and benchmark items do not exist yet.

### 2.5 What the existing plan does not specify

The plan is a policy document, not a buildable benchmark specification. It
does not define:

- the benchmark item schema;
- prompt and response language per category;
- when a reference answer is required;
- the ambiguity review procedure;
- the native-speaker review procedure (reviewers, overlap, adjudication);
- scoring anchors and an applicability matrix;
- model identity and inference settings to record;
- reproducibility and cost fields;
- exclusion rules;
- a limitations list;
- an explicit draft status marker.

Section 5 proposes these additions. The nine categories, the seven
dimensions, the approximately 50-prompt size, and the D-004 requirement are
preserved.

### 2.6 Contradictions and stale statements to flag

These are not silently fixed. They need a project-director decision.

1. `docs/ROADMAP.md` lists Phase 1 as "Not started", although Phase 1
   research is being performed now. The status line is stale.
2. `README.md` describes Phase 0 as still in progress with tooling "still to
   come", while the project reporter exists in `src/reporter/`. The status
   text is stale.
3. The Kimera paper and the Kimera repository README disagree about BLEU
   direction. The paper abstract says 21.28 Luganda to English and 17.47
   English to Luganda. The README says 21.28 English to Luganda and 17.47
   Luganda to English. Both are source claims and the direction is
   unresolved.
4. The Hugging Face dataset `cdli/ugandan_luganda_nonstandard_speech_v1.0`
   is tagged `language:lg` but describes Ugandan English speech from
   speakers with speech impairments. The tag and the description conflict.
5. Several community corpora claim permissive licences over scraped news,
   Bible translations, or machine-translated text. Those claims are not
   evidence of upstream permission.
6. The Hugging Face Wikipedia mirror `wikimedia/wikipedia` is tagged
   CC BY-SA 3.0 and GFDL and was last modified on 2024-01-09, while the live
   Luganda Wikipedia declares CC BY-SA 4.0 on 2026-10-20. The mirror is a
   stale snapshot and a different licence version.

---

## 3. Method and limits of the evidence

### 3.1 Sources used

Primary sources were preferred: dataset cards, model cards, licence files,
official project pages, repository documentation, and platform APIs.

The following kinds of endpoint were used:

- the Hugging Face dataset and model APIs, for repository revision,
  last-modified date, gating status, licence tags, declared languages,
  parameter counts, and file sizes;
- the Hugging Face file tree API, for file names and sizes only;
- the GitHub API, for repository revision, licence metadata, and file
  trees;
- the MediaWiki API, for the live Luganda Wikipedia licence and statistics;
- the Wikimedia dump index, for the dump date and size;
- the arXiv API, for the Kimera paper abstract.

Web search was unavailable during this session. No search-engine result is
treated as evidence.

### 3.2 Gated material

Several cards and repositories are gated. When a gated card returned HTTP
401 without authentication, this document says so. Facts read from those
cards in an earlier review on the same date are labelled **source claim**
unless platform metadata independently confirms them.

Gated does not mean unusable. It means that access conditions must be
accepted by an authorised person before use, and that a later reviewer may
not be able to reproduce the card reading without that access.

### 3.3 What was not done

- No dataset rows were downloaded.
- No model weights were downloaded.
- No inference was run.
- No API key or paid service was used.
- No native speaker was consulted.
- No legal opinion was obtained.

---

## 4. Task A: Resource validation

This section is the linked provenance record for the five considered
sources, as allowed by `data/README.md`. It is a review record, not an
acquisition record. No dataset has been acquired.

### 4.1 Summary

| Resource | Luganda evidence | Licence | Classification | Main blocker |
|---|---|---|---|---|
| Sunbird SALT | Verified: `language:lg` tag, `text-all` config, `multispeaker-lug` and `studio-lug` configs | CC BY-SA 4.0 tag; gated terms | **Verified candidate**, conditions apply | Gated access; share-alike; speaker and translation provenance |
| Luganda Wikipedia | Verified: live wiki, dump, statistics | CC BY-SA 4.0 on the live wiki; mirror is CC BY-SA 3.0 | **Verified candidate**, conditions apply | Not conversational; stale mirror; quality varies |
| Kimera English-Luganda corpus | Verified: repository and paper describe the corpus | CC0-1.0 repository claim over third-party sources | **Candidate requiring licensing or provenance review** | Upstream rights; alignment quality; BLEU direction conflict |
| FLORES-200 (`lug_Latn`) | Verified: `lug_Latn` files and `language:lg` tag | CC BY-SA 4.0 in README and HF tag; GitHub reports NOASSERTION | **Verified candidate**, evaluation only | Gated; hidden test; web-article domain |
| MAFAND-MT (`en-lug`) | Verified: `language:lg`, `en-lug` config, published split counts | CC BY-NC 4.0 data; Apache-2.0 code | **Candidate requiring licensing review** | Non-commercial restriction; news provenance |

None of these is approved for acquisition, training, or redistribution.
Classification is an evidence statement, not permission.

### 4.2 Sunbird SALT

**Exact source and snapshot**

- Dataset: `Sunbird/salt` on Hugging Face.
- Repository revision: `a0ffb52b49cdf7bf69149e5d418655313ffc41f4`.
- Last modified: 2025-05-06.
- Gating: automatic (`gated: auto`), so access requires accepting
  conditions while authenticated.
- Paper: https://openreview.net/pdf?id=BK-z5qzEU-9.

**Evidence that Luganda is included**

Verified from platform metadata: the tags include `language:lg`; the file
tree contains `text-all`, `text-hard`, `multispeaker-lug`, and `studio-lug`
configurations. The `lug` configuration is distinct from the `lgg`
configuration, so the two must not be confused.

The dataset card, read in an earlier review on 2026-10-20 before the card
returned HTTP 401, lists Luganda with translated text, multispeaker speech,
and studio speech all marked "Yes". That card statement is a source claim
in this revision because the card is now gated.

**Data type and intended purpose**

Multi-way parallel text plus speech. The card describes translation,
automatic speech recognition, and text-to-speech tasks. The text is
sentence-level and multi-way parallel, not conversational.

**Published size and unit**

- Source claim: a core set of 25,000 sentences covering agriculture,
  health, and society, translated into all languages; roughly 5,000
  sentences recorded.
- Verified file sizes: `text-all/train-00000-of-00001.parquet` is
  9,525,882 bytes; dev is 222,870 bytes; test is 232,970 bytes. These are
  file sizes, not row counts.
- Source claim: total dataset size about 1.74 GB and size category 10K to
  100K.

A Luganda-only row count is not published in the metadata reviewed. It
must be counted locally after approved access.

**Licence and conditions**

- Licence tag: `cc-by-sa-4.0`. Verified.
- Attribution and share-alike apply. A derived benchmark or adapted text
  may inherit share-alike obligations. This needs legal review before any
  redistribution.
- The gated terms were not reviewed because access was not requested.
- The card credits Makerere University AI Lab. Speaker consent terms,
  translator agreements, and the provenance of the source English text
  were not established.

**Does the repository licence cover the dataset?**

The Hugging Face dataset repository is the dataset, and the uploader has
tagged it CC BY-SA 4.0. That is the uploader's declaration, not a legal
opinion. The gated terms may add conditions, and the uploader may not hold
all rights in speaker recordings or third-party source text. The tag is
evidence of intent, not proof of complete provenance.

**Upstream provenance**

Source claim: produced with Makerere University AI Lab; topics are
agriculture, health, and society. The card does not publish a full
translator, speaker, or source-text provenance record in the metadata
reviewed.

**Access requirements**

Gated Hugging Face access. Requires an account, acceptance of the dataset
conditions, and probably a token for programmatic download. No access was
requested in this task.

**Training use, evaluation use, or both**

Both are technically possible under CC BY-SA 4.0, subject to the gating
terms and share-alike review. For this project, the stronger use is
evaluation and reference-text authoring because the text is professionally
translated and multi-way parallel. It is not a conversational corpus.

**Contamination risks**

- A Luganda instruction model, `AmplifiedAccess/Luganda-gemma-1b-it`,
  states that it was trained on SALT. Using SALT sentences as benchmark
  items would therefore contaminate that model's evaluation.
- The text is widely used in Luganda MT work; overlap with other public
  corpora is possible.
- The `text-all` and `text-hard` splits may share source sentences. Any
  evaluation split must be checked for exact and near-duplicate overlap.

**Unresolved questions**

- What exactly do the gated terms require?
- Are speaker recordings covered by informed consent that permits this
  use and redistribution?
- Which source text was translated, and under what rights?
- How many Luganda rows are in `text-all` and how do they relate to the
  `salt-dev` split used by Sunbird's translation model?
- Is share-alike acceptable for the project's benchmark and any future
  release?

**Verification status:** verified candidate, with gated access and
share-alike conditions. Luganda presence and licence tag verified. Detailed
provenance and gated terms unverified.

### 4.3 Luganda Wikipedia

**Exact source and snapshot**

- Live wiki: https://lg.wikipedia.org.
- Dump: `lgwiki-latest-pages-articles-multistream.xml.bz2`, dated
  2026-10-01 18:30, size 10,131,294 bytes. Verified from the Wikimedia
  dump index.
- Statistics on 2026-10-20: 5,874 content articles, 12,256 total pages,
  77,044 edits, 92 active users, 3 administrators, and 2,876,031 article
  words. Verified from the MediaWiki API.
- Hugging Face mirror: `wikimedia/wikipedia`, revision
  `b04c8d1ceb2f5cd4588862100d08de323dccfbaa`, last modified 2024-01-09,
  with a `20231101.lg` configuration. The mirror is stale relative to the
  live dump.

**Evidence that Luganda is included**

The live wiki is Luganda. The dump is the Luganda Wikipedia dump. The
Hugging Face mirror has a dedicated `lg` configuration and a `language:lg`
tag. Verified.

**Data type and intended purpose**

Monolingual encyclopedic text. Useful for language-model support data,
tokenizer statistics, spelling and vocabulary checks, and prompt
inspiration. It is not a conversational corpus and is not a source of
reference answers by itself.

**Published size and unit**

- 5,874 content articles and 2,876,031 article words, verified from the
  live wiki statistics.
- Dump size 10,131,294 bytes compressed, verified.
- The mirror's `20231101.lg` configuration is from 2023-11-01 and should
  not be described as the current wiki.

**Licence and conditions**

- The live wiki declares CC BY-SA 4.0 through the MediaWiki rights
  information endpoint. Verified.
- The Hugging Face mirror is tagged CC BY-SA 3.0 and GFDL. Verified.
- Attribution and share-alike apply. The licence version differs between
  the live wiki and the mirror, so the snapshot used must be recorded.
- Individual pages may contain quoted or imported material with separate
  rights. A bulk dump is not a guarantee that every page is clean.

**Does the repository licence cover the dataset?**

For the live wiki, the site licence covers original contributions by
editors, subject to the terms of use. For the mirror, the dataset card's
licence tag is a third-party restatement and is a version behind the live
site. The dump plus the live site terms is the better provenance record.

**Upstream provenance**

Community-authored wiki pages. Some pages may be translations, stubs, or
partly machine-generated. The project has not audited individual articles
for origin or quality.

**Access requirements**

Public. Dumps can be downloaded without an account. The mirror is public.
No gating.

**Training use, evaluation use, or both**

Training and tokenizer use are plausible after licence review. Evaluation
use is limited: encyclopedic text does not test conversation, and the
project should not treat Wikipedia prose as a gold standard for natural
Luganda.

**Contamination risks**

- Public Wikipedia text is likely present in many multilingual training
  corpora. A benchmark item copied from Wikipedia could be memorised.
- The mirror and the live dump overlap. Pick one snapshot and record it.
- Article text may overlap with news or educational sources.

**Unresolved questions**

- Which snapshot is authoritative for the project: the 2026-10-01 dump or
  the 2023-11-01 mirror?
- Is CC BY-SA 4.0 acceptable for any planned redistribution?
- How much of the wiki is stub or machine-translated text?
- Should Wikipedia be excluded from benchmark authoring to reduce
  memorisation risk?

**Verification status:** verified candidate for monolingual and tokenizer
use, with licence and quality caveats.

### 4.4 Kimera English-Luganda parallel corpus

**Exact source and snapshot**

- GitHub: `kimrichies/English-Luganda-Parallel-corpus`.
- Default branch `main`, commit `d044e97aac6e877647c11d4169fce6acf09ddc14`,
  dated 2024-06-10. Verified from the GitHub API.
- Repository size: 8,651 KB.
- Files: `FinalMergedDataset5.txt` (9,355,840 bytes),
  `Bible_paralle_corpus.xlsx` (3,837,226 bytes), `LICENSE` (7,048 bytes),
  and `README.md` (1,103 bytes). Verified from the GitHub tree API.
- Paper: https://arxiv.org/abs/2301.02773, arXiv 2301.02773v1, published
  2023-01-07.
- Related Hugging Face dataset:
  `kimrichies/English-Luganda_Bible_corpus`, revision
  `fade04c25cc315a299523aab4ba7947756f2cb6b`, last modified 2025-01-15,
  gated automatic, AFL-3.0 tag, file `eng.lug.txt` of 16,494,032 bytes.

**Evidence that Luganda is included**

The repository and paper describe an English-Luganda bilingual corpus.
The Hugging Face Bible dataset is tagged `language:en` and `language:lg`.
Verified.

**Data type and intended purpose**

Parallel text for machine translation. The paper reports building the
corpus from three open corpora and training NMT models. It is
sentence-level, not conversational.

**Published size and unit**

- Source claim: 41,070 pairwise sentences built from three open corpora.
- The repository's merged text file is 9,355,840 bytes and the Bible
  spreadsheet is 3,837,226 bytes. These are file sizes, not sentence
  counts.
- The Hugging Face Bible dataset has a size category of 1K to 10K. The
  relationship between its rows and the paper's 41,070 pairs is not
  established.

**Licence and conditions**

- The GitHub repository declares CC0-1.0. Verified through the GitHub API
  licence metadata and the repository `LICENSE` file, which contains the
  CC0 1.0 Universal legal code.
- The Hugging Face Bible dataset declares AFL-3.0. Verified.
- The README credits Zenodo record 4764039, Sunbird AI, and the Bible
  World Project as sources.
- A CC0 declaration over third-party Bible translations, Sunbird text, or
  Zenodo material is an unresolved rights question. The uploader may not
  hold the rights needed to apply CC0 to all of the content.

**Does the repository licence cover the dataset?**

The CC0 file sits at the repository root and appears intended to cover the
repository contents, including the data files. It cannot, by itself, grant
rights the uploader does not hold. The upstream sources have their own
terms. The repository licence therefore does not establish permission for
the underlying data.

**Upstream provenance**

Source claim from the README: Zenodo, Sunbird AI, and the King James Bible
text from the Bible World Project. The paper says three open corpora but
does not, in the abstract, name each one. Alignment quality is not
independently documented.

**Access requirements**

Direct GitHub and Hugging Face download. The Bible dataset is gated
automatic. No access was requested.

**Training use, evaluation use, or both**

Training use is technically possible after rights review. Evaluation use
is weaker: the religious and Bible register is not representative of
conversation, and alignment quality is unverified.

**Contamination risks**

- The corpus includes Sunbird-derived data, so it may overlap SALT and
  models trained on SALT.
- Bible text is widely available and likely present in other corpora.
- The merged file may contain duplicates across its three sources.

**Unresolved questions**

- What are the exact upstream licences for each of the three corpora?
- Did the uploader have permission to apply CC0 to all of it?
- How was sentence alignment produced and checked?
- Does the merged dataset overlap SALT, FLORES, or MAFAND?
- Which BLEU direction is correct: the paper or the README?

**BLEU conflict, recorded exactly**

- Paper abstract: "BLEU score of 21.28 from Luganda to English and 17.47
  from English to Luganda."
- Repository README: "BLEU score of 21.28 for English-to-Luganda and 17.47
  for Luganda-to-English."

Both are source claims. The disagreement is unresolved and the numbers
must not be quoted without the direction caveat.

**Verification status:** candidate requiring licensing or provenance
review. Existence, size claims, and licence tags are verified. Upstream
rights and alignment quality are unverified.

### 4.5 FLORES-200 (`lug_Latn`)

**Exact source and snapshot**

- Hugging Face dataset: `facebook/flores`, revision
  `71abf77d8b7beb5cfef59898d6b24d92ab7654fc`, last modified 2026-05-29,
  gated automatic.
- GitHub: `facebookresearch/flores`, archived, commit
  `a6c830c6e1051fb4ac1a44b32358f00463f332bd`, dated 2023-11-20.
- Snapshot note: the archived repository points to a newer FLORES+ release
  at `openlanguagedata/flores`, which is also archived and whose GitHub
  metadata does not identify a licence. The project must choose one
  snapshot before use.
- Luganda files: `data/language/lug_Latn/dev-00000-of-00001.parquet`
  (112,608 bytes) and `data/language/lug_Latn/devtest-00000-of-00001.parquet`
  (119,573 bytes). Pair directories exist for English-Luganda in both
  directions. No public test split file is present.

**Evidence that Luganda is included**

Verified: the `lug_Latn` language directory exists, the pair directories
`eng_Latn-lug_Latn` and `lug_Latn-eng_Latn` exist, and the dataset tags
include `language:lg`.

**Data type and intended purpose**

Professionally translated parallel evaluation benchmark for machine
translation. It is designed for evaluation, not training.

**Published size and unit**

- Verified from the FLORES-200 README: 842 distinct web articles, 3,001
  sentences, divided into dev, devtest, and a hidden test set.
- Verified file sizes for the Luganda dev and devtest parquet files.
- The public repository does not expose the hidden test split.

**Licence and conditions**

- The FLORES GitHub README states: "FLORES-200: CC-BY-SA 4.0". Verified.
- The Hugging Face dataset card tag is `cc-by-sa-4.0`. Verified.
- The GitHub API reports the repository licence as "Other" with SPDX
  `NOASSERTION`, so the repository metadata does not identify a standard
  licence. The README statement is more specific than the repository
  metadata and is the relevant licence statement for FLORES-200.
- Attribution and share-alike apply. A legal review is still required
  before redistribution.

**Does the repository licence cover the dataset?**

The top-level GitHub metadata does not identify a standard licence. The
README explicitly licenses FLORES-200 under CC BY-SA 4.0, and the Hugging
Face card repeats that tag. That is the best available licence statement,
but it is not a signed legal opinion.

**Upstream provenance**

The FLORES-200 README states 3,001 sentences from 842 distinct web
articles, professionally translated. The source articles' own rights are
not established by the FLORES licence. The benchmark's value is the
translation, not the source articles.

**Access requirements**

Gated automatic on Hugging Face. The GitHub repository is public, though
the hidden test set is not distributed.

**Training use, evaluation use, or both**

Evaluation only. Training on FLORES would invalidate it as a benchmark and
is explicitly discouraged by its design. The hidden test split limits
reuse and should be respected if access is granted.

**Contamination risks**

- FLORES is widely used as a training set by accident. Any model with an
  unknown training mixture may have seen it.
- `lug_Latn` dev and devtest may appear in community Luganda corpora.
- If the project uses FLORES for a translation probe, it must check
  overlap with any model's training data where possible, and must not use
  the same sentences for prompt authoring or tuning.

**Unresolved questions**

- Is the hidden test split accessible under the gated terms, and should
  the project use devtest only?
- Which FLORES snapshot is authoritative: the archived FLORES-200
  repository, the FLORES+ repository, or the 2026 Hugging Face revision?
- Does the FLORES+ release change the Luganda text, the licence, or the
  split boundaries?
- Is CC BY-SA 4.0 acceptable for the project's evaluation artefacts?
- How much of FLORES appears in SALT, MAFAND, or community corpora?

**Verification status:** verified candidate for machine-translation
evaluation, with gated access and share-alike conditions.

### 4.6 MAFAND-MT (`en-lug`)

**Exact source and snapshot**

- Hugging Face dataset: `masakhane/mafand`, revision
  `b215cd3c701dd16e447a0a2132fb73181acd6c53`, last modified 2023-09-11.
- Gating: none (`gated: false`).
- The dataset uses a loading script, `mafand.py`, version 1.0.0, with a
  configuration named `en-lug`.
- The script downloads per-split JSON files for train, validation, and
  test for the configuration.

**Evidence that Luganda is included**

Verified: the dataset tags include `language:lg`; the card lists Luganda;
the loading script defines `MafandConfig(name="en-lug",
version=datasets.Version("1.0.0"))`. The card table gives the Luganda
split counts explicitly.

**Data type and intended purpose**

News-domain parallel corpus and machine-translation benchmark. The card
states that MAFAND was created from the news domain, translated from
English or French into an African language. It is sentence-level, not
conversational.

**Published size and unit**

The card table reports:

`lug | 4075 | 1500 | 1500`

The unit is sentence pairs. Read as train, validation, and test, this is
4,075 training pairs, 1,500 validation pairs, and 1,500 test pairs, or
7,075 pairs in total. The card's size category is 1K to 10K. Verified from
the card text.

**Licence and conditions**

- Dataset card licence: CC BY-NC 4.0. Verified tag.
- The `mafand.py` script header mentions Apache License 2.0. That is the
  licence of the loading code, not of the data. The two must not be
  confused.
- Non-commercial use only. Any commercial or product use requires a
  separate permission analysis or a different dataset.
- The underlying news articles may carry publisher rights that the
  dataset licence does not override.

**Does the repository licence cover the dataset?**

The dataset card's CC BY-NC 4.0 tag is the uploader's data licence. The
Apache-2.0 script header covers the software. The news articles' upstream
rights are not established by either. The dataset is usable only if the
project accepts non-commercial terms and the provenance review clears the
news sources.

**Upstream provenance**

Source claim: a novel African news corpus created by the Masakhane project,
translated from English or French. The card does not, in the text
reviewed, list every publisher or provide a per-article rights record.

**Access requirements**

Public on Hugging Face. The loading script may require
`trust_remote_code=True` in the `datasets` library. No account or gating
was observed.

**Training use, evaluation use, or both**

Evaluation is the safer use, and only if non-commercial terms are
acceptable. Training use is possible under the same terms but would
require the provenance review and a decision on the non-commercial
restriction. The news domain is not representative of conversation.

**Contamination risks**

- News text may overlap Luganda news corpora and SALT's society topic set.
- The dataset may be present in multilingual MT training mixtures.
- The validation and test splits are public, so models trained on
  MAFAND-derived data may have seen them.

**Unresolved questions**

- Is the project non-commercial for the purposes of CC BY-NC 4.0?
- Which news publishers contributed the text, and under what terms?
- Are the Luganda translations professionally reviewed, or
  translation-assisted?
- Does MAFAND overlap SALT or FLORES?
- Should the public test split be used, or only a held-out private split?

**Verification status:** candidate requiring licensing review. Luganda
presence, split counts, and licence tag are verified. News provenance and
the consequences of the non-commercial restriction are unresolved.

### 4.7 Other resources checked

These are recorded so they are not rediscovered later. They are not part of
the five-candidate validation.

| Resource | What was verified | Classification | Note |
|---|---|---|---|
| MasakhaNER 2.0 | `language:lg`, AFL-3.0 | Verified candidate for linguistic probes | NER annotation, news domain, not conversational |
| MasakhaPOS | `language:lg`, AFL-3.0 | Verified candidate for linguistic probes | POS annotation, not conversational |
| English Wiktionary, Luganda lemmas | 165 pages and 6 subcategories | Verified candidate for authoring support | Lexical data, not conversational |
| Luganda Wiktionary incubator | 1 entry | Insufficient evidence | Not usable yet |
| Tatoeba Luganda export | 507 sentences, 501 English links, counted locally in an earlier review | Candidate requiring licence confirmation | Small; sentence-level; licence terms not re-verified in this pass |
| Community Bible corpora | Existence and licence tags | Candidate requiring licensing or provenance review | Bible translation rights usually sit with the publisher |
| NLLB-derived community corpora | Existence and size categories | Candidate requiring licensing or provenance review | Upstream NLLB data is not public; Apache-2.0 claims cannot be traced |
| OSCAR 23.01 | No `lg` in the language table; access suspended | Unsuitable for current use | No verified Luganda subcorpus |
| mC4 | 113 configurations, none `lg` or `lug` | Unsuitable for current use | No verified Luganda subcorpus |
| CulturaX | 167 languages, `lg` absent | Unsuitable for current use | No verified Luganda subcorpus |
| Common Crawl | Not language-labelled | Insufficient evidence | Luganda presence cannot be confirmed from the source |
| Common Voice legacy `lg` | `language:lg` on the legacy aggregate | Out of scope (speech) | D-002 is text-only; current release coverage unverified |
| Synthetic instruction data | Cards state machine translation or synthetic origin | Unsuitable for quality evaluation | Not native-reviewed; contamination risk |

### 4.8 Cross-cutting licence and provenance findings

1. **A repository licence is not a provenance audit.** Kimera's CC0,
   MAFAND's CC BY-NC, and several community Apache-2.0 claims describe
   what the uploader asserts, not necessarily what the upstream rights
   holders granted.
2. **Code licences and data licences are different.** MAFAND's script is
   Apache-2.0; its data is CC BY-NC 4.0. The Apache-2.0 header must not be
   read as a data licence.
3. **Share-alike is a real obligation.** SALT, FLORES, and Wikipedia are
   all share-alike. Any derived benchmark or published reference text may
   inherit those obligations.
4. **Non-commercial is a real restriction.** MAFAND and NLLB-derived
   models are CC BY-NC 4.0. The project's commercial status is not
   recorded, so this must be decided before use.
5. **Gated access is a reproducibility dependency.** SALT, FLORES,
   Sunflower, and Sunbird's translation model require authenticated
   access. A rerun by another person depends on that person also being
   approved.
6. **Language tags are not proof.** The `cdli` speech dataset is tagged
   Luganda but describes Ugandan English. Tags must be checked against
   descriptions and file contents.
7. **The Wikipedia mirror is stale.** The live wiki is CC BY-SA 4.0 and
   dated 2026-10-01; the mirror is a 2023-11-01 snapshot tagged
   CC BY-SA 3.0 and last modified in 2024.

---

## 5. Task B: Proposed benchmark specification

### 5.1 What is preserved

This proposal keeps, without change:

- the approximately 50-prompt size;
- the nine categories in `docs/EVALUATION_PLAN.md`;
- the seven scoring dimensions in `docs/EVALUATION_PLAN.md`;
- the mandatory native-speaker requirement in D-004;
- the existing contamination-control principles and reporting rules.

`docs/EVALUATION_PLAN.md` remains the source of truth until this proposal
is approved. Nothing here is approved, and no prompts are written.

The operational specification is now `docs/BENCHMARK-SPECIFICATION.md`. It
is also a draft and is not approved. This section remains the research
rationale and summary; the companion document is the reviewable
specification.

### 5.2 Proposed changes to the existing plan, and why

| Proposed change | Why it is needed |
|---|---|
| Add an item schema with stable IDs and a benchmark version | The plan has no machine-readable item format, so items cannot be versioned, reviewed, hashed, or scored consistently |
| Record prompt language and expected response language per item | The plan names categories but not language. Without this, a model could answer a Luganda prompt in English and still appear compliant |
| Add a reference-answer policy | The plan does not say when a single reference exists. Open conversational items have several valid answers and must not be scored against one string |
| Add an ambiguity review step | Unresolved ambiguity produces unfair failures. The plan has no procedure for detecting or recording it |
| Specify the native-review procedure: two reviewers, adjudicator, calibration set, agreement statistic | D-004 requires native review but the plan does not define how many reviewers, how disagreements are resolved, or how agreement is reported |
| Fix a five-point scale with anchors for 1, 3, and 5 | The plan leaves the scale open. Scoring cannot start without anchors, and reviewers need the same reference points |
| Add an applicability matrix and forbid an unweighted composite | The seven dimensions are not interchangeable. Context retention does not apply to single-turn items, and an unweighted average would hide critical failures |
| Add required run metadata | The plan says to include configuration, but not which fields. Model revision, quantisation, seed, and prompt hash are needed for reproducibility |
| Add contamination checks specific to Luganda resources | The plan states principles but no procedure. A Luganda model trained on SALT makes SALT-derived benchmark items unsafe |
| Add exclusion rules | Without them, failed or truncated runs may be silently dropped or silently counted |
| Add a limitations section | The plan does not state the limits of a 50-item benchmark, a small reviewer pool, or unverified model cards |
| Propose a draft category allocation | The plan leaves distribution open. A concrete proposal makes review possible, but it is explicitly not final |
| Add an optional translation probe separate from the 50 conversational items | The nine categories are conversational. Translation-only models cannot be scored on them, so a separate probe prevents a misleading comparison |
| Mark the benchmark as draft until approved | The plan does not carry a status marker, which makes premature citation easy |

### 5.3 Item schema (proposal)

```json
{
  "id": "LGP-BENCH-v0.1-FORMAL-001",
  "benchmark_version": "0.1-draft",
  "track": "conversational",
  "category": "formal_luganda",
  "prompt_language": "lg",
  "response_language": "lg",
  "prompt": "<prompt text>",
  "turns": [],
  "expected_behavior": "<what a correct response must do>",
  "reference_answer": null,
  "reference_status": "pending",
  "accepted_alternatives": [],
  "rubric_dimensions": [
    "semantic_correctness",
    "grammar_naturalness",
    "appropriate_register"
  ],
  "ambiguity_notes": "",
  "cultural_note": "",
  "source_inspiration": "original",
  "source_url": null,
  "source_license": null,
  "contamination_notes": "",
  "review_status": "draft",
  "reviewer_ids": [],
  "reviewer_scores": [],
  "adjudication_notes": "",
  "created_by": "human",
  "created_at": "2026-10-20"
}
```

Controlled values:

- `track`: `conversational` or `translation_probe`.
- `category`: one of the nine category codes below.
- `prompt_language`: `lg`, `lg-en`, or `en`.
- `response_language`: `lg`, `lg-en`, `en`, or `model_choice`.
- `reference_status`: `authored`, `pending`, or `not_applicable`.
- `review_status`: `draft`, `ambiguity_checked`, `native_reviewed`,
  `approved`, or `excluded`.
- `source_inspiration`: `original`, `salt`, `flores`, `mafand`,
  `wikipedia`, or `other`. If not original, `source_url` and
  `source_license` are required.

Rules:

- IDs are never reused. A retired item keeps its ID and receives
  `review_status: excluded`.
- `benchmark_version` changes whenever an item is added, removed, or
  materially edited.
- `reviewer_scores` stores raw scores and reviewer IDs; adjudicated scores
  are stored separately so the original disagreement remains visible.
- No Luganda text is generated by a model and stored as a reference
  answer.

### 5.4 Category definitions and draft allocation

The nine categories are unchanged. The operational requirement and draft
count below are proposals for review. The allocation sums to 50 but is not
final.

| Category | Code | Operational requirement | Draft count | Prompt language | Expected response |
|---|---|---|---|---|---|
| Formal Luganda | `formal_luganda` | Educated register; grammar, naturalness, and register all matter | 6 | Luganda | Luganda |
| Everyday Luganda | `everyday_luganda` | Ordinary conversational usage; naturalness and relevance | 7 | Luganda | Luganda |
| Colloquial language | `colloquial` | Informal speech, slang, or regional variation; record the variety | 6 | Luganda | Luganda |
| Luganda-English code-switching | `code_switching` | Intentional mix; expected mix behaviour is stated per item | 6 | Mixed Luganda and English | Match the prompt's mix |
| Instruction following | `instruction_following` | Constrained task with objective compliance checks | 5 | English or Luganda | Stated per item |
| Multi-turn context | `multi_turn` | At least two turns; a later turn depends on an earlier one | 5 | Luganda | Luganda |
| Explanation and reasoning | `explanation_reasoning` | Concept explanation or multi-step reasoning; correctness and coherence, not only fluency | 6 | Luganda | Luganda |
| Cultural and linguistic interpretation | `cultural_interpretation` | Idiom, proverb, or cultural context; native-authored accepted interpretation | 5 | Luganda | Luganda |
| Factuality and appropriate uncertainty | `factuality_uncertainty` | Checkable factual claim plus at least one item that rewards a correct "I do not know" | 4 | Luganda | Luganda |

Draft total: 50.

Why this shape: the product is conversational, so Everyday, Formal,
Colloquial, and Code-switching carry most items. Multi-turn and
Explanation test capabilities that single-turn translation cannot. Cultural
items need native authorship and are expensive to review, so they are
fewer. Factuality gets fewer items because checking facts requires
external verification, not only language judgment.

The exact allocation remains open. A director may prefer a flat
distribution, more factuality, or a larger multi-turn block.

### 5.5 Prompt language requirements

- Formal, Everyday, Colloquial, Multi-turn, Explanation, Cultural, and
  Factuality prompts are written in Luganda.
- Code-switching prompts intentionally mix Luganda and English.
- Instruction-following prompts may be English or Luganda. The item
  records the prompt language and the required response language.
- Script is Latin. Orthography follows the standard the native reviewers
  agree on. The benchmark records that standard; it does not invent one.
- A Luganda-only prompt contains no English gloss. If a term has no
  settled Luganda equivalent, the item states how the term is handled.
- Proper names may remain in their usual form.
- The expected response language is part of the item, not an assumption
  left to the model.

### 5.6 Reference-answer policy

- Closed factual items and translation-probe items may have one authored
  reference answer.
- Open conversational items use `expected_behavior` plus the rubric, not a
  single reference string, because several answers can be correct.
- Cultural items may record more than one accepted interpretation, with a
  native-authored note explaining the range.
- A `reference_answer` is set only when a native speaker authored or
  approved it. A model must never fill in a Luganda reference answer.
- `accepted_alternatives` records defensible variants that should not be
  marked wrong.
- If the reference is borrowed from SALT, FLORES, or Wikipedia, the item
  records the source and licence, and the borrowing must not defeat the
  contamination rules.

### 5.7 Ambiguity checks

Every item gets an ambiguity check before native review.

1. The author records the intended reading and any plausible alternative.
2. A second reviewer, fluent in Luganda and not the author, reads the item
   without the intended answer and states what they think it asks.
3. If the two readings differ materially, the item is rewritten.
4. If the ambiguity is intrinsic and cannot be removed, for example a
   proverb with several accepted interpretations, the item sets
   `reference_status: not_applicable`, records the alternatives in
   `ambiguity_notes`, and is scored on the rubric rather than against one
   answer.
5. An ambiguous item is never scored as a model failure merely because
   the model chose a defensible alternative.

The ambiguity reviewer may be a native speaker or a fluent second
reviewer. Native review still follows section 5.8.

### 5.8 Native-speaker review

D-004 makes native-speaker review mandatory for language-quality
assessment. This proposal defines the procedure:

- At least two native Luganda speakers review each item and each response.
- A third native reviewer adjudicates disagreements of two or more points
  on any dimension, or disagreements about whether an answer is
  acceptable.
- Reviewers must not be authors of the model output being scored. Authors
  of the item may review it, but that involvement is recorded.
- Reviewers receive a packet containing the item, expected behaviour,
  rubric anchors, reference answer if any, accepted alternatives, and
  ambiguity notes.
- A calibration set of about five items is scored by all reviewers before
  the main review. The calibration is used to align anchors, not to
  produce results.
- A subset of items is scored by all reviewers to allow agreement
  checking.
- Agreement is reported as exact agreement, agreement within one point,
  and a chance-corrected statistic such as quadratic-weighted Cohen's
  kappa or an intraclass correlation coefficient. The statistic used is
  recorded.
- Each review records reviewer ID, date, scores, comments, and any
  adjudication.
- Reviewers are compensated according to a budget approved by the project
  director. No rate is assumed here.
- Consent, attribution, and data retention for reviewer comments are
  recorded before review starts.
- The workload is roughly two reviews per item per model response. The
  director should size the budget before approving a four-model
  shortlist; the number of models or items may need to be reduced to fit
  the available review capacity.

No part of this document claims that native review has occurred. No
reviewer has been recruited.

### 5.9 Scoring rules and scale

A five-point ordinal scale is proposed for each applicable dimension:

- 1: unacceptable.
- 2: weak.
- 3: adequate.
- 4: good.
- 5: excellent.

Anchors for 1, 3, and 5:

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| Semantic correctness | Meaning is wrong or contradicts the prompt | Main meaning is preserved; minor omission or imprecision | Meaning is fully preserved, including nuance and implied content |
| Grammar and naturalness | Not understandable as Luganda, or systematic grammar failure | Understandable; noticeable errors or unidiomatic phrasing that do not block meaning | Grammatical, idiomatic, native-sounding Luganda for the requested register |
| Instruction compliance | Ignores the instruction or violates a hard constraint | Follows the main instruction; misses a secondary constraint | Follows all stated constraints, format, length, and response language |
| Relevance | Off-topic or does not answer | Partly relevant; some drift or a missing sub-question | Directly answers the question with appropriate scope |
| Context retention | Forgets or contradicts earlier turns | Retains the main context; loses a minor detail | Consistently uses earlier turns, resolves references, and avoids contradictions |
| Factual reliability | Confident false claim or fabricated source | Mostly correct; a minor error or unsupported detail | Correct, appropriately qualified, no fabrication; says "I do not know" when needed |
| Appropriate register | Register is wrong for the request | Broadly appropriate; some mixing or inconsistency | Consistently matches the requested register and audience |

Applicability matrix:

| Dimension | Applies to |
|---|---|
| Semantic correctness | All items |
| Grammar and naturalness | All items |
| Instruction compliance | Instruction following, Multi-turn, Code-switching, and any item with hard constraints |
| Relevance | All items |
| Context retention | Multi-turn only |
| Factual reliability | Factuality, Explanation and reasoning, and factual claims in Cultural items |
| Appropriate register | Formal, Colloquial, Code-switching, and Cultural items |

A dimension that does not apply is recorded as `null`, not as zero. Nulls
are not averaged.

Aggregation:

- Report the distribution of scores per dimension, with median and
  interquartile range.
- Do not publish a single overall score until weights are approved. The
  dimensions are not interchangeable, and an unweighted average can hide a
  critical failure such as a confident false fact.
- If a single decision score is required later, the rule must be approved
  in advance, for example a minimum across critical dimensions or a
  weighted score with published weights.
- Automated metrics are reported separately and labelled as support
  metrics. They never replace native scores.

Failure categories to record separately:

- wrong response language;
- refusal or non-answer;
- hallucinated fact or source;
- truncated output;
- unsafe or inappropriate content;
- off-topic answer;
- formatting or instruction violation.

### 5.10 Required evaluation metadata

Every run records:

- `run_id`;
- `benchmark_version` and `item_file_sha256`;
- exact model identifier, model revision, and base-model revision;
- adapter identifier and revision, if any;
- tokenizer identifier and revision;
- chat template or prompt template;
- system prompt, if any;
- quantisation, dtype, device, and framework versions;
- temperature, top_p, top_k, maximum new tokens, stop sequences, and
  repetition penalties;
- random seed, if the interface exposes one;
- batch size and number of samples per item;
- hardware, operating system, and wall-clock time;
- peak memory, if measured;
- paid API provider, model version or date, token counts, cost, and
  approval reference, if any;
- data-retention or logging terms for a hosted API;
- reviewer IDs and review dates;
- the path to the raw response file.

For a hosted API, the provider's model version may change without notice.
The run records the date and any version identifier the provider exposes.
A rerun after a provider update is a new run.

### 5.11 Reproducibility

1. Freeze the item file and record its SHA-256 before any run.
2. Pin the model, tokenizer, and adapter revisions. Do not use a moving
   `main` reference for a reported run.
3. Record every decoding setting. Greedy decoding (temperature 0) is the
   primary setting for comparability.
4. Optionally run three samples at a documented higher temperature to
   show variance. Report those separately from the greedy results.
5. Use the same prompt template for every model. If a model requires a
   different chat template, record it and do not tune the prompt
   per model.
6. Record the Python version, operating system, and key library versions.
7. Store raw responses verbatim. Do not edit, normalise, or translate
   them before storage.
8. A change to the prompts, model revision, or settings creates a new
   run ID or benchmark version. Results are not compared across versions
   without documenting the difference.
9. Record the access path for gated resources, so a rerun can establish
   whether the same snapshot was used.

### 5.12 Contamination control

- Benchmark items are original. They are not copied from SALT, FLORES,
  MAFAND, Wikipedia, or a model's training set.
- If an item is inspired by a source, the source is recorded and the item
  is rewritten so it is not a near-duplicate.
- Check exact and near-duplicate overlap between benchmark items and any
  training data whose contents are known. A practical starting point is
  an 8-gram overlap check plus manual review of flagged pairs.
- `AmplifiedAccess/Luganda-gemma-1b-it` states that it was trained on
  SALT. SALT sentences must not be used as conversational benchmark items,
  and any SALT-based translation probe must be reported as in-domain and
  potentially contaminated.
- Sunflower's training data is not public in the metadata reviewed. Its
  contamination status is unknown, not clean.
- Do not use benchmark items as few-shot examples, tuning data, or
  demonstration examples in a reported evaluation.
- Keep benchmark files in a dedicated path, separate from training data.
  A future `data/benchmark/` directory is proposed, but it is not created
  in this task.
- If items are published, consider keeping a private holdout subset to
  detect future contamination.
- Record contamination checks and their limits. A negative check on
  available data does not prove the model never saw the item.

### 5.13 Exclusions

Exclude an item or a run, and record the reason:

- unresolved licence or unresolved ambiguity;
- known or suspected contamination;
- truncated output, unless truncation is the behaviour being measured;
- missing model revision, settings, or item hash;
- no required native review;
- duplicate or near-duplicate items;
- a run that used a different prompt set without a new version.

Wrong-language output is a failure, not an exclusion. A model that cannot
produce Luganda at all is reported as failing the relevant items, not
silently dropped.

### 5.14 Limitations

- Approximately 50 items give limited statistical power. Small
  differences should not be over-interpreted.
- The model set is a convenience sample, not a leaderboard.
- The native reviewer pool may be small and may not represent all Luganda
  varieties or registers.
- No trained LugandaGPT exists. This is a baseline study only.
- Translation-only models cannot be scored on the nine conversational
  categories. They belong in a separate translation probe if one is
  approved.
- Self-reported numbers on model cards are not independently verified.
- Contamination cannot be fully ruled out without a training-data
  inventory, which does not exist yet.
- The orthography and register standards depend on native-speaker
  agreement that has not yet happened.
- Automated metrics are supporting evidence, not ground truth.
- Local memory estimates are arithmetic, not measured peak memory.

### 5.15 What is not decided

- The final category allocation.
- The final scoring weights, if any.
- The exact number of reviewers and the budget.
- Whether a translation probe is in scope.
- Whether the benchmark will be public, private, or partly private.
- The orthography standard.
- The final item file location and owner.

---

## 6. Task C: Model shortlist

### 6.1 Selection rules

The shortlist is capped at four candidates. Selection prioritised:

1. direct Luganda-related evidence, not a generic multilingual claim;
2. a plausible evaluation role;
3. licence and access clarity;
4. local feasibility on roughly 8 GB RAM, or a clearly stated reason why
   local inference is not possible.

Two tracks are used because the nine-category benchmark is conversational:

- **Conversational track:** instruction-following models that can answer
  Luganda prompts.
- **Translation probe track:** encoder-decoder translation models that
  cannot hold a conversation. They are reported separately and are not
  scored on the nine conversational categories.

The translation probe is a proposal, not part of the existing
`docs/EVALUATION_PLAN.md`. If the director does not approve it, candidates
3 and 4 drop out and the shortlist becomes two conversational models.

Candidate 4 is a two-direction pair and counts as one candidate because
the two directions are evaluated together.

No model in this section was downloaded or run. No paid API was called.

### 6.2 Shortlist summary

| # | Model | Track | Direct Luganda evidence | Licence | Access | Local 8 GB? |
|---|---|---|---|---|---|---|
| 1 | `AmplifiedAccess/Luganda-gemma-1b-it` | Conversational | Fine-tuned on SALT; card claims Luganda translation and conversation; self-reported BLEU 13.85 and chrF++ 46.59 | Adapter Apache-2.0; base Gemma terms | Adapter public; base Gemma gated manual | Plausible with 4-bit, subject to Windows tooling |
| 2 | `Sunbird/Sunflower-14B` | Conversational | Tags say Ugandan languages; card claims 31 Ugandan languages including Luganda | Apache-2.0 | Gated automatic; hosted API also offered | No: 14.77B parameters, 29.5 GB BF16 |
| 3 | `Sunbird/translate-nllb-1.3b-salt` | Translation probe | Card lists Luganda; self-reported BLEU 41.978 Luganda to English and 30.359 English to Luganda on `salt-dev` | No licence stated; base NLLB-200-1.3B is CC BY-NC 4.0 | Gated automatic | Plausible with 8-bit or 4-bit quantisation |
| 4 | `Helsinki-NLP/opus-mt-en-lg` and `opus-mt-lg-en` | Translation probe | Direct English-Luganda pair; self-reported BLEU 30.4 on JW300 and 5.7 on Tatoeba for en-lg | Apache-2.0 | Public | Yes: about 0.6 GB for both directions |

Reserve candidates, not shortlisted:

- `facebook/nllb-200-distilled-600M`: local fallback if the Sunbird
  translation licence cannot be resolved. CC BY-NC 4.0, 2.46 GB FP32,
  Luganda `lug_Latn` in the model card language list.
- `facebook/m2m100_418M`: MIT, 1.94 GB FP32, Ganda `lg` in the model card
  language list. Older and weaker evidence than the shortlisted models.
- General multilingual controls, such as `google/gemma-3-1b-it`,
  `Qwen/Qwen2.5-7B-Instruct`, and `meta-llama/Llama-3.2-3B-Instruct`:
  no verified Luganda-specific evidence. A control would help attribute
  gains to Luganda-specific training, but the four-candidate cap and the
  direct-evidence rule exclude it from this round. This is a limitation.

### 6.3 Candidate 1: Luganda Gemma 1B IT

**Exact identifier and snapshot**

- `AmplifiedAccess/Luganda-gemma-1b-it`.
- Revision `5d0f24b80a09f582708ff397c989331d7d7b536f`.
- Last modified 2026-05-23.
- Public, not gated. PEFT adapter.
- Base model: `google/gemma-3-1b-it`.

**Evidence of Luganda support**

- Source claim: the card describes a fine-tuned Gemma 3 1B Instruct model
  for English-Luganda translation and Luganda conversational AI.
- Source claim: the adapter was trained on Sunbird SALT, with 94,542
  training examples derived from about 24,000 clean English-Luganda
  sentence pairs.
- Source claim: BLEU 13.85 and chrF++ 46.59 for English to Luganda on 100
  examples, against BLEU 0.06 for the base model. The repository's
  `eval_results.json` reports the same BLEU and chrF values at
  `eval_size: 100`. This is a self-reported in-domain evaluation, not an
  independent measurement.
- Verified: the adapter file is 52,231,312 bytes. The base model file
  `model.safetensors` is 1,999,811,208 bytes, about 2.0 GB in BF16.

**Model and dataset licensing constraints**

- The adapter card declares Apache-2.0.
- The base model is Gemma 3 1B IT under the Gemma licence, and the base
  model is gated manual.
- The adapter's Apache-2.0 declaration may not override the base model's
  terms. The combined licence status is unresolved.
- The training data is SALT, which is CC BY-SA 4.0 and gated. Whether the
  adapter's training complied with share-alike and gating terms is not
  documented.
- The model card says to use 4-bit quantisation because the LoRA weights
  were trained against 4-bit base weights. Loading in 8-bit or full
  precision may degrade output.

**Access requirements**

- The adapter is public.
- The base model requires accepting the Gemma terms while authenticated.
- Local use requires Python, PyTorch, Transformers, PEFT, and a 4-bit
  quantisation path.

**Estimated local memory**

- Base weights at 4-bit: about 0.5 GB (2.0 GB BF16 divided by 4).
- Adapter: 52 MB.
- Runtime, tokenizer, and KV cache: about 1 to 2 GB, estimate.
- Total working set: about 1.5 to 2.5 GB, estimate.
- The 8 GB machine has roughly 4 to 5 GB available after the operating
  system and normal applications, so this is plausible.

**Local feasibility**

Plausible, with a Windows caveat. The local machine is Windows. 4-bit
inference commonly relies on `bitsandbytes`, whose Windows support may
require a prebuilt wheel or WSL2. This must be tested before local
feasibility is claimed. CPU inference will be slow but may be sufficient
for 50 short prompts.

**Paid service**

Not required if local 4-bit inference works. A hosted GPU is an
alternative if Windows quantisation fails, but that would require budget
approval.

**Known limitations**

- The self-reported evaluation is 100 examples, in-domain, and
  translation-oriented.
- Conversational ability is claimed but not independently tested.
- The model is small; complex reasoning and long context are likely weak.
- SALT training creates a contamination risk for SALT-derived items.
- The licence combination is unresolved.
- The model card itself warns of weaker performance on legal, medical,
  and technical domains, and possible dialectal variation.

**Evidence still needed before selection**

- A licence review of the adapter plus Gemma base terms.
- Confirmation that SALT training did not include the evaluation split
  that will be used.
- An independent conversational smoke test on non-SALT prompts.
- Confirmation that 4-bit inference runs on this Windows machine.
- The exact tokenizer and chat template to record.

### 6.4 Candidate 2: Sunbird Sunflower-14B

**Exact identifier and snapshot**

- `Sunbird/Sunflower-14B`.
- Revision `83faf5eb318dd1814786944e279204de665646fa`.
- Last modified 2026-05-23.
- Gated automatic.
- Base model: `Qwen/Qwen3-14B`.
- Parameters: 14,768,307,200. Verified from safetensors metadata.
- Model file: 29,536,666,272 bytes, about 29.5 GB BF16.

**Evidence of Luganda support**

- Verified tags: `african-languages`, `ugandan-languages`, base model
  Qwen3-14B.
- Source claim: the card states support for 31 Ugandan languages plus
  English, including Luganda. The card was gated during this review, so
  the detailed language table was not re-read.
- Source claim from the earlier review: average chrF 0.366 for English to
  Ugandan languages, chrF 0.419 for Ugandan languages to English, and BLEU
  19.61 for Ugandan languages to English, averaged across 31 languages.
  No Luganda-only breakdown was published on the card.

**Model and dataset licensing constraints**

- The model card declares Apache-2.0. Verified.
- The base model Qwen3-14B is Apache-2.0. Verified.
- The training data and its licences are not documented in the metadata
  reviewed. Apache-2.0 on the weights does not establish that the
  training data was cleared.
- Gated access terms were not reviewed.

**Access requirements**

- Gated Hugging Face access.
- The card also points to a Sunbird AI API.
- API pricing, rate limits, data-retention terms, and permission to use
  the API for benchmarking were not verified.

**Estimated local memory**

- BF16 weights: about 29.5 GB.
- 8-bit weights: about 14.8 GB.
- 4-bit weights: about 7.4 GB.
- KV cache, activations, tokenizer, and runtime: at least 1 to 2 GB,
  estimate.
- Total at 4-bit: roughly 8.5 to 9.5 GB, which exceeds the 8 GB machine.
- The estimate assumes weights-only quantisation and does not include
  memory fragmentation or a long context.

**Local feasibility**

Not plausible on the 8 GB laptop. Offloading to disk would be extremely
slow and is not a realistic baseline path. Local evaluation would need an
approved GPU with more memory, or the hosted API.

**Paid service**

Likely necessary. No price was fetched and no call was made. Any API use
requires project-director approval, a budget cap, and a check of the
provider's terms for benchmark use and data retention.

**Known limitations**

- No Luganda-only published score.
- The 31-language averages cannot be treated as a Luganda result.
- The model is too large for the local machine.
- Training data provenance is unknown.
- Gated access and API terms add reproducibility dependencies.

**Evidence still needed before selection**

- Luganda-specific evaluation evidence, not a 31-language average.
- API price, quota, terms, and data-retention policy.
- Permission to use the API for a benchmark.
- A licence and provenance review of the training data, if available.
- Confirmation that a hosted run can be reproduced with the same model
  version.

### 6.5 Candidate 3: Sunbird translate NLLB 1.3B SALT

**Exact identifier and snapshot**

- `Sunbird/translate-nllb-1.3b-salt`.
- Revision `34b3e206b5cf6d29e81a9ca53932b0afc2134894`.
- Last modified 2024-11-06.
- Gated automatic.
- Base model: `facebook/nllb-200-1.3B`.
- Parameters: 1,370,638,336. Verified from safetensors metadata.
- Weight file sizes: 4,999,863,872 bytes plus 482,809,696 bytes, about
  5.48 GB total, consistent with FP32.

**Evidence of Luganda support**

- Source claim: the card's language table explicitly lists `lug`.
- Source claim: BLEU 41.978 for Luganda to English and 30.359 for English
  to Luganda on `salt-dev`.
- The card was gated during this review, so the table and scores were not
  re-read. They are recorded as source claims from the earlier review.

**Model and dataset licensing constraints**

- No licence is stated on the model card. Verified: the model API has no
  licence field.
- The base model `facebook/nllb-200-1.3B` is CC BY-NC 4.0.
- The derivative's terms are unresolved. It is likely constrained by the
  base model's non-commercial terms, but that is an inference, not a
  confirmed licence statement.
- The training data is SALT, which is CC BY-SA 4.0 and gated. The
  interaction between the base model's non-commercial terms and SALT's
  share-alike terms is unresolved.
- `salt-dev` is both a reported evaluation set and a likely training or
  development resource. Contamination is plausible and must be checked.

**Access requirements**

- Gated Hugging Face access.
- Local use requires PyTorch, Transformers, and the NLLB tokenizer.
- Quantisation is advisable for the 8 GB machine.

**Estimated local memory**

- FP32 weights: about 5.48 GB.
- 8-bit weights: about 1.4 GB.
- 4-bit weights: about 0.7 GB.
- Runtime and tokenizer: about 1 to 2 GB, estimate.
- Total at 8-bit: about 2.5 to 3.5 GB, estimate. Plausible on 8 GB.
- FP32 may fit only with little headroom and is not recommended.

**Local feasibility**

Plausible with 8-bit or 4-bit quantisation. CPU inference will be slower
than a GPU but is workable for a small translation probe. The same
Windows quantisation caveat as Candidate 1 applies.

**Paid service**

Not required for local quantised inference. Hosted inference would
require approval and may be constrained by the missing licence.

**Known limitations**

- Translation only. It cannot be scored on the nine conversational
  categories.
- No stated licence, and a non-commercial base model.
- Gated access.
- Self-reported `salt-dev` scores may be in-domain and contaminated.
- No independent Luganda evaluation.
- The reported scores do not establish performance on everyday or
  colloquial text.

**Evidence still needed before selection**

- A written licence clarification from the publisher, or a legal
  determination that the base model's CC BY-NC 4.0 terms govern.
- Confirmation of the training and evaluation split relationship.
- An independent translation evaluation on a non-SALT, non-FLORES set.
- Confirmation that gated access will be granted.

### 6.6 Candidate 4: OPUS-MT English-Luganda pair

**Exact identifiers and snapshots**

- `Helsinki-NLP/opus-mt-en-lg`, revision
  `f83e1d2ddaee499d863e1ae66f7970cd42f33286`, last modified 2023-08-16.
- `Helsinki-NLP/opus-mt-lg-en`, revision
  `fd3b22e05f31219b7101ce37c6bc4e7e52b5dcc2`, last modified 2023-08-16.
- Both public, not gated.
- Both are Marian models, licence Apache-2.0. Verified.
- Each weight file is 302,742,201 bytes, about 303 MB. Both directions
  together are about 606 MB.

**Evidence of Luganda support**

- Verified: the `opus-mt-en-lg` card declares target language `lg`;
  `opus-mt-lg-en` is the reverse pair.
- Source claim: the en-lg card reports BLEU 30.4 and chrF 0.543 on
  JW300.en.lg, and BLEU 5.7 and chrF 0.386 on Tatoeba.en.lg.
- The large gap between JW300 and Tatoeba is a warning: the model may
  perform much better on JW300-style text than on everyday sentences.

**Model and dataset licensing constraints**

- The model weights are Apache-2.0. Verified.
- The model is an OPUS-MT model, and the card reports JW300 and Tatoeba
  test sets. The training-data provenance, including whether JW300 was
  used for training, is not established by the model licence. A
  data-provenance review is still needed if the model is used for
  anything beyond internal evaluation.
- No non-commercial restriction is stated on the model card.

**Access requirements**

- Public Hugging Face download.
- Local use requires PyTorch or a compatible Marian runtime and the
  SentencePiece models shipped with each repository.
- No account or gating.

**Estimated local memory**

- Each direction: about 303 MB FP32.
- Both directions: about 606 MB.
- Runtime and tokenizer: about 1 GB total, estimate.
- This is comfortably within 8 GB.

**Local feasibility**

Yes. CPU inference should be practical for a small translation probe.
This is the lowest-risk local candidate in the shortlist.

**Paid service**

Not required.

**Known limitations**

- Translation only. It cannot be scored on the nine conversational
  categories.
- Older models, last modified in 2023.
- The Tatoeba score is low, which suggests weak everyday-domain
  performance.
- JW300 provenance and quality are not established by the model licence.
- SentencePiece tokenisation may handle Luganda morphology poorly.
- No conversational or instruction-following ability.

**Evidence still needed before selection**

- An independent evaluation on a held-out Luganda set that is not JW300
  or Tatoeba.
- A check of the training-data provenance for JW300 and the other OPUS
  sources.
- A tokenisation and fertility check on Luganda text.
- Confirmation that the model handles the orthography the reviewers
  expect.

### 6.7 Published claims versus independent measurements

No independent measurement was made in this task. The following are
source claims:

- Luganda Gemma: BLEU 13.85, chrF++ 46.59, eval size 100, trained on SALT.
- Sunflower-14B: 31 Ugandan languages; average chrF and BLEU across 31
  languages; no Luganda-only breakdown.
- Sunbird translate NLLB: BLEU 41.978 and 30.359 on `salt-dev`.
- OPUS-MT: BLEU 30.4 on JW300 and 5.7 on Tatoeba for en-lg.
- Kimera: BLEU 21.28 and 17.47, with conflicting directions.

Verified facts are limited to identifiers, revisions, licences, gating,
declared languages, parameter counts, file sizes, and the existence of
the reported evaluation files. No score has been reproduced.

### 6.8 Decision D-005

The shortlist does not select an architecture, parameter count, or
training strategy. It is an evaluation plan only. D-005 remains open.

---

## 7. Task D: Phase 1 readiness checklist

This checklist must be complete before the first reported baseline
evaluation. Status is as of 2026-10-20. "Blocked" means work cannot
proceed without a director decision.

| # | Requirement | Evidence required | Owner | Status |
|---|---|---|---|---|
| 1 | Approved benchmark specification | Signed approval naming the version, approver, and date | Project director | Not started; draft in section 5 |
| 2 | Reviewed and approved prompts | Native-reviewed item file, ambiguity notes, item hash, director approval | DeepSeek and native reviewers | Not started; no prompts written |
| 3 | Candidate model approval | Approved shortlist with revisions, licences, access path, and track | Project director | Not started; shortlist in section 6 |
| 4 | Evaluation budget approval | Local compute cost, API cost cap, reviewer compensation, and approval reference | Project director | Not started; no budget proposed |
| 5 | Required access and software | Gated-access approvals, Python environment, Transformers, PEFT, quantisation runtime, disk space | DeepSeek | Not started |
| 6 | Native-speaker evaluation arrangements | Named panel, consent, rate, schedule, adjudication plan, calibration plan | Project director and native reviewers | Not started |
| 7 | Raw response storage and reproducibility | Run schema, storage path, item hash, model revisions, raw response files, backup | DeepSeek | Not started; schema proposed |
| 8 | Evaluation protocol and scoring | Approved rubric anchors, applicability matrix, agreement statistic, adjudication rule | Project director and native reviewers | Not started; draft in section 5 |
| 9 | Legal review of data used | Licence review for SALT, Wikipedia, FLORES, MAFAND, and any model training data | Project director and legal reviewer | Not started |
| 10 | Contamination review | Item provenance, overlap check, known training-data review, SALT-specific check | DeepSeek | Not started |
| 11 | Data governance records | Entries in `data/README.md` or a linked record for any dataset acquired or used; considered sources are recorded in section 4 | DeepSeek | Not started; no data acquired |
| 12 | Pilot run | A non-reported smoke test on 3 to 5 items to validate the pipeline | DeepSeek | Not started |
| 13 | Reporting template | Experiment log entry and report template with measured and inferred fields separated | DeepSeek | Not started |
| 14 | Stop conditions | Rules for licence breach, harmful output, data leak, or API cost overrun | Project director | Not started |

The first reported baseline must not start until items 1 to 10 and item 12
are complete. Items 11, 13, and 14 should be complete before any public
report.

---

## 8. Task E: Phase 1 exit-criteria mapping

The criteria are quoted from `docs/ROADMAP.md` Phase 1.

### 8.1 Criterion 1: Baseline behavior of existing models documented

- **Required evidence:** a baseline evaluation report with per-model
  results on the approved benchmark, plus recorded settings and raw
  responses.
- **Current status:** not met. No model was run, with or without payment.
- **Remaining work:** approve the benchmark and the shortlist, secure
  access and budget, complete native review, then run the baseline.
- **Human approval required:** yes. The director must approve the model
  list, gated access, non-commercial use, and any spend. Native speakers
  are required for language-quality scores.
- **Evidence that would close it:** a signed-off report, run logs, and
  raw response files.

### 8.2 Criterion 2: Benchmark specification reviewed and approved

- **Required evidence:** an approved specification with the item schema,
  category allocation, rubric scale, applicability matrix,
  native-review procedure, contamination controls, and an approval note.
- **Current status:** not met. `docs/EVALUATION_PLAN.md` is a policy
  document, and section 5 here is an unapproved draft.
- **Remaining work:** review the draft, settle the allocation and scale,
  obtain native input on orthography and register, and obtain director
  approval.
- **Human approval required:** yes.
- **Evidence that would close it:** an approval record naming the
  approver, date, and benchmark version.

### 8.3 Criterion 3: Candidate data sources identified with licensing noted

- **Required evidence:** an inventory of candidate sources with licence,
  access method, Luganda evidence, provenance, and quality risks.
- **Current status:** partially met. Section 4 is that inventory, but
  several questions remain unresolved: Kimera's upstream rights,
  MAFAND's non-commercial and news provenance, SALT's gated terms and
  speaker consent, and the Wikipedia snapshot choice.
- **Remaining work:** resolve each licensing question, mark approved and
  rejected candidates, and obtain director approval before acquisition.
  Acquisition itself belongs to Phase 2.
- **Human approval required:** yes, for acquisition and for any
  non-commercial or otherwise restricted source.
- **Evidence that would close it:** a licence decision per candidate and
  an approval record.

### 8.4 Phase status

Phase 1 must not be marked complete until all three criteria have evidence
and approval. As of 2026-10-20, none is fully closed. Phase 1 is in
progress, not complete.

---

## 9. Decisions requested from the project director

1. Approve, amend, or reject the proposed benchmark specification in
   section 5, including the draft category allocation.
2. Decide whether the optional translation probe is in scope. If not,
   remove candidates 3 and 4 from the shortlist.
3. Approve, amend, or reject the four-model shortlist, including gated
   access and any non-commercial use.
4. Confirm whether the project is non-commercial for the purposes of
   CC BY-NC 4.0.
5. Approve a budget for native-speaker review and, if needed, hosted
   inference. No rate or cap is proposed here.
6. Name a legal reviewer for the share-alike, non-commercial, and
   third-party provenance questions.
7. Decide whether `docs/ROADMAP.md` and `README.md` status lines should
   be updated now that Phase 1 work has started.
8. Keep D-005 open until baseline and tokenizer evidence exists.

---

## 10. Remaining uncertainties

- No Luganda conversational corpus was found. All verified parallel
  resources are sentence-level and mostly translation or encyclopedic.
- The Luganda-only row count in SALT is not published in the metadata
  reviewed.
- Kimera's upstream rights and alignment quality are unresolved.
- MAFAND's news provenance and the project's commercial status are
  unresolved.
- SALT's gated terms and speaker consent are unresolved.
- The Wikipedia mirror and the live dump are different snapshots and
  licence versions.
- FLORES-200, FLORES+, and the Hugging Face revision are different
  snapshots, and the FLORES+ metadata does not identify a licence.
- The Sunflower card could not be read without authentication in this
  revision; its Luganda-specific scores are unverified.
- The Sunbird translation card could not be read without authentication
  in this revision; its Luganda scores are unverified.
- Local memory estimates are arithmetic, not measured. Windows 4-bit
  inference is not yet tested.
- No native speaker has been consulted, and no reviewer panel exists.
- No legal opinion has been obtained.
- The benchmark allocation, weights, and orthography standard are not
  fixed.

---

## 11. Recommended next action

The project director should review this document and choose one of:

- approve the benchmark draft, the four-model shortlist, and the
  translation-probe decision, so licensing, access, and prompt authoring
  can begin; or
- amend them before any further work.

Until approval, the safe next step is documentation and review only:
resolve the licensing questions, confirm native-speaker availability and
budget, and keep D-005 open. No dataset should be acquired, no paid API
should be called, and no model should be run as a reported baseline
before approval.

---

## 12. Files changed and tests

### 12.1 Files changed by this task

- `docs/PHASE-1-RESEARCH.md`: rewritten as the Phase 1 deliverable.

No other file was changed by this task. `docs/ROADMAP.md`,
`docs/DECISIONS.md`, `docs/EVALUATION_PLAN.md`, and `README.md` were read
but not modified. Proposed changes to the roadmap and README status lines
are flagged in section 2.6, not applied.

### 12.2 Tests

No implementation code changed, so no new test was required. The existing
test suite was run as a health check after the documentation change:

```
Ran 192 tests in 19.467s
OK
```

The command was `python -m unittest discover -s tests -t .` with
`PYTHONPATH` pointing at `src`. The JSON output containing
`"collector exploded"` in the test log is deliberate test output, not a
real failure. Exit code was 0.

### 12.3 Data and model handling

- No full corpus was downloaded.
- No model weights were downloaded.
- No inference was run.
- No paid API was called.
- Fetched artefacts were metadata, documentation, a loading script,
  licence files, and a 27 KB model evaluation JSON file. No dataset rows
  were downloaded.

---

## 13. References

All URLs were fetched on 2026-10-20 unless stated otherwise. Gated cards
are marked.

- Project documents: `docs/VISION.md`, `docs/ROADMAP.md`,
  `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`,
  `docs/EVALUATION_PLAN.md`, `docs/EXPERIMENT_LOG.md`,
  `data/README.md`, `AGENTS.md`, `README.md`.
- SALT dataset (gated): https://huggingface.co/datasets/Sunbird/salt
- SALT paper: https://openreview.net/pdf?id=BK-z5qzEU-9
- Luganda Wikipedia: https://lg.wikipedia.org
- Luganda Wikipedia dump:
  https://dumps.wikimedia.org/lgwiki/latest/
- Wikipedia Hugging Face mirror:
  https://huggingface.co/datasets/wikimedia/wikipedia
- Kimera corpus:
  https://github.com/kimrichies/English-Luganda-Parallel-corpus
- Kimera paper: https://arxiv.org/abs/2301.02773
- Kimera Bible dataset (gated):
  https://huggingface.co/datasets/kimrichies/English-Luganda_Bible_corpus
- FLORES GitHub: https://github.com/facebookresearch/flores
- FLORES+ GitHub: https://github.com/openlanguagedata/flores
- FLORES dataset (gated): https://huggingface.co/datasets/facebook/flores
- MAFAND-MT: https://huggingface.co/datasets/masakhane/mafand
- MasakhaNER 2.0:
  https://huggingface.co/datasets/masakhane/masakhaner2
- MasakhaPOS:
  https://huggingface.co/datasets/masakhane/masakhapos
- English Wiktionary Luganda lemmas:
  https://en.wiktionary.org/wiki/Category:Luganda_lemmas
- Luganda Wiktionary incubator:
  https://incubator.wikimedia.org/wiki/Wt/lg/Olupapula_Olusooka
- Tatoeba Luganda export:
  https://downloads.tatoeba.org/exports/per_language/lug/
- Tatoeba terms: https://tatoeba.org/en/terms_of_use
- OSCAR 23.01:
  https://huggingface.co/datasets/oscar-corpus/OSCAR-2301
- mC4: https://huggingface.co/datasets/allenai/c4
- CulturaX: https://huggingface.co/datasets/uonlp/CulturaX
- Common Voice: https://github.com/common-voice/common-voice and
  https://huggingface.co/datasets/legacy-datasets/common_voice
- Luganda Gemma 1B IT:
  https://huggingface.co/AmplifiedAccess/Luganda-gemma-1b-it
- Gemma 3 1B IT (gated):
  https://huggingface.co/google/gemma-3-1b-it
- Sunflower-14B (gated):
  https://huggingface.co/Sunbird/Sunflower-14B
- Sunbird translate NLLB 1.3B SALT (gated):
  https://huggingface.co/Sunbird/translate-nllb-1.3b-salt
- OPUS-MT en-lg:
  https://huggingface.co/Helsinki-NLP/opus-mt-en-lg
- OPUS-MT lg-en:
  https://huggingface.co/Helsinki-NLP/opus-mt-lg-en
- NLLB-200 distilled 600M:
  https://huggingface.co/facebook/nllb-200-distilled-600M
- M2M-100 418M:
  https://huggingface.co/facebook/m2m100_418M
- Qwen3-14B: https://huggingface.co/Qwen/Qwen3-14B
- Qwen2.5 7B Instruct:
  https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- Llama 3.2 3B Instruct:
  https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
