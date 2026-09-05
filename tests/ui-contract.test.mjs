import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const required = ["button", "input", "select", "badge", "card", "separator"];

test("shadcn primitives are repository-owned", () => {
  for (const name of required) assert.ok(fs.existsSync("components/ui/" + name + ".tsx"), name);
  assert.ok(fs.existsSync("lib/utils.ts"));
  assert.match(fs.readFileSync("app/globals.css", "utf8"), /@import [\"']tailwindcss[\"']/);
});
