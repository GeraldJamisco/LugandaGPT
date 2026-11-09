"""Luganda clock hours and days, generated from the group-confirmed rules.

Rule (confirmed 2026-11-03, data/rules/rules-check-Group-1-2026-11-03.csv):
Luganda counts hours from 7. The hour number is (clock hour - 6) mod 12, with 0
written as 12. The part-of-day word depends on the clock hour.
"""

import random

NUMBERS = {
    1: "emu", 2: "bbiri", 3: "ssatu", 4: "nnya", 5: "ttaano", 6: "mukaaga",
    7: "musanvu", 8: "munaana", 9: "mwenda", 10: "kkumi",
    11: "kkumi n'emu", 12: "kkumi na bbiri",
}
DAYS = ["Ssande", "Mmande", "Lwokubiri", "Lwokusatu", "Lwokuna", "Lwokutaano", "Lwomukaaga"]
# Group rule (2026-11-03): after "on" (ku) the day is Lwo-; when stating which day it is, Lwa-.
STATING = {"Lwokubiri": "Lwakubiri", "Lwokusatu": "Lwakusatu", "Lwokuna": "Lwakuna",
           "Lwokutaano": "Lwakutaano", "Lwomukaaga": "Lwamukaaga"}


def stating(day):
    return STATING.get(day, day)

# Hours kept out of generated training data so the benchmark can test the skill
# on hours the model has not been taught (see docs/DECISIONS.md D-020).
HOLDOUT_HOURS = frozenset({8, 9, 10, 13, 14})
HOLDOUT_DAY_FACTS = frozenset({("tomorrow", "Lwokubiri"), ("next", "Lwokuna"), ("yesterday", "Lwokutaano")})


def lug_number(hour24):
    n = (hour24 - 6) % 12
    return n if n else 12


def period_word(hour24):
    if 7 <= hour24 <= 11 or hour24 in (4, 5, 6):
        return "ez'okumakya"
    if 12 <= hour24 <= 16:
        return "ez'emisana"
    if 17 <= hour24 <= 20:
        return "eya kawungeezi" if hour24 == 19 else "eza kawungeezi"
    return "ez'ekiro"  # 21 to 23 and 0 to 3


def lug_time(hour24):
    word = period_word(hour24)
    if lug_number(hour24) == 1 and word.startswith("ez'"):
        word = "ey'" + word[3:]  # "emu" is singular: the group writes ey'okumakya
    return f"ssaawa {NUMBERS[lug_number(hour24)]} {word}"


# Group note (2026-11-03): 3am and 4am can also be said with "ez'okumakya".
ALT_PERIOD = {3: "ez'okumakya", 4: "ez'ekiro"}


def lug_time_alt(hour24):
    """Accepted alternative wording, or None."""
    if hour24 not in ALT_PERIOD:
        return None
    return f"ssaawa {NUMBERS[lug_number(hour24)]} {ALT_PERIOD[hour24]}"


def english_time(hour24):
    h12 = hour24 % 12 or 12
    suffix = "am" if hour24 < 12 else "pm"
    return f"{h12}:00{suffix}"


def next_day(day):
    return DAYS[(DAYS.index(day) + 1) % 7]


def generate(count=36, seed=1):
    rng = random.Random(seed)
    hours = [h for h in range(24) if h not in HOLDOUT_HOURS]
    rows = []
    kinds = ["lug_to_en", "en_to_lug", "next", "yesterday", "tomorrow"]
    i = 0
    while len(rows) < count:
        kind = kinds[i % len(kinds)]
        i += 1
        if kind in ("lug_to_en", "en_to_lug"):
            h = rng.choice(hours)
            if kind == "lug_to_en":
                q = f"{lug_time(h).capitalize()}. Ssaawa eyo mu Luzungu zibeera mmeka?"
                a = f"{lug_time(h).capitalize()} mu Luzungu zibeera {english_time(h)}."
            else:
                q = f"Ssaawa {english_time(h)} mu Luganda eba ssaawa mmeka?"
                a = f"{lug_time(h).capitalize()}."
        else:
            d = rng.choice(DAYS)
            if (kind if kind != "next" else "next", d) in HOLDOUT_DAY_FACTS:
                continue
            nd = next_day(d)
            if kind == "next":
                q = f"Olunaku oluddako {d} lunaku ki?"
                a = f"Olunaku oluddako {d} ye {nd}."
            elif kind == "yesterday":
                q = f"Jjo lwabade {d}. Leero lunaku ki?"
                a = f"Leero {nd}."
            else:
                q = f"Leero {d}. Enkya lujja kuba lunaku ki?"
                a = f"Enkya {nd}."
        rows.append({"kind": kind, "question": q, "answer": a})
    return rows


def generate_all():
    """Every distinct allowed fact once, in a fixed order. No repeats."""
    rows = []
    for h in range(24):
        if h in HOLDOUT_HOURS:
            continue
        alt = lug_time_alt(h)
        rows.append({"kind": "lug_to_en",
                     "question": f"{lug_time(h).capitalize()}. Ssaawa eyo mu Luzungu zibeera mmeka?",
                     "answer": f"{lug_time(h).capitalize()} mu Luzungu zibeera {english_time(h)}.",
                     "alt_answer": ""})
        rows.append({"kind": "en_to_lug",
                     "question": f"Ssaawa {english_time(h)} mu Luganda eba ssaawa mmeka?",
                     "answer": f"{lug_time(h).capitalize()}.",
                     "alt_answer": f"{alt.capitalize()}." if alt else ""})
    for d in DAYS:
        nd = next_day(d)
        if ("next", d) not in HOLDOUT_DAY_FACTS:
            rows.append({"kind": "next", "question": f"Olunaku oluddako {stating(d)} lunaku ki?",
                         "answer": f"Olunaku oluddako {stating(d)} ye {stating(nd)}.", "alt_answer": ""})
        if ("yesterday", d) not in HOLDOUT_DAY_FACTS:
            rows.append({"kind": "yesterday", "question": f"Jjo lwabade {stating(d)}. Leero lunaku ki?",
                         "answer": f"Leero {stating(nd)}.", "alt_answer": ""})
        if ("tomorrow", d) not in HOLDOUT_DAY_FACTS:
            rows.append({"kind": "tomorrow", "question": f"Leero {stating(d)}. Enkya lujja kuba lunaku ki?",
                         "answer": f"Enkya {stating(nd)}.", "alt_answer": ""})
    return rows
