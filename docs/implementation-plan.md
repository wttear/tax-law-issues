# 세법 쟁점 아틀라스 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 다섯 핵심 세법에서 10개씩 고른 50개 쟁점을 법령 원문·판단·증빙·판례 흐름으로 읽는 별도 모바일 우선 정적 사이트를 만들고 GitHub Pages 게시 가능한 번들을 만든다.

**Architecture:** `content/`는 검증된 공개 학습 데이터, `scripts/bootstrap_content.py`는 기존 `tax-study` 공개 원천에서 50개 큐레이션 데이터를 한 번 추출하며, `scripts/build.py`는 그 데이터만 읽어 `docs/`에 독립 HTML을 생성한다. 런타임 JavaScript는 법률·쟁점 필터만 담당하고, 원문과 각 쟁점 페이지는 JavaScript 없이도 읽힌다. 기존 `tax-study`의 원장·템플릿·HTML은 수정하지 않는다.

**Tech Stack:** Python 3 표준 라이브러리, 정적 HTML5, CSS, 브라우저 기본 JavaScript, GitHub Pages.

---

### Task 1: 제품 기록·원천 데이터 추출

**Files:**
- Create: `PRODUCT.md`
- Create: `content/issue-selection.json`
- Create: `content/issues.json`
- Create: `content/articles.json`
- Create: `content/precedents.json`
- Create: `scripts/bootstrap_content.py`

- [x] 다섯 법률의 큐레이션 목록을 `content/issue-selection.json`에 법률별 정확히 10개씩 선언한다. 선택 목록에는 국세기본법의 납세의무·근거과세·입증·제척기간·가산세·세무조사·권리구제, 국세징수법의 납부지연·납기 전 징수·제2차 납세의무·압류·배분, 법인세법의 익금·손금·대손·감가상각·업무무관자산·특수관계·소득처분, 소득세법의 과세체계·거주자·소득구분·귀속시기·필요경비·공동사업·추계, 부가가치세법의 과세구분·공급·간주공급·사업양도·영세율·세금계산서·매입세액을 포함한다.
- [x] `bootstrap_content.py`가 `../tax-study/data/laws/learning.json`, 다섯 법률 JSON, 선택된 50개 lesson Markdown, 판례 인덱스를 읽어 issue ID를 중복 없이 모은다. 각 issue에는 법률코드, 제목, 핵심질문, 법령 article ID, 쉬운 설명, 판단지도, 세무조사 가설·증빙, 회계/조정(있을 때만), 판례 ID, 공식 출처, source lesson provenance를 넣는다.
- [x] 원문은 선택된 article ID별로 `content/articles.json`에 한 번만 저장하고, 판례는 공식 URL·사건번호·선고일·판시요지·source provenance를 `content/precedents.json`에 한 번만 저장한다. URL은 `https://` 공식 기관만 허용하며 확인되지 않은 자료는 생략한다.
- [x] 실행 후 `python3 scripts/bootstrap_content.py --source-root ../tax-study`가 `50개`와 법률별 `10개`를 출력하게 한다. 어느 법률이든 10개가 아니거나 source lesson·article·official URL이 빠지면 실패하도록 한다.

### Task 2: 정적 HTML 빌더

**Files:**
- Create: `src/index.html`
- Create: `src/issue.html`
- Create: `scripts/build.py`
- Create: `tests/test_build.py`
- Generate: `docs/index.html`, `docs/issues/*/index.html`, `docs/styles.css`, `docs/site.js`, `docs/.nojekyll`

- [x] `build.py`가 `content/*.json`을 strict UTF-8 JSON으로 읽고 모든 사용자·원천 텍스트를 HTML escape한다. 출력은 `docs/index.html` 한 개와 50개 `docs/issues/{issue_id}/index.html`이며 공식 링크 외의 외부 자원을 삽입하지 않는다.
- [x] 인덱스에는 제목·5개 법률 띠·각 법률 10개 쟁점 행·검색 입력·법률 필터·결과 수·읽는 순서를 정적 HTML로 먼저 넣는다. 각 행은 실제 issue URL을 가진다.
- [x] 쟁점 리더는 `답을 보기 전 → 법령 원문과 기준일 → 초보자 해설 → 판단 지도 → 합성 사례·증빙 → 관련 판례 → 필요한 경우 회계·세무조정 → 출처` 순서로 렌더한다. 시험형 요약은 독립 연습 데이터가 없으면 만들지 않는다.
- [x] 각 페이지 body 첫 자식에 다음 방향 계약을 HTML 주석으로 넣는다: `THESIS`, `OWN-WORLD`, `STORY`, `FIRST VIEWPORT`, `FORM`과 `FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md`.
- [x] `tests/test_build.py`는 법률별 10개·전체 50개, 51개 HTML, 각 issue 링크의 존재, 하나의 h1, skip link, official URL, 금지된 `localhost`·`file://`·raw state 문자열 부재를 검증한다.

### Task 3: 모바일 Read-mode UX/UI

**Files:**
- Modify: `src/index.html`
- Modify: `src/issue.html`
- Create: `src/site.css`
- Create: `src/site.js`

- [x] 기존 사건배당부의 석재·종이·잉크·공식 파랑·규선 언어를 상속하되, 인덱스는 카드 벽 대신 법률별 대장 행을 사용한다. 그림자·그라데이션·이모지 아이콘·햄버거 메뉴를 쓰지 않는다.
- [x] 390px에서 body 17px, 최대 68ch, `overflow-wrap:anywhere`, 링크·입력·summary 최소 44px, 키보드 focus-visible, `main` landmark, 본문 건너뛰기 링크를 보장한다.
- [x] 인덱스 필터는 결과 수와 활성 법률을 갱신하고, 필터 실패나 JavaScript 미지원 시에도 50개 행과 실제 링크가 남는다. issue 페이지는 JS 없이 원문·해설·판례를 읽는다.
- [x] 긴 원문·판례·표는 모바일에서 한 열로 쌓고, 표 셀에는 `data-label`을 넣어 행 라벨을 표시한다. `prefers-reduced-motion`과 print 스타일에서 콘텐츠 순서를 보존한다.

### Task 4: 빌드·정적 품질 검증

**Files:**
- Create: `README.md`
- Create: `DESIGN.md`
- Modify: `tests/test_build.py`

- [x] `python3 scripts/build.py`를 실행해 산출물을 만든다.
- [x] `python3 -m unittest discover -s tests -p 'test_*.py' -v`를 실행해 전체 테스트가 0 failures인지 확인한다.
- [x] `python3 -m http.server 4173 --directory docs`로 로컬 정적 서버를 열고 `/`, 대표 issue URL, 존재하지 않는 issue 경로의 동작을 curl로 확인한다. 서버에 의존하는 링크나 API 호출이 없어야 한다.
- [x] `node /home/gqz1xer/.codex/skills/impeccable/scripts/detect.mjs --json docs/index.html docs/issues/NTBA-TAX-LIABILITY-LIFECYCLE-001/index.html docs/styles.css docs/site.js`를 한 번 실행하고 기계적 오류를 수정한다.
- [x] 빌드된 세계를 기준으로 `DESIGN.md`에 색·타이포그래피·대장 구조·모바일 계약·페이지 방향 계약을 기록한다. 제품 주장이나 실재하지 않는 통계는 넣지 않는다.

### Task 5: 별도 GitHub Pages 게시

**Files:**
- Create: `.gitignore`
- Create: `.tax-law-issues-public`

- [x] 새 디렉터리에서 `git init -b main`을 실행하고 marker 내용이 `tax-law-issues-public-v1`인지 확인한다. 공개 stage 대상은 `.tax-law-issues-public`, `PRODUCT.md`, `README.md`, `DESIGN.md`, `content/`, `scripts/`, `src/`, `tests/`, `docs/`로 제한한다.
- [ ] GitHub CLI 인증 상태를 확인한 뒤 사용자 계정의 새 public repository를 만들고 origin을 연결한다. 인증 토큰이나 납세자 자료를 파일·명령·출력에 남기지 않는다.
- [ ] `docs/` 번들을 commit·push하고 Pages source가 `main:/docs`인지 확인한다. remote main SHA와 게시 build commit이 같고 Pages status가 `built`일 때만 공개 URL을 전달한다.
- [x] 인증이 만료되거나 Pages 빌드가 실패하면 로컬 사이트와 기존 `tax-study` 사이트를 보존하고, 공개 URL이 게시됐다고 말하지 않는다. 사용자에게 필요한 재인증 명령만 안내한다.
