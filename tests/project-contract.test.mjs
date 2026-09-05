import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8"));

test("Next project exposes required scripts", () => {
  assert.equal(packageJson.private, true);
  assert.equal(packageJson.scripts.build, "next build");
  assert.equal(packageJson.scripts.typecheck, "tsc --noEmit");
  assert.ok(packageJson.dependencies.next);
  assert.ok(packageJson.dependencies.tailwindcss);
});

test("static export is configured", () => {
  assert.match(fs.readFileSync("next.config.mjs", "utf8"), /output:\s*[\"']export[\"']/);
  assert.match(fs.readFileSync("next.config.mjs", "utf8"), /basePath/);
  assert.match(fs.readFileSync("postcss.config.mjs", "utf8"), /@tailwindcss\/postcss/);
  assert.ok(fs.existsSync("components.json"));
});
