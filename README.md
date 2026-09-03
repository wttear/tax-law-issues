# 세법 쟁점 대장

국세기본법·국세징수법·법인세법·소득세법·부가가치세법에서 10개씩 고른 50개 쟁점을 읽는 별도 정적 사이트입니다. 각 쟁점은 `오늘의 질문 → 새 사실 한 조각 → 관련 조문(기본 접힘) → 답·해설`을 단계별로 반복한 뒤 `판례·조사·회계 연결 → 사실이 달라지면 → 마지막 정리`로 마칩니다.

기존 [`tax-study`](../tax-study/) 사이트의 대시보드·진도·로그인 상태를 수정하지 않습니다. 이 디렉터리는 자유열람용 새 사이트이며, 학습 완료 버튼과 브라우저 저장 상태를 사용하지 않습니다.

## 로컬에서 보기

```bash
python3 scripts/bootstrap_content.py --source-root ../tax-study
python3 scripts/build.py
python3 -m http.server 4173 --directory docs
```

브라우저에서 `http://127.0.0.1:4173/`을 열면 대장이 나오고, 모바일에서는 같은 주소를 휴대전화 브라우저로 열 수 있습니다. 서버 없이도 `docs/index.html`을 직접 열어 본문을 확인할 수 있지만, 정적 링크 확인은 위 서버 방식이 정확합니다.

## 원천과 검증

- `content/issue-selection.json`: 법률별 10개 선정 목록
- `scripts/bootstrap_content.py`: 공개 `tax-study` 원천에서 쟁점·조문·판례 스냅샷을 재생성
- `content/issues.json`: 50개 쟁점과 순차 `steps` 배열
- `content/articles.json`: 연결된 현행 조문 원문과 공식 URL
- `content/precedents.json`: 공식 판결문으로 확인 가능한 판례 연결
- `scripts/build.py`: 런타임 서버 없이 `docs/`에 51개 HTML과 CSS/JS를 생성

법령 기준일은 조문별 원천 스냅샷(2026-09-01 전후), 학습 원고는 2026-08-27~28 자료를 사용합니다. 사건 당시 법령과 현행법이 다를 수 있는 판례는 판례 카드의 적용법 메모와 공식 원문을 다시 확인해야 합니다. 확인되지 않은 판례 요지나 시행령 전문은 만들어 넣지 않고 공식 연결만 표시합니다.

현재 공개 시안에서는 독립 기출 데이터로 검증되지 않은 시험형 섹션을 새 문제처럼 만들지 않았습니다. 원고에 있는 회상 질문은 마지막 정리의 선택형 자기점검으로만 표시하고, 실제 기출 원문·정답·해설 데이터가 별도 검증되면 모듈로 추가할 수 있습니다.

## GitHub Pages

게시 산출물은 `docs/`입니다. 별도 저장소를 만들고 인증이 되어 있을 때 다음 흐름으로 게시합니다.

```bash
gh auth login -h github.com
gh repo create wttear/tax-law-issues --public --source . --remote origin --push
```

그 다음 저장소 Settings → Pages에서 `main` 브랜치의 `/docs` 폴더를 선택합니다. 현재 게시 주소는 <https://wttear.github.io/tax-law-issues/>입니다.
