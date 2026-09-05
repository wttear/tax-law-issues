import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

test("the repository documents and ships only the Next.js site", () => {
  assert.equal(existsSync("scripts/build.py"), false);
  assert.equal(existsSync("src/site.js"), false);
  assert.equal(existsSync("src/site.css"), false);
  assert.equal(existsSync("docs/index.html"), false);

  const readme = readFileSync("README.md", "utf8");
  assert.match(readme, /Next\.js/);
  assert.match(readme, /npm run dev/);
  assert.match(readme, /deploy-pages/);
});
