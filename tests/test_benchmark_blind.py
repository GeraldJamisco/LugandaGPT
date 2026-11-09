import unittest
from benchmark.blind import make_pairs, tally, PAGE


def rows(model, n=6):
    return {f"I-{i}": {"item_id": f"I-{i}", "category": "c1" if i < 3 else "c2", "prompt": f"p{i}",
                       "expected_behavior": "e", "model": model, "answer": f"{model}-ans-{i}"} for i in range(n)}


class BlindTests(unittest.TestCase):
    def test_pairs_hide_model_and_key_matches(self):
        pairs, key = make_pairs(rows("base"), rows("v0.2"))
        self.assertEqual(len(pairs), 6)
        for p in pairs:
            self.assertNotIn("model", p)
            k = key[p["item_id"]]
            self.assertEqual({k["A"], k["B"]}, {"base", "v0.2"})
            self.assertTrue(p["A"].startswith(k["A"]))
            self.assertTrue(p["B"].startswith(k["B"]))

    def test_deterministic_and_mixed_sides(self):
        p1, k1 = make_pairs(rows("base", 30), rows("v0.2", 30), seed=3)
        p2, k2 = make_pairs(rows("base", 30), rows("v0.2", 30), seed=3)
        self.assertEqual(k1, k2)
        self.assertGreater(len({k["A"] for k in k1.values()}), 1)

    def test_only_common_items(self):
        a = rows("base"); b = rows("v0.2"); del b["I-0"]
        pairs, _ = make_pairs(a, b)
        self.assertEqual(len(pairs), 5)

    def test_tally_counts_by_model(self):
        key = {"I-0": {"A": "base", "B": "v0.2"}, "I-1": {"A": "v0.2", "B": "base"}}
        out = tally(key, [{"item_id": "I-0", "category": "c1", "choice": "B"},
                          {"item_id": "I-1", "category": "c1", "choice": "A"},
                          {"item_id": "I-1", "category": "c1", "choice": ""}])
        self.assertEqual(out, {"c1": {"v0.2": 2}})

    def test_page_has_placeholders(self):
        self.assertIn("__DATA__", PAGE); self.assertIn("__TAG__", PAGE)


if __name__ == "__main__":
    unittest.main()
