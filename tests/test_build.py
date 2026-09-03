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

    def test_every_issue_has_sequential_learning_steps(self) -> None:
        required = {
            "step_no",
            "question",
            "new_fact",
            "legal_refs",
            "answer",
            "explanation",
            "evidence",
            "precedent_refs",
            "accounting_note",
            "next_state",
        }
        for issue in self.data["issues"]:
            steps = issue.get("steps")
            self.assertIsInstance(steps, list, issue["issue_id"])
            self.assertGreaterEqual(len(steps), 2, issue["issue_id"])
            facts = []
            for expected_no, step in enumerate(steps, start=1):
                self.assertTrue(required.issubset(step), issue["issue_id"])
                self.assertEqual(step["step_no"], expected_no, issue["issue_id"])
                for key in ("question", "new_fact", "answer", "explanation", "next_state"):
                    self.assertTrue(str(step[key]).strip(), f"{issue['issue_id']} {key}")
                self.assertIsInstance(step["legal_refs"], list, issue["issue_id"])
                self.assertIsInstance(step["evidence"], list, issue["issue_id"])
                self.assertIsInstance(step["precedent_refs"], list, issue["issue_id"])
                facts.append(step["new_fact"])
            self.assertEqual(len(facts), len(set(facts)), issue["issue_id"])

    def test_reader_is_static_and_uses_question_first_sequence(self) -> None:
        sample = DOCS / "issues" / "NTBA-TAX-LIABILITY-LIFECYCLE-001" / "index.html"
        text = sample.read_text(encoding="utf-8")
        for label in ("오늘의 질문", "새 사실", "관련 조문 보기", "답과 해설", "판례·조사·회계 연결", "사실이 달라지면", "마지막 정리"):
            self.assertIn(label, text)
        self.assertIn('class="issue-step"', text)
        self.assertIn("국가법령정보센터 원문", text)
        self.assertIn("공식 판결문", text)
        self.assertNotIn("법령과 쟁점의 판단 지도", text)
        self.assertNotIn("법적 판단지도", text)
        self.assertNotIn("합성 사례", text)
        self.assertNotIn("결론의 이동", text)
        self.assertNotRegex(text, r"\bR[0-9]+\b")
        self.assertNotIn('class="step-law" open', text)
        sample_issue = next(
            item for item in self.data["issues"] if item["issue_id"] == "NTBA-TAX-LIABILITY-LIFECYCLE-001"
        )
        self.assertEqual(text.count('class="issue-step"'), len(sample_issue["steps"]))
        self.assertNotIn("<script", text)

        visible = text[text.index("<main") :]
        order = [
            visible.index("오늘의 질문"),
            visible.index("새 사실"),
            visible.index("관련 조문 보기"),
            visible.index("답과 해설"),
        ]
        self.assertEqual(order, sorted(order))

    def test_index_keeps_fallback_rows_for_javascript_off(self) -> None:
        index = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertEqual(index.count('class="issue-row"'), 50)
        self.assertIn("검색을 켜지 않아도", index)
        self.assertIn('id="issue-search"', index)
        self.assertIn('id="law-filter"', index)


if __name__ == "__main__":
    unittest.main()
