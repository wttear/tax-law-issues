# 반복 실무 세법 쟁점 확장 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** 기존 63개 학습 노트에 실제 사업자 신고·증빙·세무조정에서 반복되는 법인세·소득세·부가가치세 쟁점 15개를 정확한 공식 법령 근거와 함께 추가한다.

**Architecture:** 기존의 콘텐츠 전용 정적 데이터 구조를 유지한다. content/issues.json의 목록은 탐색용 기본 인덱스로, content/learning-notes.json은 독자가 읽는 검수 원고로, content/issue-selection.json은 공개 목록의 독립 검증 원본으로 함께 갱신한다. 법령 문구는 content/articles.json의 공식 국가법령정보센터 스냅샷으로만 연결하고, 화면 코드나 새로운 메뉴는 추가하지 않는다.

**Tech Stack:** Next.js App Router, React, TypeScript, Node.js test runner, Tailwind CSS, JSON 콘텐츠 스냅샷, GitHub Pages.

---

## 파일 구조

- Modify: content/issues.json — 15개 쟁점의 기본 인덱스, 법률별 순서와 집계값
- Modify: content/learning-notes.json — 독자가 읽는 15개 자연어 학습 원고
- Modify: content/issue-selection.json — 공개 목록과 선택 기준일
- Modify: content/articles.json — 새 원고가 실제 참조하는 현행 법령 카드와 원문 해시
- Modify: tests/content-loader.test.ts — 새 쟁점의 목록, 질문·사실관계·근거 연결 계약
- Modify: tests/issue-output.test.ts — 정적 산출물에 새 노트 경로가 포함되는지 확인
- Modify: README.md — 현재 콘텐츠 수와 확장 원칙을 한 줄로 갱신
- Create: docs/superpowers/specs/2026-09-07-practical-tax-core-expansion-design.md — 승인된 범위·원칙
- Create: docs/superpowers/plans/2026-09-07-practical-tax-core-expansion.md — 이 실행 계획

### Task 1: 현행 법령 근거를 수집하고 카드 범위를 결정한다

**Files:**
- Modify: content/articles.json
- Test: tests/content-loader.test.ts

- [ ] **Step 1: 국가법령정보센터에서 아래 원문을 현행 시행일 기준으로 확인한다**

  조사 대상은 법인세법 제24조·제27조의2·제28조·제33조 및 관련 시행령, 소득세법의 원천징수·사업소득 필요경비·부동산임대업·양도시기·필요경비 규정 및 관련 시행령, 부가가치세법의 사업자등록·세금계산서·가산세·의제매입세액·과세유형 전환 규정 및 관련 시행령이다.

  각 카드에는 다음 필드를 남긴다.

  ~~~json
  {
    "article_id": "새 식별자",
    "law_code": "CTA 또는 ITA 또는 VAT",
    "article_number": "조문 번호",
    "title": "공식 조문 제목",
    "official_url": "https://www.law.go.kr/ 의 직접 조문 URL",
    "source_url": "https://www.law.go.kr/ 의 법령 URL",
    "source_as_of": "2026-09-07",
    "content_status": "source_only",
    "versions": [
      {
        "checked_at": "2026-09-07",
        "effective_date": "확인한 시행일",
        "official_url": "직접 조문 URL",
        "source_sha256": "원문 UTF-8 SHA-256",
        "status": "current",
        "text": "결론에 필요한 요건과 예외를 빠짐없이 포함한 원문"
      }
    ]
  }
  ~~~

- [ ] **Step 2: 원문을 해시로 다시 확인한다**

  Run: 아래 Node 명령으로 새 카드의 text와 source_sha256을 대조한다.

  ~~~bash
  node -e "const c=require('crypto'); const a=require('./content/articles.json').articles; for (const x of a.filter(x=>x.article_id.startsWith('CTA-')||x.article_id.startsWith('ITA-')||x.article_id.startsWith('VAT-'))) for (const v of x.versions) { if (v.source_sha256) console.log(x.article_id, c.createHash('sha256').update(v.text,'utf8').digest('hex')===v.source_sha256 ? 'ok' : 'mismatch'); }"
  ~~~

  Expected: 이번에 새로 넣은 카드가 모두 \`ok\`이고 기존 카드의 결과는 변경하지 않는다.

- [ ] **Step 3: 해당 쟁점의 경계를 실제로 바꾸는 공식 판례만 추가한다**

  판례를 찾지 못했거나 조문만으로 결론이 충분하면 precedent_ids는 빈 배열로 둔다. 블로그·요약 페이지로 판시내용을 보충하지 않는다.

- [ ] **Step 4: 법령 카드 변경을 검증한다**

  Run: \`npm run typecheck\`

  Expected: PASS.

### Task 2: 실패하는 콘텐츠 계약 테스트를 먼저 추가한다

**Files:**
- Modify: tests/content-loader.test.ts
- Modify: tests/issue-output.test.ts

- [ ] **Step 1: 15개 식별자의 공개 목록 계약을 쓴다**

  tests/content-loader.test.ts 끝에 다음 테스트를 추가한다.

  ~~~ts
  test("the practical core expansion adds only direct, evidence-ready issue notes", () => {
    const ids = [
      "CTA-ADVANCE-TO-OFFICER-001",
      "CTA-BUSINESS-PROMOTION-EVIDENCE-001",
      "CTA-DONATION-001",
      "CTA-EXECUTIVE-RETIREMENT-001",
      "CTA-LOSS-CARRYFORWARD-001",
      "ITA-WITHHOLDING-PAYROLL-001",
      "ITA-FAMILY-WAGE-001",
      "ITA-RENTAL-INCOME-001",
      "ITA-CAPITAL-GAINS-TIMING-001",
      "ITA-CAPITAL-GAINS-COST-001",
      "VAT-INVOICE-PENALTY-001",
      "VAT-CARD-SALES-001",
      "VAT-DEEMED-INPUT-001",
      "VAT-INVENTORY-TAX-TRANSITION-001",
      "VAT-BUSINESS-REGISTRATION-001",
    ];

    for (const id of ids) assert.ok(getIssue(id), id);
    assert.equal(getCatalog().issues.length, 78);
    assert.match(getIssue("CTA-ADVANCE-TO-OFFICER-001")?.case_facts ?? "", /80,000,000원/);
    assert.match(getIssue("ITA-FAMILY-WAGE-001")?.question_blocks[0]?.question ?? "", /배우자에게 준 급여/);
    assert.match(getIssue("ITA-CAPITAL-GAINS-COST-001")?.question_blocks[0]?.answer ?? "", /필요경비/);
    assert.match(getIssue("VAT-DEEMED-INPUT-001")?.question_blocks[0]?.question ?? "", /농산물/);
    assert.match(getIssue("VAT-BUSINESS-REGISTRATION-001")?.question_blocks[0]?.answer ?? "", /매입세액/);
  });
  ~~~

- [ ] **Step 2: 새 URL 산출물 계약을 쓴다**

  tests/issue-output.test.ts의 기존 정적 파일 검사에 아래 3개 대표 경로를 넣는다.

  ~~~ts
  for (const slug of [
    "cta-advance-to-officer-001",
    "ita-capital-gains-timing-001",
    "vat-deemed-input-001",
  ]) {
    assert.ok(existsSync(join("out", "issues", slug, "index.html")), slug);
  }
  ~~~

- [ ] **Step 3: 아직 콘텐츠를 추가하기 전 실패를 확인한다**

  Run: \`npx tsx --test tests/content-loader.test.ts\`

  Expected: 새 15개 issue_id가 없어 \`the practical core expansion\` 테스트가 FAIL한다.

- [ ] **Step 4: 테스트 변경을 커밋한다**

  ~~~bash
  git add tests/content-loader.test.ts tests/issue-output.test.ts
  git commit -m "test: define practical tax core expansion"
  ~~~

### Task 3: 탐색 인덱스와 선택 목록을 확장한다

**Files:**
- Modify: content/issues.json
- Modify: content/issue-selection.json
- Test: tests/content-loader.test.ts

- [ ] **Step 1: 법인세법 인덱스에 다섯 쟁점을 추가한다**

  법인세법 issue_ids의 기존 마지막 항목 뒤에 아래 순서로 추가하고, position을 연속된 값으로 둔다.

  ~~~text
  CTA-ADVANCE-TO-OFFICER-001
  CTA-BUSINESS-PROMOTION-EVIDENCE-001
  CTA-DONATION-001
  CTA-EXECUTIVE-RETIREMENT-001
  CTA-LOSS-CARRYFORWARD-001
  ~~~

- [ ] **Step 2: 소득세법 인덱스에 다섯 쟁점을 추가한다**

  ~~~text
  ITA-WITHHOLDING-PAYROLL-001
  ITA-FAMILY-WAGE-001
  ITA-RENTAL-INCOME-001
  ITA-CAPITAL-GAINS-TIMING-001
  ITA-CAPITAL-GAINS-COST-001
  ~~~

- [ ] **Step 3: 부가가치세법 인덱스에 다섯 쟁점을 추가한다**

  ~~~text
  VAT-INVOICE-PENALTY-001
  VAT-CARD-SALES-001
  VAT-DEEMED-INPUT-001
  VAT-INVENTORY-TAX-TRANSITION-001
  VAT-BUSINESS-REGISTRATION-001
  ~~~

- [ ] **Step 4: issue-selection.json을 동일한 순서와 기준일로 갱신한다**

  법률별 issue_ids는 issues.json과 한 항목도 다르지 않게 유지한다. selection_note는 수량 충족이 아닌 중복 없는 실무 판단 필요성을 기준으로 삼는 문장으로 둔다.

- [ ] **Step 5: 목록 일치 테스트를 실행한다**

  Run: \`npx tsx --test tests/content-loader.test.ts\`

  Expected: 목록 일치 테스트는 PASS하고, 아직 학습 원고가 없으면 reviewed-note 누락 검증만 FAIL한다.

### Task 4: 독자가 읽는 15개 학습 원고를 작성한다

**Files:**
- Modify: content/learning-notes.json
- Test: tests/content-loader.test.ts

- [ ] **Step 1: 법인세법 다섯 원고를 작성한다**

  각 원고는 하나의 완결된 사실관계 문단, 직접 질문과 즉시 이어지는 답, 필요한 증빙과 세무조정만 담는다.

  | issue_id | 제목 | 반드시 다룰 판단 경계 |
  | --- | --- | --- |
  | CTA-ADVANCE-TO-OFFICER-001 | 대표가 법인 돈을 먼저 가져가면, 이자 없이 두어도 될까? | 업무상 대여와 대표 개인 사용, 인정이자, 회수·이자 수령 증빙 |
  | CTA-BUSINESS-PROMOTION-EVIDENCE-001 | 거래처 식사비는 영수증만 있으면 비용이 될까? | 거래 상대방·업무 목적·증빙, 기업업무추진비 한도 |
  | CTA-DONATION-001 | 기부금은 회사가 냈으면 전부 비용일까? | 세무상 기부금 분류, 한도 초과, 이월공제 |
  | CTA-EXECUTIVE-RETIREMENT-001 | 대표이사 퇴직금은 퇴직 직전에 정한 금액도 비용일까? | 사전 규정, 실제 퇴직, 한도 초과의 상여 처리 |
  | CTA-LOSS-CARRYFORWARD-001 | 적자가 난 해의 결손금은 다음 해 이익과 바로 상계할까? | 세무상 결손금, 공제 순서·한도·이월 |

- [ ] **Step 2: 소득세법 다섯 원고를 작성한다**

  | issue_id | 제목 | 반드시 다룰 판단 경계 |
  | --- | --- | --- |
  | ITA-WITHHOLDING-PAYROLL-001 | 직원을 채용하면 급여를 전액 이체하기만 하면 될까? | 급여 지급, 원천징수, 지급명세서·원천세 신고 |
  | ITA-FAMILY-WAGE-001 | 배우자에게 준 급여는 모두 필요경비일까? | 실제 근무, 적정 보수, 출퇴근·업무·지급 증빙 |
  | ITA-RENTAL-INCOME-001 | 상가 월세와 보증금은 모두 같은 방식으로 소득이 될까? | 월세, 보증금, 간주임대료 및 필요경비 |
  | ITA-CAPITAL-GAINS-TIMING-001 | 부동산 잔금을 다음 해에 받으면 양도소득도 다음 해일까? | 대금청산일·등기일·예외적 계약 조건 |
  | ITA-CAPITAL-GAINS-COST-001 | 인테리어비와 중개수수료는 양도차익에서 모두 뺄 수 있을까? | 취득가액·자본적 지출·수익적 지출·증빙 |

- [ ] **Step 3: 부가가치세법 다섯 원고를 작성한다**

  | issue_id | 제목 | 반드시 다룰 판단 경계 |
  | --- | --- | --- |
  | VAT-INVOICE-PENALTY-001 | 세금계산서를 늦게 발급하면 부가세만 내면 끝일까? | 발급 시기, 수정세금계산서, 별도 가산세 |
  | VAT-CARD-SALES-001 | 카드매출은 세금계산서를 또 발급해야 할까? | 신용카드 매출전표와 세금계산서의 중복 |
  | VAT-DEEMED-INPUT-001 | 식당이 농산물을 사면 세금계산서가 없어도 공제받을까? | 의제매입세액공제 대상·증빙·한도 |
  | VAT-INVENTORY-TAX-TRANSITION-001 | 일반과세자에서 간이과세자로 바뀌면 재고 부가세는 어떻게 될까? | 전환일, 재고·감가상각자산, 신고서 |
  | VAT-BUSINESS-REGISTRATION-001 | 개업 뒤 사업자등록을 늦게 하면 매입세액도 못 받을까? | 등록 시기, 등록 전 매입세액 예외, 지연 가산세 |

- [ ] **Step 4: 각 원고에 아래의 최소 데이터 계약을 지킨다**

  ~~~json
  {
    "issue_id": "위 표의 식별자",
    "level": "beginner 또는 intermediate",
    "case_facts": "갑·을·병 또는 자연스러운 가상 법인명을 쓴 사실관계 한 문단",
    "question_blocks": [
      {
        "question": "사실관계의 주체와 행동, 판단 대상을 포함한 한 문장",
        "answer": "예·아니오 또는 조건부 결론으로 시작하는 직접 답",
        "explanation": "결론의 법적 이유와 수치·시기를 연결한 설명",
        "evidence": ["거래 실재와 법적 요건을 확인하는 자료"],
        "practical_note": "실제 신고 또는 조사 대응에 필요한 행동"
      }
    ]
  }
  ~~~

  사례 금액은 80,000,000원처럼 천 단위 구분 기호와 원 단위를 쓰고, 반복 질문·빈 안내글·시험형 문단은 넣지 않는다.

- [ ] **Step 5: 콘텐츠 계약 테스트를 다시 실행한다**

  Run: \`npx tsx --test tests/content-loader.test.ts\`

  Expected: PASS.

- [ ] **Step 6: 콘텐츠 변경을 커밋한다**

  ~~~bash
  git add content/issues.json content/learning-notes.json content/issue-selection.json content/articles.json
  git commit -m "content: add practical tax core issues"
  ~~~

### Task 5: 정적 출력과 문서를 검증한다

**Files:**
- Modify: README.md
- Test: tests/content-loader.test.ts
- Test: tests/issue-output.test.ts

- [ ] **Step 1: README에 78개 공개 노트라는 현재 상태를 명시한다**

  첫 설명 문단 뒤에 다음 문장을 넣는다.

  ~~~markdown
  현재 공개 목록은 78개 노트이며, 개수 목표가 아니라 실제 판단·증빙·신고에 필요한 쟁점만 확장한다.
  ~~~

- [ ] **Step 2: 전체 검증을 실행한다**

  Run: \`npm run verify\`

  Expected: TypeScript 검사, 정적 빌드, Node 콘텐츠 테스트와 브라우저 없는 출력 테스트가 모두 PASS한다.

- [ ] **Step 3: 정적 경로 수와 대표 노트 HTML을 확인한다**

  Run: \`find out/issues -mindepth 2 -maxdepth 2 -name index.html | wc -l\`

  Expected: \`78\`.

  Run: \`rg -n "대표가 법인 돈을 먼저 가져가면|부동산 잔금을 다음 해에 받으면|식당이 농산물을 사면" out/issues/*/index.html\`

  Expected: 각 제목이 하나 이상의 정적 HTML 파일에서 확인된다.

- [ ] **Step 4: 최종 문서·검증 변경을 커밋한다**

  ~~~bash
  git add README.md docs/superpowers/plans/2026-09-07-practical-tax-core-expansion.md
  git commit -m "docs: document practical tax core expansion"
  ~~~

### Task 6: 독립 검토, 병합, 공개 배포를 마무리한다

**Files:**
- Review: 전체 변경 파일

- [ ] **Step 1: 콘텐츠·법령 근거·모바일 경로를 독립 검토한다**

  검토자는 새 원고가 빈 문장·강제 수량·중복 사례 없이 질문과 답이 1:1로 이어지는지, 법령 카드가 주장에 필요한 예외까지 포함하는지, 대표 경로가 정적 산출물에 존재하는지를 확인한다.

- [ ] **Step 2: 검토 지적을 반영하고 전체 검증을 재실행한다**

  Run: \`npm run verify\`

  Expected: PASS.

- [ ] **Step 3: main 최신 상태와 통합한다**

  ~~~bash
  git fetch origin
  git merge origin/main
  git checkout main
  git merge --no-ff feat/practical-tax-core-expansion
  git push origin main
  ~~~

- [ ] **Step 4: GitHub Pages 배포를 확인한다**

  Run: \`gh run list --workflow deploy-pages.yml --branch main --limit 1\`

  Expected: 새 커밋의 배포 워크플로가 \`completed success\`가 된 뒤 https://wttear.github.io/tax-law-issues/ 에서 78개 노트가 공개된다.
