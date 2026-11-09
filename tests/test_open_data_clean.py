import json
import tempfile
import unittest
from pathlib import Path

from open_data.clean import clean_wikitext, paragraphs, write_salt


class CleanTests(unittest.TestCase):
    def test_salt_keeps_only_english_and_luganda_and_separates_splits(self):
        rows = [
            {"split": "train", "id": 1, "eng_source_text": "Hello", "lug_text": " Nkulamusizza  ", "swa_text": "Habari", "ach_text": "x"},
            {"split": "test", "id": 2, "eng_source_text": "Bye", "lug_text": "Weraba", "swa_text": "Kwaheri"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "salt.jsonl"
            src.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            counts = write_salt(src, Path(tmp) / "out")
            train = [json.loads(l) for l in open(Path(tmp) / "out" / "salt-luganda-train.jsonl", encoding="utf-8")]
            held = [json.loads(l) for l in open(Path(tmp) / "out" / "salt-luganda-heldout.jsonl", encoding="utf-8")]
        self.assertEqual(counts, {"train": 1, "heldout": 1})
        self.assertEqual(set(train[0]), {"id", "split", "english", "luganda"})
        self.assertEqual(train[0]["luganda"], "Nkulamusizza")
        self.assertEqual(held[0]["split"], "test")

    def test_wikitext_markup_is_removed(self):
        raw = "'''Kampala''' kye [[kibuga]] ekikulu [[Uganda|eya Uganda]].<ref>x</ref> {{Infobox|a=b}}\n[[File:a.jpg|thumb|cap [[x]]]]\n"
        text = clean_wikitext(raw)
        self.assertIn("Kampala kye kibuga ekikulu eya Uganda.", text)
        self.assertNotIn("Infobox", text)
        self.assertNotIn("a.jpg", text)

    def test_short_list_heading_and_english_lines_are_dropped(self):
        luganda = "Kampala kye kibuga ekikulu ekya Uganda era kirimu abantu bangi nnyo mu ggwanga lyonna lyonna."
        english = "The city is the capital of the country and it was the first in the region with the people."
        text = "== Omutwe ==\n* ekintu\nbufunze\n" + luganda + "\n" + english
        self.assertEqual(list(paragraphs(text)), [luganda])


if __name__ == "__main__":
    unittest.main()
