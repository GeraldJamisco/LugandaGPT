import io
import json
import tempfile
import unittest
from pathlib import Path

from open_data import fetch


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FetchTests(unittest.TestCase):
    def test_download_writes_file_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fetch.fetch_wikipedia(opener=lambda req, timeout=None: FakeResponse(b"abc" * 10), out_dir=tmp)
            target = Path(tmp) / "luganda-wikipedia" / "lgwiki-latest-pages-articles.xml.bz2"
            self.assertEqual(target.read_bytes(), b"abc" * 10)
            saved = json.loads(Path(str(target) + ".provenance.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["sha256"], record["sha256"])
            self.assertEqual(saved["approval"], "D-023")
            self.assertEqual(saved["bytes"], 30)
            self.assertIn("CC BY-SA", saved["licence"])

    def test_only_approved_sources_exist(self):
        self.assertEqual(set(fetch.SOURCES), {"luganda-wikipedia", "salt-text"})


if __name__ == "__main__":
    unittest.main()
