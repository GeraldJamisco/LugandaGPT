import unittest

from rule_data.time_days import (HOLDOUT_HOURS, english_time, generate, generate_all, lug_number,
                                 lug_time, lug_time_alt, next_day, stating)
from rule_data.normalize import normalize


class RuleTests(unittest.TestCase):
    def test_group_confirmed_hours(self):
        expected = {7: "ssaawa emu ey'okumakya", 9: "ssaawa ssatu ez'okumakya", 12: "ssaawa mukaaga ez'emisana",
                    13: "ssaawa musanvu ez'emisana", 18: "ssaawa kkumi na bbiri eza kawungeezi",
                    19: "ssaawa emu eya kawungeezi", 21: "ssaawa ssatu ez'ekiro", 0: "ssaawa mukaaga ez'ekiro",
                    6: "ssaawa kkumi na bbiri ez'okumakya"}
        for hour, text in expected.items():
            self.assertEqual(lug_time(hour), text)

    def test_hour_number_cycle(self):
        self.assertEqual([lug_number(h) for h in (7, 18, 19, 6)], [1, 12, 1, 12])

    def test_english_time(self):
        self.assertEqual((english_time(0), english_time(12), english_time(15)), ("12:00am", "12:00pm", "3:00pm"))

    def test_days(self):
        self.assertEqual(next_day("Lwomukaaga"), "Ssande")
        self.assertEqual(next_day("Lwokuna"), "Lwokutaano")

    def test_generation_is_repeatable_and_skips_holdouts(self):
        self.assertEqual(generate(30, seed=2), generate(30, seed=2))
        for hour in HOLDOUT_HOURS:
            word = lug_time(hour)
            self.assertFalse(any(r["question"].startswith(word.capitalize()) for r in generate(200, seed=3)))

    def test_all_facts_are_unique_and_alt_wording_is_kept(self):
        rows = generate_all()
        self.assertEqual(len({r["question"] for r in rows}), len(rows))
        self.assertEqual(lug_time_alt(3), "ssaawa mwenda ez'okumakya")
        self.assertIsNone(lug_time_alt(12))
        alts = [r for r in rows if r["alt_answer"]]
        self.assertEqual(len(alts), 2)

    def test_group_spelling_standards(self):
        self.assertEqual(normalize("saawa kumi nabbiri ezemisana"), "ssaawa kkumi na bbiri ez'emisana")
        self.assertEqual(normalize("Saawa kuminabbiri"), "Ssaawa kkumi na bbiri")
        self.assertEqual(normalize("ssaawa kkumi na bbiri ez'emisana"), "ssaawa kkumi na bbiri ez'emisana")
        self.assertEqual(normalize("ssaawa kumi n'emu"), "ssaawa kkumi n'emu")
        self.assertEqual(normalize("ssaawa ssatu ezokumakya"), "ssaawa ssatu ez'okumakya")
        self.assertEqual(normalize("ssaawa ssatu ezekiro"), "ssaawa ssatu ez'ekiro")
        self.assertEqual(normalize("ssaawa bbiri ezakawungeezi"), "ssaawa bbiri eza kawungeezi")
        self.assertEqual(normalize("ssaawa emu eyokumakya"), "ssaawa emu ey'okumakya")
        self.assertEqual(normalize("eze kawungeezi"), "eze kawungeezi")  # not decided, left alone

    def test_stating_a_day_uses_lwa(self):
        self.assertEqual((stating("Lwokuna"), stating("Ssande")), ("Lwakuna", "Ssande"))
        rows = generate_all()
        row = next(r for r in rows if r["kind"] == "yesterday" and "Lwakuna" in r["question"])
        self.assertEqual(row["answer"], "Leero Lwakutaano.")


if __name__ == "__main__":
    unittest.main()
