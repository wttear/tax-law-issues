import { test } from "node:test";
import assert from "node:assert/strict";
import { getCatalog, getIssue, getLaws } from "../lib/content";

test("catalog contains five laws and ten issues per law", () => {
  const catalog = getCatalog();
  assert.equal(catalog.issues.length, 50);
  assert.equal(getLaws().length, 5);
  for (const law of getLaws()) assert.equal(law.issue_ids.length, 10);
});

test("issue lookup returns the representative issue", () => {
  const issue = getIssue("NTBA-TAX-LIABILITY-LIFECYCLE-001");
  assert.ok(issue);
  assert.equal(issue.title, "납세의무의 성립·확정·소멸");
  assert.ok(issue.case_facts.length > 0);
  assert.ok(issue.question_blocks.length >= 2);
  assert.equal(getIssue("does-not-exist"), undefined);
});
