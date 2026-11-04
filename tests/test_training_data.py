import unittest
from training_data.build import HELDOUT_PATTERN, _msg


class TrainingDataTests(unittest.TestCase):
    def test_heldout_pattern_catches_hours(self):
        self.assertTrue(HELDOUT_PATTERN.search("Ssaawa 1:00pm"))
        self.assertFalse(HELDOUT_PATTERN.search("Ssaawa 11:00am"))

    def test_message_shape(self):
        r = _msg("x", "s", "q", "a")
        self.assertEqual([m["role"] for m in r["messages"]], ["user", "assistant"])


if __name__ == "__main__":
    unittest.main()
