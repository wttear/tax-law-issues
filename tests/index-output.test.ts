import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";
import { getCatalog } from "../lib/content";

test("the static export contains the mobile-first issue browser", () => {
  const html = readFileSync("out/index.html", "utf8");
  assert.match(html, /법령별 쟁점/);
  assert.match(html, /쟁점 검색/);
  assert.match(html, /국세기본법/);
  assert.match(html, new RegExp(`전체[\\s\\S]{0,100}${getCatalog().issues.length}[\\s\\S]{0,100}개`));
  assert.match(html, /issue-row/);
  assert.match(html, /issues\/NTBA-LEGALITY-001/);
});

test("catalogue summaries derive their counts from the loaded content", () => {
  const home = readFileSync("app/page.tsx", "utf8");
  const browser = readFileSync("components/issue-browser.tsx", "utf8");

  assert.match(home, /국세 \{laws\.length\}개 법령 · \{issues\.length\}개 쟁점/);
  assert.match(home, /법령별 실제 개수/);
  assert.match(home, /\{law\.issue_count\}개 쟁점/);
  assert.match(browser, /\{issueCount\}개 쟁점에서 골라 읽기/);
  assert.doesNotMatch(browser, /50개 쟁점에서 골라 읽기/);
});
