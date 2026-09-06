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
