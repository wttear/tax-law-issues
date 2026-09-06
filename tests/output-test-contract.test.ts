import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

test("static-output checks rely on one fresh build run by the test script", () => {
  const packageJson = JSON.parse(readFileSync("package.json", "utf8")) as { scripts: Record<string, string> };
  const indexTest = readFileSync("tests/index-output.test.ts", "utf8");
  const issueTest = readFileSync("tests/issue-output.test.ts", "utf8");

  assert.match(packageJson.scripts["test:node"], /^npm run build && node /);
  assert.doesNotMatch(indexTest, /execFileSync/);
  assert.doesNotMatch(issueTest, /execFileSync/);
});
