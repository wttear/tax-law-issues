# Next.js + Tailwind + shadcn 전환 Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 현재 50개 세법 쟁점 대장의 콘텐츠·URL·모바일 읽기 흐름을 보존하면서 Next.js App Router, Tailwind CSS v4, shadcn/ui 기반의 GitHub Pages 정적 사이트로 전환한다.

**Architecture:** content/*.json은 공개 스냅샷으로 유지하고 lib/content.ts가 빌드 시 타입과 필수 필드를 검증한다. app/의 서버 컴포넌트가 메인 대장과 50개 상세 페이지를 정적으로 생성하며 메인 검색·필터만 클라이언트 컴포넌트가 담당한다. next build가 out/을 만들고 GitHub Actions가 Pages artifact로 배포한다.

**Tech Stack:** Next.js App Router, React, TypeScript, Tailwind CSS v4/PostCSS, shadcn/ui 소스 컴포넌트, Node.js LTS/npm, Python 3 표준 라이브러리 콘텐츠 추출, GitHub Pages Actions.

---

## 파일 구조

- app/layout.tsx, app/page.tsx, app/not-found.tsx
- app/issues/[issueId]/page.tsx
- app/globals.css
- components/issue-browser.tsx, issue-row.tsx, law-section.tsx, issue-reader.tsx
- components/ui/{button,input,select,badge,card,separator}.tsx
- components.json, lib/content.ts, lib/utils.ts, types/content.ts
- next.config.mjs, postcss.config.mjs
- .github/workflows/deploy-pages.yml, public/.nojekyll
- tests/*.test.mjs, tests/*.test.ts, tests/test_build.py
- scripts/bootstrap_content.py는 콘텐츠 갱신용으로 유지한다.

## Task 1: Node/Next 정적 프로젝트 골격

**Files:** package.json, package-lock.json, tsconfig.json, next-env.d.ts, next.config.mjs, postcss.config.mjs, components.json, .gitignore, tests/project-contract.test.mjs

- [ ] Step 1: 실패 테스트를 먼저 만든다.

~~~js
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));

test("Next project exposes required scripts", () => {
  assert.equal(pkg.private, true);
  assert.equal(pkg.scripts.build, "next build");
  assert.equal(pkg.scripts.typecheck, "tsc --noEmit");
  assert.ok(pkg.dependencies.next);
  assert.ok(pkg.dependencies.tailwindcss);
});

test("static export is configured", () => {
  assert.match(fs.readFileSync("next.config.mjs", "utf8"), /output:\s*["']export["']/);
  assert.match(fs.readFileSync("next.config.mjs", "utf8"), /basePath/);
  assert.match(fs.readFileSync("postcss.config.mjs", "utf8"), /@tailwindcss\/postcss/);
  assert.ok(fs.existsSync("components.json"));
});
~~~

- [ ] Step 2: Run: node --test tests/project-contract.test.mjs. Expected: FAIL because the files do not exist.
- [ ] Step 3: Install dependencies and scripts.

~~~bash
npm init -y
npm install next react react-dom tailwindcss @tailwindcss/postcss postcss shadcn class-variance-authority clsx tailwind-merge lucide-react tw-animate-css
npm install --save-dev typescript @types/node @types/react @types/react-dom tsx
npm pkg set private=true
npm pkg set scripts.dev="next dev" scripts.build="next build" scripts.start="next start" scripts.typecheck="tsc --noEmit" scripts.test:node="node --import tsx --test tests/*.test.ts" scripts.test:python="python3 -m unittest discover -s tests -p 'test_*.py'" scripts.verify="npm run typecheck && npm run build && npm run test:node && npm run test:python"
~~~

- [ ] Step 4: Create next.config.mjs.

~~~js
const nextConfig = {
  output: "export",
  basePath: process.env.NEXT_PUBLIC_BASE_PATH ?? "/tax-law-issues",
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
};
export default nextConfig;
~~~

Create strict tsconfig.json with resolveJsonModule, moduleResolution bundler, baseUrl ., paths @/* → ./*, Next plugin, and include next-env.d.ts, .next/types/**/*.ts, and all ts/tsx files. Create next-env.d.ts with standard Next references. Create postcss.config.mjs with the @tailwindcss/postcss plugin. Add node_modules/, .next/, and out/ to .gitignore.

- [ ] Step 5: Create components.json with style new-york, rsc true, tsx true, app/globals.css, CSS variables, and aliases for @/components, @/components/ui, @/lib/utils, and @/lib.
- [ ] Step 6: Run node --test tests/project-contract.test.mjs. Expected: PASS. Commit chore: scaffold Next.js static export project.

## Task 2: Typed content loader

**Files:** types/content.ts, lib/content.ts, tests/content-loader.test.ts

- [ ] Step 1: Write this failing test.

~~~ts
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
~~~

- [ ] Step 2: Run: node --import tsx --test tests/content-loader.test.ts. Expected: FAIL because the loader is missing.
- [ ] Step 3: Define Law, Issue, QuestionBlock, Article, ArticleVersion, Precedent, RelatedReference, IssueModules, and snapshot types. QuestionBlock requires block_no, judgment_type (rule | calculation | evidence | change), question, fact_scope, legal_refs, answer, explanation, evidence, precedent_refs, and accounting_note.
- [ ] Step 4: Implement lib/content.ts. Import the three JSON snapshots; expose getCatalog, getLaws, getIssues, getIssue, getArticle, and getPrecedent. Validate at module load: five laws, ten issues per law, unique issue IDs, non-empty case_facts, at least two question blocks, required strings/arrays, and every article/precedent reference exists. Throw Error("Content validation failed: issue.field") on failure.
- [ ] Step 5: Run the loader test. Expected: PASS. Commit feat: add typed tax content loader.

## Task 3: Tailwind and shadcn/ui primitives

**Files:** lib/utils.ts, components/ui/button.tsx, input.tsx, select.tsx, badge.tsx, card.tsx, separator.tsx, app/globals.css, tests/ui-contract.test.mjs

- [ ] Step 1: Write the failing contract.

~~~js
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const required = ["button", "input", "select", "badge", "card", "separator"];

test("shadcn primitives are repository-owned", () => {
  for (const name of required) assert.ok(fs.existsSync("components/ui/" + name + ".tsx"));
  assert.ok(fs.existsSync("lib/utils.ts"));
  assert.match(fs.readFileSync("app/globals.css", "utf8"), /@import ["']tailwindcss["']/);
});
~~~

- [ ] Step 2: Run: node --test tests/ui-contract.test.mjs. Expected: FAIL.
- [ ] Step 3: Generate components with npx shadcn@latest add button input select badge card separator. Keep generated source in components/ui and lock any primitive dependencies.
- [ ] Step 4: Make lib/utils.ts export cn using clsx and twMerge.

~~~ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
~~~

- [ ] Step 5: Start app/globals.css with @import "tailwindcss"; and the shadcn animation import. Define CSS variables and @theme inline tokens for background #f4f1e8, foreground #16283d, card #fffdf7, primary #155d9c, secondary #0b6f69, muted #ece8dd, destructive #9b3d36, border #b7b4ab, and radius 0.2rem. Set body to 17px, line-height 1.72, keep-all, and anywhere.
- [ ] Step 6: Run the contract. Expected: PASS. Commit feat: add Tailwind and shadcn primitives.

## Task 4: Main atlas and client filtering

**Files:** app/layout.tsx, app/page.tsx, components/issue-browser.tsx, issue-row.tsx, law-section.tsx, tests/index-output.test.ts

- [ ] Step 1: Write the failing output contract.

~~~ts
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { execFileSync } from "node:child_process";

test("Next build emits the five-law index", () => {
  execFileSync("npm", ["run", "build"], { env: { ...process.env, NEXT_PUBLIC_BASE_PATH: "" } });
  const html = fs.readFileSync("out/index.html", "utf8");
  assert.equal((html.match(/<h1/g) ?? []).length, 1);
  for (const law of ["국세기본법", "국세징수법", "법인세법", "소득세법", "부가가치세법"]) assert.match(html, new RegExp(law));
  assert.equal((html.match(/class="issue-row"/g) ?? []).length, 50);
  assert.match(html, /id="issue-search"/);
  assert.match(html, /id="law-filter"/);
});
~~~

- [ ] Step 2: Run: node --import tsx --test tests/index-output.test.ts. Expected: FAIL because app routes do not exist.
- [ ] Step 3: Create app/layout.tsx with lang ko, viewport, description, globals.css, skip link, sticky header, and a single main landmark.
- [ ] Step 4: Create server components. app/page.tsx calls getCatalog. IssueRow outputs data-law, data-search, number, level, title, core question, Badge module labels, and a buttonVariants Link to /issues/{id}/. LawSection renders all five groups and ten rows per group.
- [ ] Step 5: Create issue-browser.tsx with "use client". It must keep children as server-rendered markup, use shadcn Input and Select, filter data-search/data-law, update hidden and aria-hidden, and announce visible count. It must never use localStorage or URL state; without JavaScript all 50 rows remain visible.
- [ ] Step 6: Run the output test. Expected: PASS. Commit feat: render Next.js issue index.

## Task 5: Issue reader and static routes

**Files:** app/issues/[issueId]/page.tsx, app/not-found.tsx, components/issue-reader.tsx, question-block.tsx, law-article.tsx, precedent-card.tsx, tests/issue-output.test.ts

- [ ] Step 1: Write this test, which runs a base-path-empty build, asserts 50 out/issues directories, checks the reader labels in order, and verifies the static 404.

~~~ts
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { execFileSync } from "node:child_process";

test("all issue pages preserve the reader sequence", () => {
  execFileSync("npm", ["run", "build"], { env: { ...process.env, NEXT_PUBLIC_BASE_PATH: "" } });
  assert.equal(fs.readdirSync("out/issues").length, 50);
  const html = fs.readFileSync("out/issues/NTBA-TAX-LIABILITY-LIFECYCLE-001/index.html", "utf8");
  for (const label of ["사실관계", "질문별 판단", "관련 조문 보기", "답과 해설", "판례·조사·회계 연결", "마지막 정리"]) assert.match(html, new RegExp(label));
  assert.ok(html.indexOf("사실관계") < html.indexOf("질문별 판단"));
  assert.ok(html.indexOf("질문별 판단") < html.indexOf("관련 조문 보기"));
  assert.ok(fs.existsSync("out/404.html"));
});
~~~
- [ ] Step 2: Run: node --import tsx --test tests/issue-output.test.ts. Expected: FAIL.
- [ ] Step 3: Implement generateStaticParams from getIssues, dynamicParams = false, getIssue lookup, notFound for an unknown ID, and metadata from title/core question.
- [ ] Step 4: Implement IssueReader in this fixed order: breadcrumb/title, full case_facts, 질문별 판단, question blocks, final summary, precedent·audit·accounting connection, transfer conditions, last recap. Each QuestionBlock must show question first, then fact_scope, native details for related articles, answer/explanation, evidence/precedents/accounting. Never repeat the full case facts or invent missing sources.
- [ ] Step 5: Implement app/not-found.tsx with one h1, a clear missing-issue message, and a Link back to the atlas. Do not include login, completion, or browser state.
- [ ] Step 6: Run the issue test. Expected: PASS. Commit feat: generate static tax issue readers.

## Task 6: Mobile visual system and accessibility

**Files:** app/globals.css, app/layout.tsx, components/issue-browser.tsx, components/issue-reader.tsx, tests/style-output.test.mjs

- [ ] Step 1: Write this failing test for the palette, Tailwind import, no CDN stylesheet, and skip link.

~~~js
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("compiled output uses atlas tokens without a CDN stylesheet", () => {
  const source = fs.readFileSync("app/globals.css", "utf8");
  assert.match(source, /#f4f1e8/i);
  assert.match(source, /#16283d/i);
  assert.match(source, /@import ["']tailwindcss["']/);
  const html = fs.readFileSync("out/index.html", "utf8");
  assert.doesNotMatch(html, /cdn\.jsdelivr\.net|unpkg\.com|fonts\.googleapis\.com/);
  assert.match(html, /skip-link|sr-only/);
});
~~~
- [ ] Step 2: Run: node --test tests/style-output.test.mjs. Expected: FAIL until styles are present.
- [ ] Step 3: Move the existing visual language into static Tailwind classes: paper/stone/ink palette, thin rules, ledger rows, one-column mobile layout, and no shadows/gradients/emoji/hamburger. Use w-full, min-w-0, break-words, text labels with badges, 44px minimum targets, print preservation, and prefers-reduced-motion. Keep only token/base/accessibility rules in globals.css; do not recreate the old monolithic stylesheet.
- [ ] Step 4: Run NEXT_PUBLIC_BASE_PATH="" npm run build && node --test tests/style-output.test.mjs. Expected: PASS. Commit style: migrate atlas UI to Tailwind tokens.

## Task 7: GitHub Pages Actions

**Files:** .github/workflows/deploy-pages.yml, public/.nojekyll, tests/deploy-contract.test.mjs

- [ ] Step 1: Write this failing workflow contract.

~~~js
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("Pages workflow publishes the Next export", () => {
  const workflow = fs.readFileSync(".github/workflows/deploy-pages.yml", "utf8");
  for (const token of ["actions/checkout", "actions/setup-node", "npm ci", "npm run build", "upload-pages-artifact", "deploy-pages"]) {
    assert.ok(workflow.includes(token), token);
  }
  assert.match(workflow, /path:\s*\.\/out/);
  assert.match(workflow, /NEXT_PUBLIC_BASE_PATH:\s*\/tax-law-issues/);
});
~~~
- [ ] Step 2: Run: node --test tests/deploy-contract.test.mjs. Expected: FAIL.
- [ ] Step 3: Create the workflow with push to main and workflow_dispatch, contents read/pages write/id-token write permissions, concurrency group pages, Node 22 setup with npm cache, NEXT_PUBLIC_BASE_PATH=/tax-law-issues, npm ci, npm run build, upload-pages-artifact path ./out, and a deploy job using actions/deploy-pages@v4. Create empty public/.nojekyll. The workflow uses committed JSON snapshots; it does not try to access sibling tax-study.
- [ ] Step 4: Run the contract. Expected: PASS. Commit ci: deploy Next static export to GitHub Pages.

## Task 8: Tests, documentation, and legacy cleanup

**Files:** tests/test_build.py, README.md, PRODUCT.md, DESIGN.md, docs/implementation-plan.md, .gitignore; remove old generated UI only after verification

- [ ] Step 1: Change tests/test_build.py from DOCS to OUTPUT = ROOT / "out"; run npm run build with NEXT_PUBLIC_BASE_PATH="" in setUpClass; read representative pages from out. Preserve checks for 50 issues, 10 per law, one h1, official links, no localStorage, no 수업 완료, and no 55:25:20.
- [ ] Step 2: Run python3 -m unittest discover -s tests -p 'test_*.py' -v. Expected: FAIL until output paths and Next output align.
- [ ] Step 3: Update README.md with npm ci, NEXT_PUBLIC_BASE_PATH="" npm run build, and python3 -m http.server 4173 --directory out. Explain that bootstrap_content.py is only for local source refresh, list the free GitHub Pages workflow, and retain the public URL. Update PRODUCT.md Stack and DESIGN.md tokens/component policy. Replace the old static-stack description in docs/implementation-plan.md.
- [ ] Step 4: After npm run verify and local HTTP checks pass, remove only the obsolete renderer and generated UI: scripts/build.py, src/site.js, src/site.css, docs/index.html, docs/styles.css, docs/site.js, docs/.nojekyll, and docs/issues/. Keep content/, scripts/bootstrap_content.py, docs/superpowers/, and product/design documents.
- [ ] Step 5: Run npm run verify. Expected: typecheck, Next build, Node tests, and Python tests all PASS. Commit refactor: make Next.js the canonical site build.

## Task 9: Final verification and public deployment

**Files:** no new source files; out/ is ignored

- [ ] Step 1: Run npm run typecheck, NEXT_PUBLIC_BASE_PATH="" npm run build, node --import tsx --test tests/*.test.ts, node --test tests/*.test.mjs, and python3 -m unittest discover -s tests -p 'test_*.py' -v. Expected: exit 0, out/index.html and out/404.html exist, and 50 out/issues/*/index.html files exist.
- [ ] Step 2: Serve out with python3 -m http.server 4173 --directory out and curl root, representative issue path, and an unknown path. Each response must contain the expected Korean labels.
- [ ] Step 3: Run the impeccable detector on out/index.html and one representative issue page, run git diff --check, and inspect git status. Fix only concrete findings.
- [ ] Step 4: Push the verified main commit, set repository Settings → Pages → Source to GitHub Actions once, wait for the workflow, and curl the public root and representative issue URL. Do not claim publication until both requests succeed.
- [ ] Step 5: Record the verified commit SHA and public URL in the handoff and state that tax-study was not modified. Commit chore: verify Next.js Pages deployment.
