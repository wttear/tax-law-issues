import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

test("the static export contains the mobile-first issue browser", () => {
  if (!existsSync("out/index.html")) {
    execFileSync("npm", ["run", "build"], {
      env: { ...process.env, NEXT_PUBLIC_BASE_PATH: "" },
      stdio: "pipe",
    });
  }

  const html = readFileSync("out/index.html", "utf8");
  assert.match(html, /법령별 쟁점/);
  assert.match(html, /쟁점 검색/);
  assert.match(html, /국세기본법/);
  assert.match(html, /전체[\s\S]{0,100}50[\s\S]{0,100}개/);
  assert.match(html, /issue-row/);
  assert.match(html, /issues\/NTBA-LEGALITY-001/);
});
