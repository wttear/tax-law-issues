import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { getCatalog, getIssue, getLaws, mergeLearningNotes, validateContentSnapshot } from "../lib/content";

test("catalog lists its published laws and issues", () => {
  const catalog = getCatalog();
  assert.ok(catalog.issues.length > 0);
  assert.ok(getLaws().length > 0);
  assert.equal(
    catalog.issues.length,
    getLaws().reduce((total, law) => total + law.issue_count, 0),
  );
  for (const law of getLaws()) {
    assert.ok(catalog.issues.some((issue) => issue.law_code === law.law_code));
  }
});

test("content validation accepts a law with one complete note and one direct question", () => {
  assert.doesNotThrow(() =>
    validateContentSnapshot(
      {
        schema_version: 2,
        generated_as_of: "2026-09-06",
        source_repository: "test",
        laws: [{ law_code: "TEST", law_name: "테스트법" }],
        issues: [
          {
            issue_id: "TEST-DIRECT-001",
            law_code: "TEST",
            law_name: "테스트법",
            position: 1,
            title: "개별 판단을 배우는 노트",
            canonical_title: "개별 판단을 배우는 노트",
            level: "beginner",
            core_question: "갑이 지급한 비용을 올해 비용으로 처리할 수 있을까?",
            article_ids: ["TEST-1"],
            precedent_ids: [],
            case_facts: "학습용 사례에서 갑은 업무와 관련된 용역대금 5,000,000원을 지급했다.",
            question_blocks: [
              {
                question: "갑이 지급한 5,000,000원은 올해 비용으로 인정될까?",
                answer: "사례에서 필요한 요건이 모두 확인되면 비용으로 인정할 수 있다.",
                explanation: "지급 사실만으로는 충분하지 않으므로 용역의 실제 제공과 업무 관련성을 함께 확인한다.",
                legal_refs: ["테스트법 제1조"],
                article_ids: ["TEST-1"],
              },
            ],
          },
        ],
      },
      [
        {
          article_id: "TEST-1",
          law_code: "TEST",
          article_number: "제1조",
          title: "테스트 규정",
          official_url: "https://www.law.go.kr/법령/테스트법/제1조",
          source_url: "https://www.law.go.kr/법령/테스트법",
          source_as_of: "2026-09-06",
          content_status: "source_only",
          versions: [],
        },
      ],
      [],
    ),
  );
});

test("issue lookup returns the representative issue", () => {
  const issue = getIssue("NTBA-TAX-LIABILITY-LIFECYCLE-001");
  assert.ok(issue);
  assert.equal(issue.title, "법인세는 언제 생기고, 언제 끝날까?");
  assert.ok(issue.case_facts.length > 0);
  assert.ok(issue.question_blocks.length >= 2);
  assert.equal(getIssue("does-not-exist"), undefined);
});

test("a rewritten note replaces legacy template questions with its reviewed learning copy", () => {
  const issue = getIssue("NTBA-LEGALITY-001");
  assert.ok(issue);
  assert.equal(issue.core_question, "내부지침만으로 지원금에 세금을 매길 수 있을까?");
  assert.equal(issue.question_blocks.length, 2);
  assert.equal(issue.question_blocks[0].question, "내부지침만으로 지원금에 세금을 매길 수 있을까?");
  assert.equal(issue.audit_application.length, 0);
  assert.equal(issue.accounting_tax_adjustment.length, 0);
  assert.equal(issue.practical_application?.title, "처분안을 받을 때 먼저 확인할 것");
});

test("a directly relevant precedent is connected only where it adds a concrete boundary", () => {
  const issue = getIssue("NTBA-LIMITATION-001");
  assert.ok(issue);
  assert.deepEqual(issue.precedent_ids, ["SC-2021DU33371-2021-12-30"]);
});

test("income-tax notes connect precedents that answer their specific judgment boundary", () => {
  const residency = getIssue("ITA-RESIDENCY-SOURCE-001");
  const classification = getIssue("ITA-INCOME-CLASSIFICATION-001");
  const jointBusiness = getIssue("ITA-JOINT-BUSINESS-001");
  const books = getIssue("ITA-BOOKS-ESTIMATION-001");

  assert.ok(residency);
  assert.ok(classification);
  assert.ok(jointBusiness);
  assert.ok(books);
  assert.deepEqual(residency.precedent_ids, ["SC-2016DU37584-2016-08-17"]);
  assert.deepEqual(classification.precedent_ids, ["SAC-2008GUHAP14548-2008-11-26"]);
  assert.deepEqual(jointBusiness.precedent_ids, ["SC-1996NU8192-1997-09-26"]);
  assert.deepEqual(books.precedent_ids, ["SC-1996NU8192-1997-09-26"]);
});

test("every published issue has a reviewed learning-note override", () => {
  const source = JSON.parse(readFileSync("content/learning-notes.json", "utf8")) as { notes: Array<{ issue_id: string }> };
  const publishedIds = getCatalog().issues.map((issue) => issue.issue_id).sort();
  const rewrittenIds = source.notes.map((note) => note.issue_id).sort();

  assert.deepEqual(rewrittenIds, publishedIds);
});

test("a missing reviewed note cannot silently fall back to legacy learning copy", () => {
  assert.throws(
    () =>
      mergeLearningNotes(
        {
          issues: [{ issue_id: "TEST-MISSING-001" }],
        },
        { notes: [] },
      ),
    /missing reviewed note TEST-MISSING-001/,
  );
});
