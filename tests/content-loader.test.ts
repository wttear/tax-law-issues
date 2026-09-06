import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { getArticle, getCatalog, getIssue, getLaws, getPrecedent, mergeLearningNotes, validateContentSnapshot } from "../lib/content";

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

test("the curated selection mirrors every published issue without duplicates", () => {
  const selection = JSON.parse(readFileSync("content/issue-selection.json", "utf8")) as {
    laws: Array<{ issue_ids: string[] }>;
  };
  const selectedIds = selection.laws.flatMap((law) => law.issue_ids);
  const publishedIds = getCatalog().issues.map((issue) => issue.issue_id);

  assert.equal(new Set(selectedIds).size, selectedIds.length);
  assert.deepEqual([...selectedIds].sort(), [...publishedIds].sort());
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

test("collection notes use precedents to make priority and setoff dates concrete", () => {
  const priority = getIssue("NCTA-TAX-PRIORITY-001");
  const thirdDebtor = getIssue("NCTA-THIRD-DEBTOR-001");
  const setoffCase = getPrecedent("SC-2011DA45521-2012-02-16");

  assert.ok(priority);
  assert.ok(thirdDebtor);
  assert.ok(setoffCase);
  assert.deepEqual(priority.precedent_ids, ["SC-1997DA12037-1998-09-08"]);
  assert.deepEqual(thirdDebtor.precedent_ids, ["SC-2011DA45521-2012-02-16"]);
  assert.match(thirdDebtor.question_blocks[1].answer, /압류 효력이 생긴 때.*상계/);
  assert.equal(setoffCase.case_number, "2011다45521");
  assert.match(setoffCase.official_source_url, /law\.go\.kr/);
});

test("income-disposition learning separates cash retained by the company from the representative's personal use", () => {
  const issue = getIssue("CTA-INCOME-DISPOSITION-001");

  assert.ok(issue);
  assert.match(issue.question_blocks[0].answer, /70,000,000원.*익금/);
  assert.match(issue.question_blocks[1].question, /법인 계좌에 남은 35,000,000원.*개인 생활비로 쓴 35,000,000원/);
  assert.match(issue.question_blocks[1].answer, /사내유보/);
  assert.match(issue.question_blocks[1].answer, /상여/);
});

test("income-disposition learning cites the source-backed omitted-sales precedent", () => {
  const issue = getIssue("CTA-INCOME-DISPOSITION-001");
  const precedent = getPrecedent("SC-1997NU19151-1999-05-25");

  assert.ok(issue);
  assert.ok(precedent);
  assert.deepEqual(issue.precedent_ids, ["SC-1997NU19151-1999-05-25"]);
  assert.equal(precedent.case_number, "97누19151");
  assert.match(precedent.official_source_url, /law\.go\.kr/);
});

test("related-party pricing learning tests the actual economic consideration at the transaction date", () => {
  const issue = getIssue("CTA-RELATED-PARTY-001");

  assert.ok(issue);
  assert.deepEqual(issue.precedent_ids, ["SC-2017DU35165-2020-12-10"]);
  assert.match(issue.question_blocks[0].answer, /거래 당시/);
  assert.match(issue.question_blocks[1].answer, /100,000,000원/);
  assert.match(issue.question_blocks[1].answer, /실제 부담/);
});

test("a precedent is not attached to an unrelated legal-principle note", () => {
  const issue = getIssue("NTBA-LEGALITY-001");

  assert.ok(issue);
  assert.deepEqual(issue.precedent_ids, []);
});

test("nonbusiness-asset learning calculates the interest adjustment from the stated annual balances", () => {
  const issue = getIssue("CTA-INTEREST-NONBUSINESS-ASSET-001");

  assert.ok(issue);
  assert.match(issue.case_facts, /해당 사업연도 세법상 평균 계산가액은 100,000,000원/);
  assert.match(issue.question_blocks[0].answer, /업무무관자산/);
  assert.match(issue.question_blocks[1].question, /지급이자 25,000,000원 중/);
  assert.match(issue.question_blocks[1].answer, /25,000,000원 × 100,000,000원 ÷ 500,000,000원/);
  assert.match(issue.question_blocks[1].answer, /5,000,000원/);
  assert.match(issue.question_blocks[1].explanation, /적수/);
});

test("construction-contract learning teaches the current work-progress default instead of an obsolete one-year trigger", () => {
  const issue = getIssue("CTA-LONG-TERM-CONTRACT-001");

  assert.ok(issue);
  assert.equal(issue.title, "공사가 아직 끝나지 않았는데, 올해 매출을 잡아야 할까?");
  assert.match(issue.case_facts, /중소기업에 해당하지 않으며/);
  assert.match(issue.question_blocks[0].answer, /작업진행률/);
  assert.match(issue.question_blocks[0].explanation, /계약기간이 1년 이상인지 여부만으로/);
  assert.match(issue.question_blocks[1].answer, /1,200,000,000원/);
  assert.match(issue.question_blocks[1].answer, /1,500,000,000원/);
  assert.match(issue.question_blocks[1].explanation, /계약 당시에 추정한 공사원가/);
});

test("business-income timing learning uses service completion instead of the cash-receipt date", () => {
  const issue = getIssue("ITA-INCOME-TIMING-001");
  const serviceTimingRule = getArticle("ITA-48");

  assert.ok(issue);
  assert.ok(serviceTimingRule);
  assert.equal(issue.title, "설계대금을 다음 해에 받아도, 올해 매출일까?");
  assert.match(issue.case_facts, /2026년 12월 28일에 최종 설계도와 실행도면을 모두 넘겼고/);
  assert.match(issue.question_blocks[0].answer, /2026년 총수입금액/);
  assert.match(issue.question_blocks[0].explanation, /용역의 제공을 완료한 날/);
  assert.match(issue.question_blocks[1].answer, /2027년 매출로 다시 적지 않는다/);
  assert.match(issue.question_blocks[1].explanation, /미수금 11,000,000원/);
  assert.match(serviceTimingRule.versions[0]?.text ?? "", /용역의 제공을 완료한 날/);
});

test("common-input learning separates direct attribution, final allocation, and scheduled-return settlement", () => {
  const issue = getIssue("VAT-COMMON-INPUT-ALLOCATION-001");
  const allocationRule = getArticle("VAT-81");

  assert.ok(issue);
  assert.ok(allocationRule);
  assert.equal(issue.title, "과세·면세를 함께 하는 광고비, 부가세는 얼마까지 공제될까?");
  assert.match(issue.question_blocks[0].answer, /200,000원/);
  assert.match(issue.question_blocks[1].answer, /240,000원/);
  assert.match(issue.question_blocks[1].answer, /760,000원/);
  assert.match(issue.question_blocks[1].explanation, /5퍼센트 미만/);
  assert.match(issue.question_blocks[2].answer, /160,000원/);
  assert.match(issue.question_blocks[2].explanation, /확정신고를 할 때에 정산/);
  assert.match(allocationRule.versions[0]?.text ?? "", /면세사업등에 관련된 매입세액/);
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

test("the practical expansion adds only reviewed, source-backed issue notes", () => {
  const ids = [
    "NTBA-CORRECTION-CLAIM-001",
    "NCTA-PAYMENT-EXTENSION-001",
    "CTA-OFFICER-BONUS-001",
    "ITA-BUSINESS-ACCOUNT-001",
    "VAT-CORRECTED-INVOICE-001",
  ];

  for (const id of ids) assert.ok(getIssue(id));
  assert.match(getIssue("NTBA-CORRECTION-CLAIM-001")?.question_blocks[0].answer ?? "", /5년/);
  const businessCar = getIssue("CTA-BUSINESS-CAR-001");
  assert.match(businessCar?.case_facts ?? "", /해당 사업연도 전체 기간/);
  assert.match(businessCar?.question_blocks[0].answer ?? "", /13,600,000원/);
  assert.match(businessCar?.question_blocks[1].answer ?? "", /영\(0\)원/);
  assert.match(getArticle("NTBA-45-2")?.versions[0]?.text ?? "", /증가된 과세표준 및 세액.*3개월/);
  assert.match(getArticle("CTA-27-2")?.versions[0]?.text ?? "", /8,000,000원.*이월하여/);
  assert.match(getArticle("CTAE-50-2")?.versions[0]?.text ?? "", /해당 사업연도 전체 기간/);
  assert.match(getIssue("VAT-BAD-DEBT-CREDIT-001")?.question_blocks[1].answer ?? "", /110분의 10/);
});

test("the practical core expansion adds direct, evidence-ready issue notes", () => {
  const ids = [
    "CTA-ADVANCE-TO-OFFICER-001",
    "CTA-BUSINESS-PROMOTION-EVIDENCE-001",
    "CTA-DONATION-001",
    "CTA-EXECUTIVE-RETIREMENT-001",
    "CTA-LOSS-CARRYFORWARD-001",
    "ITA-WITHHOLDING-PAYROLL-001",
    "ITA-FAMILY-WAGE-001",
    "ITA-RENTAL-INCOME-001",
    "ITA-CAPITAL-GAINS-TIMING-001",
    "ITA-CAPITAL-GAINS-COST-001",
    "VAT-INVOICE-PENALTY-001",
    "VAT-CARD-SALES-001",
    "VAT-DEEMED-INPUT-001",
    "VAT-INVENTORY-TAX-TRANSITION-001",
    "VAT-BUSINESS-REGISTRATION-001",
  ];

  for (const id of ids) assert.ok(getIssue(id), id);
  assert.equal(getCatalog().issues.length, 78);
  assert.equal(getLaws().find((law) => law.law_code === "CTA")?.issue_count, 18);
  assert.equal(getLaws().find((law) => law.law_code === "ITA")?.issue_count, 17);
  assert.equal(getLaws().find((law) => law.law_code === "VAT")?.issue_count, 18);
  assert.match(getIssue("CTA-ADVANCE-TO-OFFICER-001")?.case_facts ?? "", /80,000,000원/);
  assert.match(getIssue("ITA-FAMILY-WAGE-001")?.question_blocks[0]?.question ?? "", /배우자에게 준 급여/);
  assert.match(getIssue("ITA-CAPITAL-GAINS-COST-001")?.question_blocks[0]?.answer ?? "", /자본적 지출/);
  assert.match(getIssue("VAT-DEEMED-INPUT-001")?.question_blocks[0]?.question ?? "", /농산물/);
  assert.match(getIssue("VAT-BUSINESS-REGISTRATION-001")?.question_blocks[0]?.answer ?? "", /매입세액/);
  assert.match(getArticle("CTAE-44")?.versions[0]?.text ?? "", /현실적으로 퇴직/);
  assert.match(getArticle("ITA-128")?.versions[0]?.text ?? "", /다음 달 10일까지/);
  assert.match(getArticle("ITAE-163")?.versions[0]?.text ?? "", /증명서류를 수취ㆍ보관/);
  assert.match(getArticle("VAT-42")?.versions[0]?.text ?? "", /면세농산물등/);
  assert.match(getArticle("VATE-112")?.versions[0]?.text ?? "", /재고납부세액/);
  assert.match(getIssue("CTA-ADVANCE-TO-OFFICER-001")?.question_blocks[1]?.answer ?? "", /인정이자/);
  assert.match(getIssue("CTA-LOSS-CARRYFORWARD-001")?.question_blocks[0]?.legal_refs.join(" ") ?? "", /제14조 제3항/);
  assert.match(getArticle("CTA-24")?.versions[0]?.text ?? "", /10년 이내/);
  assert.match(getIssue("ITA-RENTAL-INCOME-001")?.question_blocks[0]?.legal_refs.join(" ") ?? "", /제25조 제1항$/);
  assert.match(getArticle("ITAE-163")?.versions[0]?.text ?? "", /제163조[\s\S]*⑤/);
  assert.match(getIssue("ITA-CAPITAL-GAINS-COST-001")?.question_blocks[0]?.legal_refs.join(" ") ?? "", /제163조 제5항/);
  assert.match(getArticle("ITA-97")?.versions[0]?.official_url ?? "", /1033246443/);
  assert.match(getArticle("ITA-98")?.versions[0]?.official_url ?? "", /1033246255/);
  assert.match(getArticle("VAT-33")?.versions[0]?.text ?? "", /세금계산서를 발급하지 아니한다/);
  assert.match(getIssue("VAT-CARD-SALES-001")?.question_blocks[1]?.answer ?? "", /제33조 제2항/);
  assert.match(getIssue("VAT-INVOICE-PENALTY-001")?.article_ids.join(" ") ?? "", /VAT-34/);
  assert.match(getIssue("VAT-BUSINESS-REGISTRATION-001")?.question_blocks[1]?.legal_refs.join(" ") ?? "", /제60조 제1항/);
  assert.equal(getIssue("VAT-INVENTORY-TAX-TRANSITION-001")?.question_blocks[0]?.legal_refs[0], "부가가치세법 제64조");
  assert.match(getIssue("VAT-INVENTORY-TAX-TRANSITION-001")?.question_blocks[0]?.legal_refs.join(" ") ?? "", /제112조 제3항 제1호/);
  assert.match(getIssue("VAT-INVENTORY-TAX-TRANSITION-001")?.question_blocks[0]?.legal_refs.join(" ") ?? "", /제112조 제7항/);
  assert.match(getIssue("VAT-INVENTORY-TAX-TRANSITION-001")?.question_blocks[1]?.legal_refs.join(" ") ?? "", /제112조 제1항 제5호/);
  assert.match(getIssue("VAT-INVENTORY-TAX-TRANSITION-001")?.question_blocks[1]?.legal_refs.join(" ") ?? "", /제112조 제3항 제3호 나목/);
  assert.match(getArticle("VATE-112")?.versions[0]?.text ?? "", /그 밖의 감가상각자산/);
});
