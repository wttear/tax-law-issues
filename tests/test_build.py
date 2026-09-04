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
            for banned in (
                "앞서 확인한 사실",
                "추가 사실",
                "다음 단계에서 관련 판단을 더 구체화한다",
                "완전 안내",
                "부분 안내형",
                "독립 해결형",
                "VAT 실무 bridge",
                "책임선",
                "학습값",
                "분개를 억지로 만들지 않고",
                "교육문제는",
                "보여 줘야",
                "학습상",
                "학습 기준",
                "학습 원천징수율",
                "교육금액",
                "학습하게 한다",
                "학습하므로",
                "어떤 순서로 가르나요",
            ):
                self.assertNotIn(banned, text, page_path)
            for url in URL_RE.findall(text):
                self.assertEqual(urlsplit(url).hostname in ALLOWED_HOSTS, True, url)

    def test_every_issue_has_case_first_question_blocks(self) -> None:
        required = {
            "block_no",
            "judgment_type",
            "question",
            "fact_scope",
            "legal_refs",
            "answer",
            "explanation",
            "evidence",
            "precedent_refs",
            "accounting_note",
        }
        for issue in self.data["issues"]:
            self.assertTrue(str(issue.get("case_facts", "")).strip(), issue["issue_id"])
            blocks = issue.get("question_blocks")
            self.assertIsInstance(blocks, list, issue["issue_id"])
            self.assertGreaterEqual(len(blocks), 2, issue["issue_id"])
            for expected_no, block in enumerate(blocks, start=1):
                self.assertTrue(required.issubset(block), issue["issue_id"])
                self.assertEqual(block["block_no"], expected_no, issue["issue_id"])
                self.assertIn(
                    block["judgment_type"],
                    {"rule", "calculation", "evidence", "change"},
                    issue["issue_id"],
                )
                for key in ("question", "fact_scope", "answer", "explanation"):
                    self.assertTrue(str(block[key]).strip(), f"{issue['issue_id']} {key}")
                self.assertGreaterEqual(len(str(block["answer"]).strip()), 8, issue["issue_id"])
                self.assertNotEqual(block["answer"], block["legal_refs"][0] if block["legal_refs"] else None)
                self.assertIsInstance(block["legal_refs"], list, issue["issue_id"])
                self.assertIsInstance(block["evidence"], list, issue["issue_id"])
                self.assertIsInstance(block["precedent_refs"], list, issue["issue_id"])
            self.assertTrue(all("new_fact" not in block for block in blocks), issue["issue_id"])
            self.assertTrue(all("next_state" not in block for block in blocks), issue["issue_id"])

    def test_learner_copy_has_no_authoring_guidance(self) -> None:
        banned = (
            "앞서 확인한 사실",
            "추가 사실",
            "다음 단계에서 관련 판단을 더 구체화한다",
            "완전 안내",
            "부분 안내형",
            "독립 해결형",
            "VAT 실무 bridge",
            "책임선",
            "학습값",
            "분개를 억지로 만들지 않고",
            "교육문제는",
            "보여 줘야",
            "학습상",
            "학습 기준",
            "학습 원천징수율",
            "교육금액",
            "학습하게 한다",
            "학습하므로",
            "어떤 순서로 가르나요",
            "55:25:20",
        )
        for issue in self.data["issues"]:
            payload = json.dumps(issue, ensure_ascii=False)
            for phrase in banned:
                self.assertNotIn(phrase, payload, issue["issue_id"])
            questions = [block["question"] for block in issue["question_blocks"]]
            self.assertEqual(len(questions), len(set(questions)), issue["issue_id"])
            for question in questions:
                self.assertTrue(question.endswith("?"), question)
                self.assertNotIn("??", question, question)

    def test_question_and_answer_share_a_concrete_subject(self) -> None:
        vague = (
            "어떤 순서",
            "어떻게 설명",
            "어떻게 연결할",
            "무엇을 고를",
            "어떤 자료로 결론낼",
        )
        for issue in self.data["issues"]:
            for block in issue["question_blocks"]:
                question = block["question"]
                answer = block["answer"]
                for phrase in vague:
                    self.assertNotIn(phrase, question, f"{issue['issue_id']} {question}")
                suffixes = (
                    "으로써", "으로", "에서", "에게", "부터", "까지", "보다", "처럼",
                    "만큼", "로", "은", "는", "이", "가", "을", "를", "에", "도", "만", "와", "과",
                )

                def stems(text: str) -> set[str]:
                    result = set()
                    for token in re.findall(r"[가-힣A-Za-z]{2,}|\d[\d,\.]*", text):
                        for suffix in suffixes:
                            if token.endswith(suffix) and len(token) - len(suffix) >= 2:
                                token = token[: -len(suffix)]
                                break
                        result.add(token)
                    return result

                concrete_tokens = stems(question)
                answer_tokens = stems(answer)
                shared = concrete_tokens & answer_tokens
                self.assertGreaterEqual(
                    len(shared),
                    2,
                    f"{issue['issue_id']} Q{block['block_no']}: {question} / {answer}",
                )

    def test_question_wording_is_direct_and_readable(self) -> None:
        for issue in self.data["issues"]:
            for block in issue["question_blocks"]:
                question = block["question"]
                self.assertNotIn("있고·단정하지·않는다", question, issue["issue_id"])
                self.assertNotIn("확인할 원본 자료는", question, issue["issue_id"])
                self.assertNotIn("확인에 필요한 원본 자료는", question, issue["issue_id"])
                if block["judgment_type"] == "evidence":
                    self.assertRegex(
                        question,
                        r"(?:어떻게 확인하는가|무엇을 입증하는가|어떻게 입증하는가|어느 부분을 입증하는가)\?$",
                        issue["issue_id"],
                    )

    def test_reader_is_static_and_uses_question_first_sequence(self) -> None:
        sample = DOCS / "issues" / "NTBA-TAX-LIABILITY-LIFECYCLE-001" / "index.html"
        text = sample.read_text(encoding="utf-8")
        for label in ("사실관계", "질문별 판단", "관련 조문 보기", "답과 해설", "판례·조사·회계 연결", "사실이 달라지면", "마지막 정리"):
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
        self.assertEqual(text.count('class="issue-step"'), len(sample_issue["question_blocks"]))
        self.assertEqual(text.count('<div class="case-facts">'), 1)
        self.assertNotIn("<script", text)

        visible = text[text.index("<main") :]
        order = [
            visible.index("사실관계"),
            visible.index("질문별 판단"),
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
