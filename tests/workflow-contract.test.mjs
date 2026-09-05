import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

test("GitHub Pages workflow builds and deploys the Next static export", () => {
  const workflow = readFileSync(".github/workflows/deploy-pages.yml", "utf8");
  assert.match(workflow, /actions\/checkout@v4/);
  assert.match(workflow, /actions\/setup-node@v4/);
  assert.match(workflow, /npm ci/);
  assert.match(workflow, /NEXT_PUBLIC_BASE_PATH: \/tax-law-issues/);
  assert.match(workflow, /actions\/upload-pages-artifact@v3/);
  assert.match(workflow, /actions\/deploy-pages@v4/);
  assert.match(workflow, /pages: write/);
  assert.match(workflow, /id-token: write/);
});
