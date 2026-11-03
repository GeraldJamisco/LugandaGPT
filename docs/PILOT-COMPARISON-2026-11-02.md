# Pilot comparison: native Luganda vs Sunflower-14B via API (2026-11-02)

Evidence label: Pilot diagnostic. Not a benchmark result. Not a basis for any
public or investor claim.

## Method (as it happened)

- Source: 14 machine translations in `data/machine/sunbird-suggestions.csv`
  (items E-001 to E-005, model `sunflower-14b`, temperature 0.3).
- Tool: `tools/luganda-compare/index.html`. Each item: native Luganda typed
  first, Sunbird output revealed after, then adequacy and fluency 1 to 5 and
  error tags.
- Four native-speaking reviewers took part and agreed a conclusion together.
  This was a group discussion, not four independent blind ratings, so it does
  not meet the benchmark spec (independent blind review). The export
  (`data/machine/sunbird-comparison-2026-11-02.csv`) records one set of
  ratings and no reviewer code.

## Counts recorded (14 items)

| Rating | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Adequacy | 1 | 6 | 4 | 3 | 0 |
| Fluency | 2 | 8 | 0 | 4 | 0 |

## Error patterns reported by the reviewers

1. Clock time: Luganda counts hours from morning (9am is "ssaawa ssatu").
   Sunbird used the English number ("mwenda"). Seen in E-001, E-003, E-005.
2. Days of the week mixed up or changed (E-002).
3. "Workshop" left as English or rendered poorly; reviewers use "omwoleso".
   E-003 question was not understandable to a native speaker.
4. Vocabulary gaps (for example "summary", E-002).
5. Same English term rendered differently within one item (E-001, E-003).

## Limits

- 14 outputs from 5 scenarios, one model setting, one run.
- Reviewers saw their own draft before Sunbird's, and discussed as a group.
- E-001 source_prompt: identical text from both sides but rated 2/2 with no
  errors. To be re-checked.
- Corrected Luganda is candidate text only until it passes the Translation
  Studio with consent and review.

## Use going forward

- Target areas for benchmark items (needs owner approval under O-02): clock
  time, days and dates, event and workshop vocabulary, term consistency,
  instruction summaries.
- Re-run a larger sample with independent blind review before any claim.

## Round 2: Sunflower-14B on 7 draft benchmark items (2026-11-03)

Evidence label: Pilot diagnostic. Not a benchmark result. Single run,
temperature 0.3, one group review (export file code in the CSV: T3; file name
says GROUP-1). Items from `data/benchmark/drafts/pilot-weak-areas-0.2-draft.jsonl`.

| Item | Adequacy / Fluency (group) | Note |
|---|---|---|
| EVERYDAY-001 | 1 / 1 | Said "ssaawa ssatu ez'okumakya" is 9 at night ("mwenda ez'ekiro"). Wrong. |
| EVERYDAY-002 | 5 / 5 | Correct (1:00 PM). |
| EVERYDAY-003 | 5 / 5 | Correct (Lwokusatu). |
| FORMAL-001 | 5 / 5 | Inserted a date ("15 Ogwomusanvu") that is not in the prompt. To re-check. |
| INSTRUCTION-001 | 5 / 5 | Gave "ssaawa ttaano ez'emisana" for 1pm. Earlier reference by T2 says "musanvu". To re-check. |
| EXPLANATION-001 | 3 / 3 | Grammar. |
| CODESWITCH-001 | 3 / 3 | Wrong email title, meaning changed. |

Findings: the clock-time weakness reproduced on the first item, but two other
time and day items passed, so Sunflower is inconsistent, not uniformly wrong.
Two 5/5 ratings conflict with other evidence and need a second look.
Limits: 7 items, one run, one group, no reference answers for most items,
group ratings (no agreement data).

## Round 3: Sunflower-14B on 23 more draft items (2026-11-03)

Evidence label: Pilot diagnostic. Not a benchmark result. Single run (23
requests, about 10,200 tokens), one group review (code Group-1), items from
`pilot-set-2-0.4-draft.jsonl`, answers in `data/machine/sunflower-benchmark-set-2.csv`,
ratings in `data/machine/sunbird-comparison-2026-11-03.group-1.csv`.

Group ratings (23 items). Adequacy 1/2/3/4/5: 4/3/3/1/12. Fluency 1/2/3/4/5: 6/2/3/2/10.
No average is computed.

Findings:
- Time and day items (7 in this set): 2 correct, 5 wrong (hour numbers, the day
  after Lwokuna, yesterday-to-today, an 8am item, a made-up time-zone answer).
- Formal letters and notices mostly rated 5/5, but outputs contain invented
  dates, and one letter has words with no meaning in Luganda (reviewer note).
- Reviewer notes: "ni" in "ye Kampala" is Swahili, not Luganda; "obwire" is not
  a Luganda word; one reply ignored the instruction (CODESWITCH-005).
- Some "own answer" boxes look nearly identical to Sunflower's text (for
  example explanations), so they are not independent references. Do not use
  them as reference answers without a check.
- Two ratings to re-check: FORMAL-002 and FORMAL-004 were 5/5 despite dates
  that were not in the prompt.
