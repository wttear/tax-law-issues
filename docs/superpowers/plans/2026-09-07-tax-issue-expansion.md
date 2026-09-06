# 실무 세법 쟁점 확장 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 50개 노트와 겹치지 않는 실무 핵심 세법 쟁점을 현행 법령 근거와 함께 공개 목록에 추가한다.

**Architecture:** 기존 `issues.json`은 공개 쟁점의 안정적인 ID·법령 분류만 유지하고, 독자가 읽는 원고는 `learning-notes.json`의 검수본으로 덮어쓴다. 조문 원문은 `articles.json`의 현행 확인본으로 분리하고, 판례는 해당 판단의 경계를 실제로 설명할 때만 `precedents.json`에 연결한다. 목록과 라우팅은 `lib/content.ts`의 동적 카탈로그를 그대로 사용하므로 UI 구조를 바꾸지 않는다.

**Tech Stack:** Next.js 16 static export, TypeScript, Tailwind CSS, shadcn/ui, Node test runner, GitHub Pages.

---

## 선정 기준

법률별 수를 맞추지 않는다. 아래 항목은 기존 50개가 이미 다루는 납세의무·수정신고·세무조사, 압류·배분, 손금일반·감가상각·특수관계 거래, 소득구분·기장, 세금계산서·매입세액과 **다른 실제 판단 단위**여서 추가한다.

| 법령 | 새 공개 ID | 중심 질문 | 선택 이유 |
| --- | --- | --- | --- |
| 국세기본법 | `NTBA-CORRECTION-CLAIM-001` | 세금을 더 냈다는 사실을 나중에 알면 돌려받을 수 있을까? | 수정신고와 반대 방향의 경정청구가 빠져 있다. |
| 국세기본법 | `NTBA-PRE-ASSESSMENT-REVIEW-001` | 과세예고를 받으면 고지 전에 반박할 수 있을까? | 세무조사 이후, 처분 전의 대응 단계가 비어 있다. |
| 국세기본법 | `NTBA-APPEAL-DEADLINE-001` | 고지서를 받은 뒤 불복 90일은 언제부터 셀까? | 처분 후 권리구제의 출발일·절차 선택을 별도 판단으로 익힌다. |
| 국세징수법 | `NCTA-PAYMENT-EXTENSION-001` | 자금난이면 세금을 나누어 낼 수 있을까? | 체납 전의 납부기한 연장·분할납부 판단이 없다. |
| 국세징수법 | `NCTA-SEIZURE-RELEASE-001` | 체납액을 냈는데 통장은 언제 풀릴까? | 압류 이후의 해제 요건과 일부해제를 구분한다. |
| 법인세법 | `CTA-SALES-PROMOTION-001` | 거래처 판촉비는 기업업무추진비일까, 판매비일까? | 판매와 직접 연결된 지급과 접대성 지출을 구분한다. |
| 법인세법 | `CTA-OFFICER-BONUS-001` | 결산 뒤 대표이사 성과급을 비용 처리할 수 있을까? | 임원 상여의 사전 기준·이익처분을 실제 결산 흐름에 연결한다. |
| 법인세법 | `CTA-BUSINESS-CAR-001` | 법인 명의 승용차 비용은 모두 비용일까? | 업무전용보험·번호판·운행기록·한도라는 반복 실무 판단을 다룬다. |
| 소득세법 | `ITA-BUSINESS-ACCOUNT-001` | 개인사업자 통장을 사업용계좌로 신고해야 할까? | 복식부기의무자의 자금 흐름과 증빙을 연결한다. |
| 소득세법 | `ITA-WORKER-OR-FREELANCER-001` | 출근하는 프리랜서를 3.3% 사업소득으로 처리해도 될까? | 계약 명칭이 아닌 실제 근로 제공 관계를 판단한다. |
| 부가가치세법 | `VAT-CORRECTED-INVOICE-001` | 판매 후 반품이 생기면 세금계산서를 어떻게 고칠까? | 반품·계약해제·가격변동의 작성일과 수정 방식이 빠져 있다. |
| 부가가치세법 | `VAT-BAD-DEBT-CREDIT-001` | 외상매출을 못 받으면 이미 낸 부가세를 돌려받을까? | 회계상 대손과 VAT 대손세액공제의 요건·시점을 구분한다. |
| 부가가치세법 | `VAT-SIMPLIFIED-TAXPAYER-001` | 매출이 작으면 자동으로 간이과세자가 될까? | 적용 기준·제외 업종·전환 시점을 기초 실무 판단으로 제공한다. |

### Task 1: 확장 항목을 먼저 검증하는 실패 테스트 작성

**Files:**
- Modify: `tests/content-loader.test.ts`
- Modify: `tests/issue-output.test.ts`

- [x] **Step 1: 공개 카탈로그의 신규 ID와 핵심 경계를 요구하는 테스트를 추가한다.**

```ts
test("the practical expansion adds only reviewed, source-backed issue notes", () => {
  const ids = [
    "NTBA-CORRECTION-CLAIM-001",
    "NCTA-PAYMENT-EXTENSION-001",
    "CTA-OFFICER-BONUS-001",
    "ITA-BUSINESS-ACCOUNT-001",
    "VAT-CORRECTED-INVOICE-001",
  ];
  for (const id of ids) assert.ok(getIssue(id));
  assert.match(getIssue("NTBA-CORRECTION-CLAIM-001")?.question_blocks[0].answer ?? "", /5년/);
  assert.match(getIssue("CTA-BUSINESS-CAR-001")?.question_blocks[0].answer ?? "", /업무전용자동차보험/);
  assert.match(getIssue("VAT-BAD-DEBT-CREDIT-001")?.question_blocks[1].answer ?? "", /110분의 10/);
});
```

- [x] **Step 2: 정적 HTML에 대표적인 새 질문·결론·현행 조문 카드가 나타나는 테스트를 추가한다.**

```ts
test("expanded notes render direct questions, current rules, and no template filler", () => {
  const correction = readFileSync("out/issues/NTBA-CORRECTION-CLAIM-001/index.html", "utf8");
  const invoice = readFileSync("out/issues/VAT-CORRECTED-INVOICE-001/index.html", "utf8");
  assert.match(correction, /세금을 더 냈다는 사실을 나중에 알면/);
  assert.match(correction, /경정 등의 청구/);
  assert.match(invoice, /반품된 날/);
  assert.match(invoice, /수정세금계산서/);
});
```

- [x] **Step 3: 새 테스트가 아직 없는 라우트 때문에 실패하는지 확인한다.**

Run: `node --import tsx --test tests/content-loader.test.ts`

Expected: `getIssue(...)`가 없다는 assertion failure.

### Task 2: 현행 조문·판례 근거 카드 추가

**Files:**
- Modify: `content/articles.json`
- Modify: `content/precedents.json`

- [x] **Step 1: 다음 조문만 현행 확인본으로 추가하고, 원문 URL·시행일·확인일·원문 해시를 함께 기록한다.**

```text
NTBA-45-2 (국세기본법 제45조의2), NTBA-61, NTBA-68,
NCTA-13,
CTA-25, CTAE-43, CTA-27-2, CTAE-50-2,
ITA-160-5,
VAT-45, VATE-70, VATE-87, VAT-61, VATE-109
```

선택 원문에는 노트에서 실제 사용하는 항·호만 넣는다. `source_sha256`은 저장한 `text`의 SHA-256으로 계산하고, 모든 링크는 국가법령정보센터의 현행 조문으로 한다.

- [x] **Step 2: 판매촉진비의 실질을 보여 주는 서울행정법원 2014구합53445 판결만 판례 카드로 추가한다.**

판례 카드에는 과거 접대비 규정하의 사건이라는 한계, 일정 구매조건을 붙였어도 여행 지원의 성질·상대방·규모 때문에 접대비로 본 사실, 현재 기업업무추진비 판단에 기계적으로 적용하면 안 된다는 설명을 넣는다.

- [x] **Step 3: 새 카드의 URL과 원문이 실제 ID로 조회되는지 확인한다.**

Run: `node --import tsx --test tests/content-loader.test.ts`

Expected: Task 1의 신규 issue assertions만 실패하고, 누락된 조문 ID 오류는 없다.

### Task 3: 공개 쟁점 인벤토리와 검수 원고 추가

**Files:**
- Modify: `content/issues.json`
- Modify: `content/learning-notes.json`
- Modify: `content/issue-selection.json`

- [x] **Step 1: `issues.json`에 Task 1의 13개 ID를 추가한다.**

각 항목은 올바른 `law_code`, 법령명, 법령 내 다음 `position`, 조문 ID, 관련 판례 ID를 가진다. 법령별 `issue_count`·`issue_ids`는 실제 값으로 갱신한다. 전체 `article_count`와 `precedent_count`도 실제 데이터 수와 맞춘다.

- [x] **Step 2: `learning-notes.json`에 13개 검수 원고를 추가한다.**

각 원고는 다음 순서를 지킨다.

```text
제목 → 사실관계 전문(한 문단) → 질문 하나 → 바로 답과 초보자 해설 →
그 질문에 필요한 법령·자료·회계 메모 → 다음 질문
```

사실에는 `갑·을·병` 또는 업종에 맞는 가상 법인만 사용하고, 금액은 `45,000,000원`처럼 적는다. 질문 수·사례 수·판례 수를 맞추지 않는다. 질문은 질문 자체만 읽어도 누구·무엇·어떤 결론을 묻는지 알 수 있게 쓴다.

- [x] **Step 3: 쟁점별 핵심 경계를 반영한다.**

```text
경정청구: 과다 신고·세액공제 누락과 5년, 후발적 사유의 3개월을 구별.
과세전적부심사: 과세예고·조사결과 통지 후 30일, 예외 사유를 구별.
불복기한: 처분을 안 날/받은 날부터 90일, 심사·심판 중복 금지를 설명.
납부기한 연장: 자금난만의 선언이 아니라 현저한 손실·부도 우려와 증빙을 연결.
압류해제: 전액 납부·취소의 즉시 해제와 일부 납부의 재량적 일부해제를 구분.
판촉비: 거래 상대방의 구매·판매와 직접 연동되는지와 접대 목적을 구별.
임원 성과급: 사전 급여기준·지급액·결산 뒤 이익처분을 구별.
업무용승용차: 보험·번호판·운행기록, 운행기록 부재 시 15,000,000원 기준, 감가상각 8,000,000원 한도를 단계로 설명.
사업용계좌: 복식부기의무자 여부, 계좌 신고, 금융거래·인건비·임차료의 흐름을 구분.
근로자/프리랜서: 계약서의 명칭이 아니라 지휘·감독, 근무시간·장소, 보수 구조와 독립성 확인.
수정세금계산서: 환입일·계약해제일·가격 증감일을 각각 작성일로 연결.
대손세액: 단순 연체와 대손 확정 사유를 구분하고 `대손금액 × 10 ÷ 110`을 계산.
간이과세: 개인사업자·직전연도 공급대가·104,000,000원 미만, 임대/유흥 48,000,000원 경계와 제외 업종·전환 시점을 구분.
```

- [x] **Step 4: 유효성 검사가 모든 공개 ID에 검수 원고가 있음을 확인하는지 실행한다.**

Run: `node --import tsx --test tests/content-loader.test.ts`

Expected: PASS.

### Task 4: 공개 메타데이터와 문서의 고정 개수 표현 정리

**Files:**
- Modify: `README.md`
- Modify: `DESIGN.md`

- [x] **Step 1: README의 “법령별 10개” 설명을 실제 공개 목록과 검수 원고 기준이라는 설명으로 바꾼다.**

- [x] **Step 2: DESIGN의 과거 10개 고정 목록 설명을 초기 공개분의 기록으로 한정하고, 이후에는 중복되지 않는 판단 단위만 추가한다고 명시한다.**

- [x] **Step 3: 역사 문서인 이전 실행계획은 과거 결정 기록으로 남기고 현재 제품 설명으로 인용하지 않는다.**

### Task 5: 정적 결과·전체 검증·검토

**Files:**
- Verify: `out/issues/NTBA-CORRECTION-CLAIM-001/index.html`, `out/issues/CTA-BUSINESS-CAR-001/index.html`, `out/issues/VAT-CORRECTED-INVOICE-001/index.html`
- Test: `tests/content-loader.test.ts`
- Test: `tests/issue-output.test.ts`

- [x] **Step 1: 전체 빌드로 새 경로를 생성한다.**

Run: `npm run build`

Expected: 새 13개 ID를 포함한 66개 정적 경로가 생성된다.

- [x] **Step 2: 정적 HTML 회귀 테스트를 실행한다.**

Run: `node --import tsx --test tests/issue-output.test.ts`

Expected: PASS.

- [x] **Step 3: 전체 검증을 실행한다.**

Run: `npm run verify && git diff --check && git status --short`

Expected: 모든 TypeScript·정적 출력·계약 테스트가 통과하고 공백 오류가 없다.

- [x] **Step 4: 변경 내용과 출처를 재검토한 뒤 한 개의 콘텐츠 확장 커밋으로 저장한다.**

```bash
git add content tests README.md DESIGN.md docs/superpowers/plans/2026-09-07-tax-issue-expansion.md
git commit -m "content: expand practical tax issue library"
```

### Task 6: main 병합 및 GitHub Pages 배포

**Files:**
- Verify: `.github/workflows/deploy.yml`

- [ ] **Step 1: 원격 `main`을 가져와 선형 병합이 가능한지 확인한다.**

```bash
git fetch origin
git -C /mnt/d/workspace/세법/tax-law-issues merge --no-ff feat/tax-issue-expansion
```

- [ ] **Step 2: main에서 `npm run verify`를 다시 실행한다.**

- [ ] **Step 3: main을 푸시하고 GitHub Pages 배포 워크플로가 성공하는지 확인한다.**

- [ ] **Step 4: 배포가 성공한 뒤에만 정확한 신규 쟁점 수, 검증 결과, 공개 URL을 보고하고 작업 브랜치·worktree를 정리한다.**
