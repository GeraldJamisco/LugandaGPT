# Luganda style rules agreed by the native group

Source: the native group (code Group-1), 2026-11-03. These rules apply to all
project-written Luganda: training data, benchmark items, and generated examples.
Evidence label: owner-reported group decisions. The group, not Claude, is the authority.

## Spelling

| Use | Not | Reason given |
|---|---|---|
| ssaawa | saawa | "saawa" means the clock; "ssaawa" means the hours |
| ez'emisana | ezemisana | "emisana" means during the day; use the apostrophe form in time phrases |
| kkumi na bbiri | kkumi nabbiri, kuminabbiri | agreed standard for twelve |
| kkumi | kumi | agreed standard for ten |

| ez'okumakya | ezokumakya | decided 2026-11-03 |
| ez'ekiro | ezekiro | decided 2026-11-03 |
| eza kawungeezi | ezakawungeezi | decided 2026-11-03 |

Singular hour forms (ssaawa emu) are normalised to ey'okumakya and eya kawungeezi.
Other variants (for example eze kawungeezi, ez'olweggulo) are left exactly as written.

## Hours

Luganda counts hours from 7. The hour number is (clock hour minus 6), wrapping
at 12. Part-of-day words: ez'okumakya (morning, also 4 to 6am), ez'emisana
(afternoon), eza kawungeezi (evening), ez'ekiro (night). The singular hour
"emu" takes ey' or eya: ssaawa emu ey'okumakya, ssaawa emu eya kawungeezi.
3am and 4am can take either ez'ekiro or ez'okumakya. 4pm can be ez'emisana or
eza kawungeezi (both accepted).

## Days

- After "on" (ku) the day is Lwo-: ku Lwokuna.
- When stating which day it is, the day is Lwa-: Leero Lwakutaano.
- Sunday is Ssande. Monday is Mmande or Bbalaza.
- Yesterday is jjo or eggulo. Tomorrow is enkya. Today is leero (Lwaleero also occurs).

## Notes

- "Ssaawa mmeka?" asks the time. "Ebulayo essaawa mmeka?" asks how many hours.
- Benchmark prompts EVERYDAY-003 and EVERYDAY-007 were updated to the Lwa- rule on
  2026-11-03 (Leero Lwakubiri, Jjo lwabade Lwakutaano).

- Asking the English time of a Luganda hour: "Ssaawa eyo mu Luzungu zibeera mmeka?" (group decision 2026-11-10; not "ziba mmeka").
