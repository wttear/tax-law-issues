import { readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";
import { getCatalog } from "../lib/content";

test("the static export puts the case before direct questions without forced learning modules", () => {
  const issueDirectories = readdirSync("out/issues", { withFileTypes: true }).filter((entry) => entry.isDirectory());
  assert.equal(issueDirectories.length, getCatalog().issues.length);

  const html = readFileSync("out/issues/NTBA-LEGALITY-001/index.html", "utf8");
  assert.equal((html.match(/<h1\b/g) ?? []).length, 1);
  assert.ok(html.indexOf("사실관계 전문") < html.indexOf("내부지침만으로 지원금에 세금을 매길 수 있을까?"));
  assert.match(html, /질문[\s\S]{0,50}1/);
  assert.match(html, /관련 법령/);
  assert.match(html, /전체 쟁점 목록으로/);
  assert.doesNotMatch(html, /질문별 판단/);
  assert.doesNotMatch(html, /세무조사에 적용하기/);
  assert.doesNotMatch(html, /조건이 달라지면/);
});

test("a directly relevant, source-backed precedent is rendered after the learning note", () => {
  const html = readFileSync("out/issues/NTBA-LIMITATION-001/index.html", "utf8");
  assert.match(html, /관련 판례/);
  assert.match(html, /2021두33371/);
  assert.match(html, /law.go.kr/);
});

test("a vetted income-tax precedent is visible in its static learning note", () => {
  const html = readFileSync("out/issues/ITA-RESIDENCY-SOURCE-001/index.html", "utf8");
  assert.match(html, /관련 판례/);
  assert.match(html, /2016두37584/);
  assert.match(html, /law.go.kr/);
});

test("collection precedent cards are visible where statutory dates decide the result", () => {
  const priorityHtml = readFileSync("out/issues/NCTA-TAX-PRIORITY-001/index.html", "utf8");
  const thirdDebtorHtml = readFileSync("out/issues/NCTA-THIRD-DEBTOR-001/index.html", "utf8");

  assert.match(priorityHtml, /관련 판례/);
  assert.match(priorityHtml, /97다12037/);
  assert.match(thirdDebtorHtml, /관련 판례/);
  assert.match(thirdDebtorHtml, /2011다45521/);
});

test("corporate-tax learning notes render the concrete split and transaction-time precedent boundaries", () => {
  const incomeDispositionHtml = readFileSync("out/issues/CTA-INCOME-DISPOSITION-001/index.html", "utf8");
  const relatedPartyHtml = readFileSync("out/issues/CTA-RELATED-PARTY-001/index.html", "utf8");

  assert.match(incomeDispositionHtml, /법인 계좌에 남은 35,000,000원/);
  assert.match(incomeDispositionHtml, /97누19151/);
  assert.match(relatedPartyHtml, /같은 날 독립 거래 가격이 100,000,000원/);
  assert.match(relatedPartyHtml, /2017두35165/);
});

test("the nonbusiness-asset note renders its interest calculation rather than a generic instruction", () => {
  const html = readFileSync("out/issues/CTA-INTEREST-NONBUSINESS-ASSET-001/index.html", "utf8");

  assert.match(html, /지급이자 25,000,000원 중 얼마를 손금불산입으로 볼까/);
  assert.match(html, /25,000,000원 × 100,000,000원 ÷ 500,000,000원 = 5,000,000원/);
  assert.match(html, /적수/);
});

test("the construction-contract note renders the current work-progress rule and both calculation outcomes", () => {
  const html = readFileSync("out/issues/CTA-LONG-TERM-CONTRACT-001/index.html", "utf8");

  assert.match(html, /공사가 아직 끝나지 않았는데, 올해 매출을 잡아야 할까/);
  assert.match(html, /계약기간이 1년 이상인지 여부만으로/);
  assert.match(html, /1,200,000,000원/);
  assert.match(html, /1,500,000,000원/);
});

test("the business-income timing note renders service completion, receivable recovery, and the decree source", () => {
  const html = readFileSync("out/issues/ITA-INCOME-TIMING-001/index.html", "utf8");

  assert.match(html, /설계대금을 다음 해에 받아도, 올해 매출일까/);
  assert.match(html, /2026년 총수입금액/);
  assert.match(html, /2027년 매출로 다시 적지 않는다/);
  assert.match(html, /사업소득의 수입시기/);
});

test("the common-input note renders direct attribution, final allocation, and scheduled-return settlement", () => {
  const html = readFileSync("out/issues/VAT-COMMON-INPUT-ALLOCATION-001/index.html", "utf8");

  assert.match(html, /과세·면세를 함께 하는 광고비, 부가세는 얼마까지 공제될까/);
  assert.match(html, /공제받을 광고비 부가세는 760,000원/);
  assert.match(html, /160,000원 더 줄여 정산한다/);
  assert.match(html, /공통매입세액 안분 계산/);
});

test("expanded notes render direct questions, current rules, and no template filler", () => {
  const correction = readFileSync("out/issues/NTBA-CORRECTION-CLAIM-001/index.html", "utf8");
  const invoice = readFileSync("out/issues/VAT-CORRECTED-INVOICE-001/index.html", "utf8");

  assert.match(correction, /세금을 더 냈다는 사실을 나중에 알면/);
  assert.match(correction, /경정 등의 청구/);
  assert.match(invoice, /반품된 날/);
  assert.match(invoice, /수정세금계산서/);
});

test("the practical core notes are included in the static export", () => {
  for (const issueId of [
    "CTA-ADVANCE-TO-OFFICER-001",
    "ITA-CAPITAL-GAINS-TIMING-001",
    "VAT-DEEMED-INPUT-001",
  ]) {
    const html = readFileSync(`out/issues/${issueId}/index.html`, "utf8");
    assert.match(html, /사실관계 전문/);
  }
});

test("the practical core notes render their corrected legal boundaries", () => {
  const cardSale = readFileSync("out/issues/VAT-CARD-SALES-001/index.html", "utf8");
  const invoicePenalty = readFileSync("out/issues/VAT-INVOICE-PENALTY-001/index.html", "utf8");
  const donation = readFileSync("out/issues/CTA-DONATION-001/index.html", "utf8");
  const capitalCost = readFileSync("out/issues/ITA-CAPITAL-GAINS-COST-001/index.html", "utf8");
  const inventoryTransition = readFileSync("out/issues/VAT-INVENTORY-TAX-TRANSITION-001/index.html", "utf8");

  assert.match(cardSale, /세금계산서 발급의무의 면제 등/);
  assert.match(cardSale, /제33조 제2항/);
  assert.match(invoicePenalty, /세금계산서 발급시기/);
  assert.match(invoicePenalty, /단순 지연 발급/);
  assert.match(donation, /10년 이내/);
  assert.match(capitalCost, /소득세법 시행령 제163조 제5항/);
  assert.match(inventoryTransition, /제112조 제3항 제1호/);
  assert.match(inventoryTransition, /제112조 제3항 제3호 나목/);
});
