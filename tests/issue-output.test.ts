import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

test("the static export creates one connected reading page for every issue", () => {
  if (!existsSync("out/issues")) {
    execFileSync("npm", ["run", "build"], {
      env: { ...process.env, NEXT_PUBLIC_BASE_PATH: "" },
      stdio: "pipe",
    });
  }

  const issueDirectories = readdirSync("out/issues", { withFileTypes: true }).filter((entry) => entry.isDirectory());
  assert.equal(issueDirectories.length, 50);

  const html = readFileSync("out/issues/NTBA-LEGALITY-001/index.html", "utf8");
  assert.equal((html.match(/<h1\b/g) ?? []).length, 1);
  assert.ok(html.indexOf("사실관계 전문") < html.indexOf("질문별 판단"));
  assert.ok(html.indexOf("질문별 판단") < html.indexOf("관련 법령 원문"));
  assert.match(html, /질문[\s\S]{0,50}1/);
  assert.match(html, /세무조사에 적용하기/);
  assert.match(html, /관련 판례/);
  assert.match(html, /조건이 달라지면/);
  assert.match(html, /법령 원문 열기|공식 판결문/);
});
