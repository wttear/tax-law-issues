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
