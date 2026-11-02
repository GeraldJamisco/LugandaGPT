# Sunbird API connection

Runs Sunbird's Sunflower models through their hosted API and collects
English-to-Luganda suggestions for the source records. Code is in
`src/sunbird_api/`, tests in `tests/test_sunbird_api.py`. Decision record:
D-018.

**Status:** Built and unit-tested with a simulated server. No request has been
sent to Sunbird from this repository, so the live response shape, pricing, and
rate limits are unverified.

**Evidence labels:** the endpoint, model names, and request fields below are a
source claim from docs.sunbird.ai, read on 2026-11-02.

## What it does and does not do

- Sends only English text taken from `data/source/pilot-v1/translator_export.csv`
  or a prompt you type. It never reads teacher translations, reviews, user
  accounts, or the Studio database.
- Writes suggestions to `data/machine/sunbird-suggestions.csv`. That folder is
  ignored by Git, every row carries `machine_output=true` and
  `review_status=unreviewed`, and nothing is written into the Studio. Machine
  output is a comparison aid. It is not a submitted translation, a native
  review, or approved training data.
- Keeps Sunflower's answer verbatim apart from trimming whitespace, and
  records the finish reason so truncated answers are visible.

## Setup

1. Register at https://api.sunbird.ai/register and open the tokens page at
   https://api.sunbird.ai/keys to get an access token. Registration through
   `/auth/register` and `/auth/token` also works (documented at docs.sunbird.ai).
2. Put the token in an environment variable. Do not paste it into chat, code,
   a config file, or a commit.

   PowerShell, current window only:

       $env:SUNBIRD_API_TOKEN = "paste-token-here"
       $env:PYTHONPATH = "src"

   If you also set `SUNBIRD_USERNAME` and `SUNBIRD_PASSWORD`, the client logs in
   again by itself when a token is rejected. The docs disagree on token
   lifetime (one page says 7 days, another says no expiry), so this avoids
   surprises on long runs.
3. Verify the token without generating any text:

       python -m sunbird_api check

## Commands

Count the work first. This sends nothing and needs no token:

    python -m sunbird_api translate-source --dry-run

At the 2026-11-02 snapshot that reports 340 tasks and 368 requests for all 124
source records. Fields translated per item, and the Studio field each one is
meant for:

| Suggestion field | Studio field to compare against |
|---|---|
| `source_context` | `source_context_lg` |
| `prior_turns` (one request per turn) | `prior_turns_lg` |
| `source_prompt` | `source_prompt_lg` |
| `reference_answer` | `final_assistant_response_lg` |

Run a small batch, then more:

    python -m sunbird_api translate-source --limit 5
    python -m sunbird_api translate-source --ids E-001,P-001
    python -m sunbird_api translate-source --max-requests 400

Other commands:

    python -m sunbird_api chat "Translate from English to Luganda: Good morning"
    python -m sunbird_api chat "Muli mutya?" --model sunflower-9b --system "You are a helpful assistant."

Runs resume: items already in the output file are skipped, and each finished
task is saved immediately, so a crash or a stop loses nothing.

## Spending guard

Sunbird publishes no price or rate limit in the documentation reviewed. Every
run is therefore capped at 25 requests unless you pass `--max-requests`. The
run stops cleanly at the cap and reports how many tasks remain. A rate-limit
or server error is retried up to three times with backoff (it honours
`Retry-After`). Any other API error stops the run.

Every request appends one line to `reports/sunbird/usage-ledger.jsonl`:
timestamp, model, purpose, outcome, token counts, latency, and a SHA-256 of the
prompt. It holds no prompt text and no token, so it is safe to commit. Check
Sunbird's account dashboard for the real charges before raising the cap.

## Limits to keep in mind

- **Hosted model versus pinned weights.** The API names `sunflower-9b` and
  `sunflower-14b`. Nothing confirms that `sunflower-14b` is the same revision
  as the Hugging Face weights pinned in `docs/PHASE-1-RESEARCH.md` 6.4. Every
  response's `model` field is stored, and a baseline measured through the API
  is a baseline of the hosted service until that is confirmed.
- **Terms.** Data-retention terms and permission to use the API for benchmarking
  are unchecked. Only project-authored English source text is sent.
- **Quality.** Sunflower can produce fluent but wrong Luganda, and its own
  documentation says translation quality varies by language. Native speakers
  decide what is correct.
- **Licence.** Sunbird's separate NLLB translation endpoint is not used here. Its
  base model is CC BY-NC 4.0, which matters if output ever feeds training data.
- **Studio.** Showing suggestions inside the Studio would change D-010 and could
  anchor translators and reviewers. It is not done.
