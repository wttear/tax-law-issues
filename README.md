# 세법 쟁점 아틀라스

국세기본법·국세징수법·법인세법·소득세법·부가가치세법의 검수된 실무 쟁점을 읽는 Next.js 정적 사이트입니다. 법률별 개수를 맞추지 않고, 학습에 필요한 판단 단위만 추가합니다. 각 쟁점은 `사실관계 전문 → 질문별 판단 → 관련 법령 원문 → 세무조사·회계 연결 → 판례 → 조건 변경 → 마지막 정리` 순서로 이어집니다.

이 저장소는 기존 학습 앱의 진도·로그인 상태를 수정하지 않습니다. 학습 완료 버튼이나 브라우저 저장 없이 모바일에서 자유롭게 열람하는 별도 사이트입니다.

## 기술 스택

- Next.js App Router + React 정적 내보내기(`output: export`)
- Tailwind CSS v4
- 저장소가 소유한 shadcn 스타일 UI 프리미티브(`components/ui`)
- GitHub Actions → GitHub Pages 배포

## 로컬에서 보기

```bash
npm ci
NEXT_PUBLIC_BASE_PATH='' npm run dev
```

개발 서버는 `http://localhost:3000/`에서 열립니다. GitHub Pages와 같은 정적 산출물을 만들려면 다음을 실행합니다.

```bash
NEXT_PUBLIC_BASE_PATH='' npm run build
python3 -m http.server 4173 --directory out
```

그 다음 모바일 또는 데스크톱에서 `http://127.0.0.1:4173/`을 엽니다. 실제 게시 경로는 `/tax-law-issues/`이므로 그 경로를 로컬에서 재현하려면 `NEXT_PUBLIC_BASE_PATH=/tax-law-issues npm run build`를 사용합니다.

## 검증

```bash
npm run typecheck
npm run build
npm run test:node
```

테스트는 50개 콘텐츠·경로, 메인 검색/필터 HTML fallback, 쟁점 읽기 순서, 법령·판례 공식 링크, 접근성 계약을 확인합니다.

## 콘텐츠와 출처

- `content/issue-selection.json`: 현재 공개 쟁점의 선정 목록
- `content/issues.json`: 50개 쟁점과 사실관계·질문 블록·조사·회계 연결
- `content/articles.json`: 연결된 현행 조문 원문과 공식 URL
- `content/precedents.json`: 공식 판결문으로 연결되는 판례 색인
- `scripts/bootstrap_content.py`: 공개 원천에서 콘텐츠 스냅샷을 갱신하는 보조 스크립트

법령 기준일과 원문 확인일은 각 읽기 화면에 표시합니다. 사건 당시 법령과 현행법이 다를 수 있는 판례는 공식 출처에서 다시 확인해야 하며, 확인되지 않은 판시내용은 채워 넣지 않습니다.

## GitHub Pages

`.github/workflows/deploy-pages.yml`이 `main`에 push될 때 Next 정적 산출물(`out/`)을 만들고 Pages artifact로 배포합니다. 저장소 Settings → Pages에서 source를 **GitHub Actions**로 한 번 지정하면 됩니다.

공개 주소: <https://wttear.github.io/tax-law-issues/>

상속세 및 증여세법·개별소비세법·지방세법·조세특례제한법은 이번 50개 범위에서 제외했습니다.
