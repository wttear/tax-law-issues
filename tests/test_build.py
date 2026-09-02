from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ALLOWED_HOSTS = {
    "law.go.kr",
    "www.law.go.kr",
    "scourt.go.kr",
    "www.scourt.go.kr",
    "kasb.or.kr",
    "www.kasb.or.kr",
}
URL_RE = re.compile(r'href="(https://[^" ]+)"')


class BuildOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(
            [sys.executable, "scripts/build.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        cls.data = json.loads((ROOT / "content" / "issues.json").read_text(encoding="utf-8"))

    def test_exactly_ten_per_law_and_fifty_total(self) -> None:
        self.assertEqual(len(self.data["issues"]), 50)
        self.assertEqual(len({item["issue_id"] for item in self.data["issues"]}), 50)
        for law in self.data["laws"]:
            self.assertEqual(law["issue_count"], 10)
            self.assertEqual(len(law["issue_ids"]), 10)

    def test_all_issue_pages_and_index_links_exist(self) -> None:
        pages = list((DOCS / "issues").glob("*/index.html"))
        self.assertEqual(len(pages), 50)
        index = (DOCS / "index.html").read_text(encoding="utf-8")
        for issue in self.data["issues"]:
            destination = DOCS / "issues" / issue["issue_id"] / "index.html"
            self.assertTrue(destination.exists(), issue["issue_id"])
            self.assertIn(f'issues/{issue["issue_id"]}/', index)

    def test_page_contract_accessibility_and_sources(self) -> None:
        pages = [DOCS / "index.html", *sorted((DOCS / "issues").glob("*/index.html"))]
        for page_path in pages:
            text = page_path.read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1"), 1, page_path)
            self.assertIn('class="skip-link"', text, page_path)
            self.assertIn("THESIS:", text, page_path)
            self.assertIn("FIRST VIEWPORT:", text, page_path)
            self.assertIn("FINISH: unreviewed and undocumented is unfinished", text, page_path)
            self.assertNotIn("localhost", text.lower(), page_path)
            self.assertNotIn("file://", text.lower(), page_path)
            self.assertNotIn("localStorage", text, page_path)
            self.assertNotIn("55:25:20", text, page_path)
            self.assertNotIn("수업 완료", text, page_path)
            for url in URL_RE.findall(text):
                self.assertEqual(urlsplit(url).hostname in ALLOWED_HOSTS, True, url)

    def test_reader_is_static_and_has_required_sections(self) -> None:
        sample = DOCS / "issues" / "NTBA-TAX-LIABILITY-LIFECYCLE-001" / "index.html"
        text = sample.read_text(encoding="utf-8")
        for anchor in (
            "law-source",
            "beginner",
            "map",
            "example",
            "audit",
            "precedents",
            "sources",
        ):
            self.assertIn(f'id="{anchor}"', text)
        self.assertIn("국가법령정보센터 원문", text)
        self.assertIn("공식 판결문", text)
        self.assertNotIn("<script", text)

    def test_index_keeps_fallback_rows_for_javascript_off(self) -> None:
        index = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertEqual(index.count('class="issue-row"'), 50)
        self.assertIn("검색을 켜지 않아도", index)
        self.assertIn('id="issue-search"', index)
        self.assertIn('id="law-filter"', index)


if __name__ == "__main__":
    unittest.main()
