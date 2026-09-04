# 세법 쟁점 아틀라스 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 다섯 핵심 세법에서 10개씩 고른 50개 쟁점을 `전체 사실관계 → 질문별 판단` 흐름으로 읽는 별도 모바일 우선 정적 사이트를 만들고 GitHub Pages 게시 가능한 번들을 만든다.

**Architecture:** `content/`는 검증된 공개 학습 데이터, `scripts/bootstrap_content.py`는 기존 `tax-study` 공개 원천에서 50개 큐레이션 데이터를 한 번 추출하며, `scripts/build.py`는 그 데이터만 읽어 `docs/`에 독립 HTML을 생성한다. 각 쟁점은 사건 전체를 한 번 제공하는 `case_facts`와, 해당 사실의 일부를 가리켜 법령·판례·증빙·실무 결과를 붙이는 `question_blocks`로 표현한다. 문장 단위 자동 분할 대신 판단 단위의 사실 묶음을 사용하며, 학습자에게 노출되는 생성 안내문·메타 문구는 추출 단계에서 제거한다. 런타임 JavaScript는 법률·쟁점 필터만 담당하고, 사실관계·질문 블록·원문은 브라우저 기본 `details`만으로 JavaScript 없이 읽힌다. 기존 `tax-study`의 원장·템플릿·HTML은 수정하지 않는다.

**Tech Stack:** Python 3 표준 라이브러리, 정적 HTML5, CSS, 브라우저 기본 JavaScript, GitHub Pages.

---

### Task 1: 제품 기록·원천 데이터 추출

**Files:**
- Create: `PRODUCT.md`
- Create: `docs/writing-style.md`
- Create: `content/issue-selection.json`
- Create: `content/issues.json`
- Create: `content/articles.json`
- Create: `content/precedents.json`
- Create: `scripts/bootstrap_content.py`

- [x] 다섯 법률의 큐레이션 목록을 `content/issue-selection.json`에 법률별 정확히 10개씩 선언한다. 선택 목록에는 국세기본법의 납세의무·근거과세·입증·제척기간·가산세·세무조사·권리구제, 국세징수법의 납부지연·납기 전 징수·제2차 납세의무·압류·배분, 법인세법의 익금·손금·대손·감가상각·업무무관자산·특수관계·소득처분, 소득세법의 과세체계·거주자·소득구분·귀속시기·필요경비·공동사업·추계, 부가가치세법의 과세구분·공급·간주공급·사업양도·영세율·세금계산서·매입세액을 포함한다.
- [x] `bootstrap_content.py`가 `../tax-study/data/laws/learning.json`, 다섯 법률 JSON, 선택된 50개 lesson Markdown, 판례 인덱스를 읽어 issue ID를 중복 없이 모은다. 각 issue에는 법률코드, 제목, 핵심질문, `case_facts`, `question_blocks`, 공식 출처, source lesson provenance를 넣는다. 각 블록은 질문·판단할 사실 범위·관련 article ID·답·해설을 필수로 하고, 증빙·판례·회계/조정은 해당 판단에만 선택적으로 붙인다.
- [x] 원문은 선택된 article ID별로 `content/articles.json`에 한 번만 저장하고, 판례는 공식 URL·사건번호·선고일·판시요지·source provenance를 `content/precedents.json`에 한 번만 저장한다. URL은 `https://` 공식 기관만 허용하며 확인되지 않은 자료는 생략한다.
- [x] 기존 원고에서 사건 전체 사실관계를 한 번 추출하고, 문장별 분할 대신 서로 같은 판단요소를 설명하는 사실 묶음으로 보존한다. 화면용 내부 ID(`R1`, `R2`)는 제거하고, 질문 블록은 전체 사실의 관련 단락·문단을 가리킨다. 동일 사실을 질문 블록에서 전문으로 반복하지 않는다.
- [x] 질문 블록을 `질문 → 판단할 사실 범위 → 관련 조문 → 답 → 쉬운 해설 → 증빙·판례·실무 효과` 순서로 만든다. `앞서 확인한 사실`, `추가 사실 n`, `다음 단계에서 관련 판단을 더 구체화한다` 같은 문구는 생성하지 않는다.
- [x] 학습에 필요하지 않은 생성 지시·작업 메타(예: `완전 안내`, `부분 안내형`, `독립 해결형`, `VAT 실무 bridge`, `책임선`, `학습값`, `분개를 억지로 만들지 않고`, 고정 비중 문구)를 학습자용 텍스트에서 제거한다.
- [x] `docs/writing-style.md`에 Deslop·Slopspeare·Your Voice에서 참고한 편집 원칙과 출처를 기록하고, 생성 전후에 빈 서론·추상어·결론 반복·근거 없는 사실을 점검한다. 법률용어와 공식 문구는 정확성을 우선해 보존한다.
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
- [x] 쟁점 리더는 `오늘의 쟁점 → 사실관계 전문 → 핵심 질문 → 질문 1(판단할 사실 범위 → 관련 조문 → 답·해설) → 질문 2 ... → 최종 결론 → 판례·조사·회계 연결 → 사실이 달라지면` 순서로 렌더한다. 전체 사례는 처음에 한 번만 제시하고, 질문 블록에서는 관련 범위만 가리킨다. 시험형 요약은 독립 연습 데이터가 없으면 만들지 않는다.
- [x] 각 질문 블록은 질문을 `summary`로 먼저 노출하고, 펼친 뒤 `판단할 사실 범위`, `관련 조문(기본 접힘)`, `답과 해설` 순서를 지킨다. 전체 사실관계는 질문 블록보다 앞에 두며, `새 사실`·`R1/R2`·기계적인 판단지도 블록은 만들지 않는다.
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
- [x] 질문 블록은 모바일에서 세로로 이어지는 번호와 질문 제목만 먼저 보여 주고, 판단할 사실 범위·관련 조문·답을 한 블록씩 펼치게 한다. 원문은 해당 블록의 `details` 안에서만 기본 접힘으로 제공한다.
- [x] 긴 원문·판례·표는 모바일에서 한 열로 쌓고, 표 셀에는 `data-label`을 넣어 행 라벨을 표시한다. `prefers-reduced-motion`과 print 스타일에서 콘텐츠 순서를 보존한다.

### Task 4: 빌드·정적 품질 검증

**Files:**
- Create: `README.md`
- Create: `DESIGN.md`
- Modify: `tests/test_build.py`

- [x] `python3 scripts/build.py`를 실행해 산출물을 만든다.
- [x] `python3 -m unittest discover -s tests -p 'test_*.py' -v`를 실행해 전체 테스트가 0 failures인지 확인한다.
- [x] 테스트는 모든 issue에 전체 사실관계와 2개 이상의 질문 블록 및 필수 필드(question/fact_scope/legal_refs/answer)가 있는지, 생성된 DOM이 사실관계→질문→관련 조문→답 순서인지 검증한다.
- [x] 테스트는 학습자용 HTML·JSON에 금지된 생성 안내문과 고정 비중 메타가 남지 않았는지, 질문 문장이 빈칸이거나 작성자 지시형으로 끝나지 않는지 검증한다.
- [x] `python3 -m http.server 4173 --directory docs`로 로컬 정적 서버를 열고 `/`, 대표 issue URL, 존재하지 않는 issue 경로의 동작을 curl로 확인한다. 서버에 의존하는 링크나 API 호출이 없어야 한다.
- [x] `node /home/gqz1xer/.codex/skills/impeccable/scripts/detect.mjs --json docs/index.html docs/issues/NTBA-TAX-LIABILITY-LIFECYCLE-001/index.html docs/styles.css docs/site.js`를 한 번 실행하고 기계적 오류를 수정한다.
- [x] 빌드된 세계를 기준으로 `DESIGN.md`에 색·타이포그래피·대장 구조·모바일 계약·페이지 방향 계약을 기록한다. 제품 주장이나 실재하지 않는 통계는 넣지 않는다.

### Task 5: 별도 GitHub Pages 게시

**Files:**
- Create: `.gitignore`
- Create: `.tax-law-issues-public`

- [x] 새 디렉터리에서 `git init -b main`을 실행하고 marker 내용이 `tax-law-issues-public-v1`인지 확인한다. 공개 stage 대상은 `.tax-law-issues-public`, `PRODUCT.md`, `README.md`, `DESIGN.md`, `content/`, `scripts/`, `src/`, `tests/`, `docs/`로 제한한다.
- [x] GitHub CLI/remote 인증 상태를 확인한 뒤 사용자 계정의 public repository를 만들고 origin을 연결한다. 인증 토큰이나 납세자 자료를 파일·명령·출력에 남기지 않는다.
- [x] `docs/` 번들을 commit·push하고 Pages source가 `main:/docs`인 공개 주소에서 새 HTML을 확인한다. 원격 `main` SHA와 게시된 순차 HTML을 대조한 뒤 공개 URL을 전달한다.
- [x] 인증이 만료되거나 Pages 빌드가 실패하면 로컬 사이트와 기존 `tax-study` 사이트를 보존하고, 공개 URL이 게시됐다고 말하지 않는다. 사용자에게 필요한 재인증 명령만 안내한다.

### Task 6: 사실관계 전문 우선·학습자용 문구 정리

**Files:**
- Modify: `scripts/bootstrap_content.py`
- Modify: `scripts/build.py`
- Modify: `src/site.css`
- Modify: `tests/test_build.py`
- Generate: `content/issues.json`, `content/articles.json`, `content/precedents.json`, `docs/index.html`, `docs/issues/*/index.html`, `docs/styles.css`

- [x] 각 issue에 원문 `사실` 단락을 `case_facts`로 한 번 저장하고, 질문 블록은 이를 공통 배경으로 참조한다. 문장별 `새 사실` 배열과 `앞서 확인한 사실` 의존 질문을 제거한다.
- [x] 질문 블록은 쟁점별로 2개 이상 만들되 `질문 → 판단할 사실 범위 → 관련 조문 → 답 → 쉬운 해설 → 증빙·판례·실무 효과` 순서를 사용한다. 질문은 주체·행위·법적 판단을 직접 적고, 자동 문구를 재사용하지 않는다.
- [x] 전체 사실관계는 질문보다 앞에 렌더하고, 모바일에서는 `사실관계` 앵커로 돌아갈 수 있게 한다. 질문마다 사실 전문을 복사하지 않는다.
- [x] `요약 안내`, `잠정 결론을 적으세요`, `새 사실을 하나씩 확인하세요`, `추가 사실 n`, `다음 단계에서 관련 판단을 더 구체화한다`, `완전 안내`, `부분 안내형`, `독립 해결형`, `VAT 실무 bridge`, `책임선`, `학습값`, `분개를 억지로 만들지 않고` 등 학습에 직접 필요 없는 생성·진행 안내문을 데이터와 HTML에서 제거한다. `학습자료·학습금액·교육문제·학습상·학습 기준·보여 줘야 한다`처럼 원고 제작 과정을 드러내는 표현도 사실·답·판례 문맥에 맞는 중립어로 치환한다.
- [x] 법령은 질문별 법적 기능(근거·요건·예외·효과)을 붙여 표시하고, 판례·증빙·회계 연결은 해당 질문의 판단을 설명할 때만 노출한다. 연결 정보가 없는 경우 추정 문구를 만들지 않는다.
- [x] 질문 블록의 답과 마지막 요약은 조문 번호만 남기는 빈 fallback을 허용하지 않고, 판단 문장 또는 세무상 효과를 최소 한 문장으로 제공한다.
- [x] 전수 재생성 후 50개 issue, 각 법률 10개, 사실관계 선행, 질문 블록 선행, 금지 문구 부재, 공식 URL, HTML 구조와 모바일 줄바꿈을 자동 검증한다.

### Task 7: 질문·답 정렬 단위

**Files:**
- Modify: `scripts/bootstrap_content.py`
- Modify: `scripts/build.py`
- Modify: `src/site.css`
- Modify: `tests/test_build.py`
- Generate: `content/issues.json`, `docs/issues/*/index.html`, `docs/styles.css`

- [x] `답안 핵심요소`의 법리 구분·증빙 선택·새 사실 전이와 판단 과정의 산식을 각각 하나의 `judgment_type` 단위(`rule`, `calculation`, `evidence`, `change`)로 만든다.
- [x] 질문을 먼저 독립적으로 뽑아 답에 붙이지 않고, 같은 판단 단위의 결론·금액·증빙·변경 조건에서 질문을 생성한다. 따라서 한 질문은 하나의 판단 또는 계산만 묻고 답은 그 질문의 결론만 설명한다.
- [x] 출처의 작성 지시형 표현을 중립적인 결론형 문장으로 정리하고, 파티클·날짜·조문 번호가 어색하게 이어지는 질문은 생성 단계에서 정규화한다.
- [x] 질문과 답에 구체 명사·금액·조문 등 공통 단서가 두 개 이상 있는지 전수 테스트하고, 질문 제목에 법리·계산·증빙·조건 변경 유형을 표시한다.
