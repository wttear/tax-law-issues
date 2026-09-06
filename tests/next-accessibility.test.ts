import { readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";
import { getCatalog } from "../lib/content";

function htmlFiles(): string[] {
  const pages = ["out/index.html"];
  for (const entry of readdirSync("out/issues", { withFileTypes: true })) {
    if (entry.isDirectory()) pages.push(`out/issues/${entry.name}/index.html`);
  }
  return pages;
}

test("static pages keep the orientation, accessibility, and source contracts", () => {
  const banned = [
    "법령과 쟁점의 판단 지도",
    "법적 판단지도",
    "합성 사례",
    "결론의 이동",
    "55:25:20",
    "수업 완료",
    "localhost",
    "file://",
  ];

  for (const file of htmlFiles()) {
    const html = readFileSync(file, "utf8");
    assert.equal((html.match(/<h1\b/g) ?? []).length, 1, file);
    assert.match(html, /본문으로 건너뛰기/, file);
    assert.match(html, /name="viewport"/, file);
    assert.match(html, /THESIS:/, file);
    assert.match(html, /FIRST VIEWPORT:/, file);
    assert.match(html, /FINISH:/, file);
    for (const phrase of banned) assert.doesNotMatch(html.toLowerCase(), new RegExp(phrase.toLowerCase()), `${file}: ${phrase}`);
  }
});

test("the index keeps all issue rows in the HTML fallback", () => {
  const html = readFileSync("out/index.html", "utf8");
  assert.equal((html.match(/data-issue-row="true"/g) ?? []).length, getCatalog().issues.length);
  assert.match(html, /id="issue-search"/);
  assert.match(html, /id="law-filter"/);
});
