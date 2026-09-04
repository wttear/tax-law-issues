# Next.js 정적 전환 설계

## 목표

현재 공개 중인 세법 쟁점 대장의 50개 학습 문서와 모바일 읽기 흐름을 유지하면서, 화면·라우팅·빌드를 Next.js App Router 기반으로 전환한다. 결과물은 별도 서버 없이 GitHub Pages에서 무료로 제공하고, 기존 `tax-study` 사이트와 그 진도 상태에는 손대지 않는다.

## 확정된 범위

이번 전환에 포함한다.

- 메인 법률 목록과 쟁점 검색·법률 필터
- `/issues/[issueId]/` 형태의 50개 쟁점 상세 경로
- 사실관계 전문 → 질문별 판단 → 판례·조사·회계 연결의 현재 읽기 순서
- `content/*.json`에 있는 50개 쟁점, 조문, 판례 데이터의 재사용
- 모바일 반응형 스타일, 키보드 초점, 스킵 링크, JavaScript 비활성 상태의 기본 열람
- GitHub Pages용 정적 export와 자동 배포

이번 전환에는 포함하지 않는다.

- 새 법률·쟁점 원고 작성이나 판례 내용 변경
- 로그인, 학습 완료 상태, `localStorage`, 사용자별 진도
- 데이터베이스, API 라우트, 서버 액션, 결제 또는 관리자 화면
- 기존 `tax-study`의 HTML·템플릿·원장 수정
- Vercel 서버 런타임 또는 유료 인프라 도입

## 접근법과 선택 이유

### 선택안 A — Next.js App Router + TypeScript + 정적 export (선택)

`app/` 라우트가 JSON 콘텐츠를 빌드 시 읽고, 50개 상세 페이지를 모두 정적으로 생성한다. 검색과 필터처럼 브라우저 상태가 필요한 메인 목록만 작은 클라이언트 컴포넌트로 만든다. Next.js의 서버 컴포넌트 기본 동작을 사용하므로 상세 페이지에는 불필요한 클라이언트 번들이 들어가지 않는다.

`output: 'export'`로 생성한 `out/`을 GitHub Pages Actions가 게시한다. 공개 주소는 현재의 `https://wttear.github.io/tax-law-issues/`와 쟁점별 trailing slash 경로를 유지한다. TypeScript 타입과 빌드 시 데이터 검증으로 쟁점 블록 필드가 빠지면 배포 전에 실패하게 한다.

### 선택안 B — 기존 Python HTML 빌더와 Next.js를 병행

기존 `scripts/build.py`가 계속 화면을 만들고 Next.js는 일부 화면만 담당한다. 단기 위험은 낮아 보이지만 동일한 정보 구조와 CSS를 두 렌더러에서 관리해야 하며, 어느 결과물이 실제 공개본인지 혼란이 생긴다. 장기 유지보수 비용이 커서 선택하지 않는다.

### 선택안 C — Next.js 서버 배포

Vercel 같은 서버 런타임으로 SSR·API를 사용할 수 있다. 그러나 현재 콘텐츠는 모두 공개 JSON이고 사용자 상태도 필요하지 않다. GitHub Pages 무료 주소와 현재 운영 방식을 바꾸므로 이번 범위에서는 선택하지 않는다.

## 기술 스택

- Next.js App Router
- React와 React DOM
- TypeScript
- CSS 전역 스타일시트(`app/globals.css`로 이관)
- JSON 콘텐츠 스냅샷
- Python 3 표준 라이브러리: 기존 원천자료 추출·콘텐츠 재생성
- Node.js LTS와 npm lockfile
- GitHub Pages + GitHub Actions

런타임에는 데이터베이스나 외부 API가 없으며, 사이트가 로드될 때 공식 법령·판례 링크를 제외한 외부 리소스를 요청하지 않는다.

## 애플리케이션 구조

```text
tax-study 공개 원천
        │
        ▼
scripts/bootstrap_content.py
        │
        ▼
content/issues.json · articles.json · precedents.json
        │
        ▼
lib/content.ts  ── 타입/필수 필드 검증
        │
        ├── app/page.tsx                    메인 대장(서버 컴포넌트)
        ├── components/issue-browser.tsx    검색·법률 필터(클라이언트)
        └── app/issues/[issueId]/page.tsx   50개 정적 상세 페이지
        │
        ▼
next build → out/
        │
        ▼
GitHub Pages Actions → https://wttear.github.io/tax-law-issues/
```

권장 파일 경계는 다음과 같다.

- `app/layout.tsx`: 문서 언어, viewport, 공통 메타데이터, 전역 CSS
- `app/page.tsx`: 법률 섹션과 정적 쟁점 행의 서버 렌더링
- `app/issues/[issueId]/page.tsx`: `generateStaticParams`, 메타데이터, 쟁점 리더
- `app/not-found.tsx`: 존재하지 않는 쟁점 경로의 읽기 쉬운 404와 대장 복귀 링크
- `components/issue-browser.tsx`: 검색어·법률 필터·결과 수를 관리하는 유일한 클라이언트 컴포넌트
- `components/issue-reader.tsx`: 사실관계, 질문 블록, 조문 `details`, 판례·조사·회계 카드를 표시
- `lib/content.ts`: JSON 로드, 법률별 목록, issue ID 조회, 공식 URL 허용목록, 필수 구조 검증
- `types/content.ts`: 법률·쟁점·질문 블록·조문·판례의 타입
- `app/globals.css`: 현재 `src/site.css`의 시각 언어와 모바일 규칙을 이관
- `next.config.mjs`: 정적 export, `basePath: '/tax-law-issues'`, `trailingSlash: true`, 정적 이미지 설정
- `.github/workflows/deploy-pages.yml`: Node 설치, `npm ci`, 콘텐츠 생성, Next 빌드, `out/` Pages artifact 업로드·배포

기존 `src/site.js`의 검색·필터 로직은 `issue-browser.tsx`로 옮기되, 서버가 모든 행과 실제 링크를 먼저 출력한다. 따라서 JavaScript가 꺼져도 목록·제목·상세 링크·원문 링크는 읽을 수 있다.

## 라우팅과 정적 생성

- `/`는 다섯 법률과 각 10개 쟁점을 표시한다.
- `/issues/{issue_id}/`는 `content/issues.json`의 모든 ID에 대해 `generateStaticParams()`로 생성한다.
- 상세 페이지는 `case_facts`를 한 번 표시한 뒤 각 `question_blocks`를 질문 → 판단할 사실 범위 → 관련 조문 → 답·해설 → 증빙·판례·회계 순서로 렌더링한다.
- `notFound()`는 데이터에 없는 ID에서 호출하며, Pages에서는 정적 `404.html`로 처리한다.
- 공식 외부 링크는 `https://`와 허용 호스트(`law.go.kr`, `scourt.go.kr`, `kasb.or.kr`)를 모두 통과한 경우에만 링크로 만든다. 나머지는 URL을 표시하지 않는다.
- `basePath`와 `trailingSlash`를 이용해 GitHub Pages 프로젝트 경로와 기존 trailing slash URL을 보존한다. 내부 이동은 Next.js `Link`를 사용한다.

## 배포와 무료 운영

GitHub Free 공개 저장소의 GitHub Pages를 사용한다. Actions는 `out/`만 Pages artifact로 올리므로 소스 저장소의 `content/`와 앱 코드는 공개 저장소에 남고, 별도 서버 비용은 없다. 저장소 Settings의 Pages source를 GitHub Actions로 한 번 전환하면 이후 `main` push 때 자동 배포한다.

배포 워크플로에는 다음 권한과 순서를 고정한다.

1. `contents: read`, `pages: write`, `id-token: write`
2. Node LTS 설치와 `npm ci`
3. 저장소에 커밋된 `content/*.json` 스냅샷을 입력으로 사용한다. `bootstrap_content.py`는 로컬에서 원천 `tax-study`를 갱신할 때만 실행하며, 원천 저장소를 공개 배포 저장소에 복사하거나 Actions에서 추적하지 않는다.
4. `npm run build`로 `out/` 생성
5. Pages artifact 업로드와 배포

외부 도메인은 선택 사항이며 도메인을 별도로 구매할 때만 비용이 생긴다. GitHub Pages의 공개 사이트 용량·트래픽·빌드 제한을 넘는 대용량 미디어나 상업적 서비스는 이번 설계 범위가 아니다.

## 콘텐츠 경계와 오류 처리

- `content/*.json`은 현재 공개 스냅샷을 그대로 사용한다. 원고 문구를 Next.js 마이그레이션과 함께 재작성하지 않는다.
- `lib/content.ts`는 법률 수, issue ID 중복, 법률별 10개, 질문 블록의 필수 문자열·배열을 빌드 시 검사한다. 실패 메시지는 누락된 파일과 필드를 명시한다.
- 쟁점에 공식 조문·판례 링크가 없으면 빈 링크 대신 “공식 출처 확인 필요” 상태를 표시한다.
- 알 수 없는 쟁점 ID는 404로 보내며, 404 화면에서 메인 대장으로 돌아갈 수 있다.
- 브라우저 상태는 검색·필터에만 사용하고 저장하지 않는다. 개인정보나 학습자 식별자를 수집하지 않는다.

## 접근성·모바일 기준

- 한국어 `lang`, 단일 `h1`, 스킵 링크, 의미 있는 heading 순서를 유지한다.
- 링크·검색창·select·summary의 터치 영역은 최소 44px로 유지한다.
- 390px 폭에서 가로 스크롤이 생기지 않도록 표는 작은 화면에서 카드/행 형태로 줄바꿈한다.
- 색만으로 법률·판단 유형을 구분하지 않고 텍스트 라벨을 함께 표시한다.
- 상세 원문은 브라우저 기본 `<details>`로 열고 닫으며, JavaScript 없이도 전체 문서가 접근 가능하다.
- 외부 공식 링크에는 `rel="noopener noreferrer"`와 명확한 링크 라벨을 둔다.

## 검증 기준

마이그레이션 완료로 판단하려면 다음을 모두 만족해야 한다.

- `npm ci`와 `npm run build`가 경고·오류 없이 끝난다.
- `out/index.html`과 50개 `out/issues/{issue_id}/index.html`이 생성된다.
- 메인 페이지에 다섯 법률과 법률별 10개 행이 있고, 각 행 링크가 실제 정적 파일을 가리킨다.
- 대표 상세 페이지와 404 페이지에 하나의 `h1`, 스킵 링크, 사실관계·질문별 판단·공식 출처가 있다.
- 콘텐츠 검증 테스트와 기존 원천 데이터 검증 테스트가 모두 통과한다.
- 빌드 산출물에 `localStorage`, 로그인·완료 상태, `localhost`, `file://`, 허용목록 밖의 외부 링크가 없다.
- JavaScript를 비활성화해도 모든 쟁점 행과 상세 페이지를 읽을 수 있다.
- 로컬 정적 서버에서 `/`, 대표 issue URL, 존재하지 않는 issue URL이 각각 기대한 상태 코드와 본문을 반환한다.
- GitHub Pages 공개 주소에서 루트와 대표 issue URL을 모바일 폭으로 확인하고, 기존 주소가 새 Next.js 산출물을 제공한다.

## 단계적 전환과 되돌리기

1. Next.js 앱과 타입·콘텐츠 로더를 새 파일로 추가하고 기존 `docs/` 산출물은 첫 단계에서 보존한다.
2. 동일한 JSON으로 로컬 `out/`을 만들고 기존 대표 문서의 핵심 라벨·링크·문장 순서를 비교한다.
3. 접근성·콘텐츠·빌드 검증을 통과한 뒤 Pages source를 GitHub Actions로 전환한다.
4. 공개 루트와 대표 상세 경로를 확인한 뒤, 더 이상 Pages가 사용하지 않는 구형 생성 산출물의 정리 여부를 별도 커밋으로 판단한다.
5. 공개 검증이 실패하면 Pages source를 기존 `main:/docs`로 되돌리고, 마지막으로 정상 확인된 커밋을 기준으로 원인을 수정한다. `tax-study`에는 어떤 단계에서도 변경을 적용하지 않는다.

## 승인 상태

사용자는 무료 운영 조건과 **Next.js App Router + TypeScript + GitHub Pages 정적 export** 접근법을 승인했다. 이 문서는 구현 계획을 작성하기 위한 기준이며, 구현 전 사용자의 문서 검토를 거친다.
