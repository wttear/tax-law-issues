#!/usr/bin/env python3
"""Build the standalone, dependency-free tax issue atlas."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
import shutil
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
SOURCE = ROOT / "src"
DOCS = ROOT / "docs"
OFFICIAL_HOSTS = {
    "law.go.kr",
    "www.law.go.kr",
    "scourt.go.kr",
    "www.scourt.go.kr",
    "kasb.or.kr",
    "www.kasb.or.kr",
}
LEVEL_LABELS = {
    "beginner": "입문",
    "intermediate": "중급",
    "advanced": "고급",
    "expert": "심화",
}
STATUS_LABELS = {
    "current": "현행",
    "source_only": "원문",
    "historical": "과거 기준",
}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def official_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.startswith("https://"):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.hostname not in OFFICIAL_HOSTS:
        return None
    return value


def link(url: Any, label: str, class_name: str = "") -> str:
    safe = official_url(url)
    if safe is None:
        return esc(label)
    class_attr = f' class="{esc(class_name)}"' if class_name else ""
    return (
        f'<a href="{esc(safe)}"{class_attr} rel="noopener noreferrer">'
        f"{esc(label)}</a>"
    )


def linebreak_text(value: Any) -> str:
    return esc(value).replace("\n", "<br>")


def level_label(value: Any) -> str:
    return LEVEL_LABELS.get(str(value), str(value or "자유열람"))


def list_items(values: Any, class_name: str = "") -> str:
    if not isinstance(values, list) or not values:
        return ""
    class_attr = f' class="{esc(class_name)}"' if class_name else ""
    return "<ul{}>{}</ul>".format(
        class_attr,
        "".join(f"<li>{esc(value)}</li>" for value in values),
    )


def page_shell(
    *,
    title: str,
    description: str,
    body: str,
    asset_prefix: str,
    include_script: bool = False,
) -> str:
    script = f'<script src="{asset_prefix}site.js" defer></script>' if include_script else ""
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(description)}">
  <title>{esc(title)} · 세법 쟁점 대장</title>
  <link rel="stylesheet" href="{asset_prefix}styles.css">
  {script}
</head>
<body>
{body}
</body>
</html>
'''


def direction_contract() -> str:
    return """<!--
DIRECTION CONTRACT
THESIS: 법령 원문에서 출발해 쟁점·증빙·판례의 판단 경계를 한 화면의 읽기 순서로 만든다.
OWN-WORLD: 기존 사건배당부의 석재·종이·잉크·공식 파랑·규선 언어를 법률별 대장으로 확장한다.
STORY: 법률 선택 → 쟁점 한 행 → 답을 보기 전 질문 → 원문 → 초보자 해설 → 판단 지도 → 증빙 → 판례 → 필요 시 회계.
FIRST VIEWPORT: 첫 화면에서 다섯 법률과 50개 쟁점의 위치를 보고, 검색 없이도 어느 행을 열지 결정한다.
FORM: 직각 대장 행, 얇은 규선, 짧은 라벨, 한 열 모바일 읽기 흐름을 사용한다. concept-seed: 0e3fac08.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md.
-->"""


def render_module_tags(issue: dict[str, Any]) -> str:
    tags = ["법령·판단", "조사·증빙"]
    if issue.get("precedents"):
        tags.append(f"판례 {len(issue['precedents'])}")
    if issue.get("modules", {}).get("accounting"):
        tags.append("회계·조정")
    return "".join(f'<li class="module-tag">{esc(tag)}</li>' for tag in tags)


def render_index(data: dict[str, Any]) -> str:
    issue_by_id = {issue["issue_id"]: issue for issue in data["issues"]}
    law_sections: list[str] = []
    nav_links: list[str] = []
    for law in data["laws"]:
        code = law["law_code"]
        nav_links.append(
            f'<a class="law-tab" href="#law-{esc(code)}">'
            f'<span class="law-tab__code">{esc(code)}</span>'
            f'<span>{esc(law["law_name"])}</span>'
            f'<span class="law-tab__count">{law["issue_count"]}개</span></a>'
        )
        rows: list[str] = []
        for issue_id in law["issue_ids"]:
            issue = issue_by_id[issue_id]
            search_text = " ".join(
                [issue["title"], issue.get("canonical_title", ""), issue["core_question"]]
            )
            rows.append(
                f'''<li class="issue-row" data-law="{esc(code)}" data-search="{esc(search_text)}">
  <span class="issue-row__number" aria-hidden="true">{issue["position"]:02d}</span>
  <div class="issue-row__body">
    <h3><span class="issue-row__context">{esc(code)} · {esc(level_label(issue.get("level")))}</span><a href="issues/{esc(issue_id)}/">{esc(issue["title"])}</a></h3>
    <p class="issue-row__question">{esc(issue["core_question"])}</p>
    <ul class="module-tags" aria-label="학습 모듈">{render_module_tags(issue)}</ul>
  </div>
  <a class="row-open" href="issues/{esc(issue_id)}/" aria-label="{esc(issue['title'])} 읽기">읽기<span aria-hidden="true">↗</span></a>
</li>'''
            )
        law_sections.append(
            f'''<section class="ledger-section" id="law-{esc(code)}" data-law-section="{esc(code)}">
  <header class="ledger-section__header">
    <div><h2><span class="heading-sequence">{esc(code)}</span>{esc(law["law_name"])}</h2></div>
    <p class="section-count">{law["issue_count"]}개 쟁점</p>
  </header>
  <ol class="issue-ledger">{"".join(rows)}</ol>
</section>'''
        )

    body = f'''{direction_contract()}
<a class="skip-link" href="#main-content">본문으로 건너뛰기</a>
<header class="site-header">
  <div class="site-header__inner">
    <a class="wordmark" href="./"><span class="wordmark__mark">TAX</span><span>쟁점 대장</span></a>
    <span class="header-note">자유열람 · 기준일 {esc(data.get("generated_as_of"))}</span>
  </div>
</header>
<main id="main-content" class="page page--index">
  <section class="atlas-intro" aria-labelledby="atlas-title">
    <h1 id="atlas-title">다섯 법률, 오십 개 판단 단위</h1>
    <p class="intro-copy">조문을 먼저 열고, 결론을 바꾸는 사실과 증빙을 확인한 다음, 직접 연결된 판례로 판단의 경계를 넓혀 보세요.</p>
    <div class="intro-rule" aria-hidden="true"><span></span><span></span><span></span></div>
    <p class="intro-caption">국세기본법 · 국세징수법 · 법인세법 · 소득세법 · 부가가치세법</p>
  </section>

  <nav class="law-directory" aria-label="법률별 바로가기">{"".join(nav_links)}</nav>

  <section class="register-tools" aria-labelledby="tools-title">
    <div class="tools-heading"><h2 id="tools-title">지금 읽을 행을 고르세요</h2></div>
    <div class="tool-controls">
      <label class="field-label" for="issue-search">쟁점 검색
        <input id="issue-search" type="search" placeholder="예: 세무조사, 손금, 세금계산서" autocomplete="off">
      </label>
      <label class="field-label" for="law-filter">법률 필터
        <select id="law-filter">
          <option value="all">다섯 법률 모두</option>
          {"".join(f'<option value="{esc(law["law_code"])}">{esc(law["law_name"])}</option>' for law in data["laws"])}
        </select>
      </label>
    </div>
    <p id="filter-status" class="filter-status" role="status" aria-live="polite">50개 쟁점 표시</p>
    <noscript><p class="no-script-note">검색을 켜지 않아도 아래 모든 쟁점 행과 링크를 읽을 수 있습니다.</p></noscript>
  </section>

  <div id="issue-register" class="issue-register">{"".join(law_sections)}</div>

  <section class="reading-order" aria-labelledby="reading-order-title">
    <h2 id="reading-order-title"><span class="heading-sequence">읽는 순서</span>질문을 먼저 세우고, 원문으로 돌아오기</h2>
    <ol>
      <li><span>01</span> 답을 보기 전 결론을 바꿀 사실을 적습니다.</li>
      <li><span>02</span> 현행 조문과 기준일을 확인합니다.</li>
      <li><span>03</span> 초보자 해설·판단 지도·증빙을 연결합니다.</li>
      <li><span>04</span> 관련 판례와 필요한 회계·세무조정을 대조합니다.</li>
    </ol>
  </section>
</main>
<footer class="site-footer"><div><strong>세법 쟁점 대장</strong><span>기존 학습 사이트의 진도·로그인·완료 상태와 분리된 공개 읽기 공간입니다.</span></div></footer>'''
    return page_shell(
        title="세법 쟁점 대장",
        description="다섯 핵심 세법 50개 쟁점을 법령 원문과 판단·증빙·판례로 읽는 모바일 우선 아틀라스",
        body=body,
        asset_prefix="",
        include_script=True,
    )


def render_article(article: dict[str, Any]) -> str:
    versions = article.get("versions", [])
    version = versions[0] if versions else {}
    text = version.get("text") or "현재 스냅샷에 원문이 없습니다. 공식 출처에서 확인하세요."
    effective = version.get("effective_date") or "기준일 자료"
    status = version.get("status") or article.get("content_status") or "확인 필요"
    status = STATUS_LABELS.get(str(status), str(status))
    return f'''<details class="article-record" open>
  <summary><span>{esc(article.get("article_number"))}</span><strong>{esc(article.get("title"))}</strong><em>{esc(status)} · 시행 {esc(effective)}</em></summary>
  <div class="article-record__body">
    <p class="source-label">국가법령정보센터 원문</p>
    <div class="law-source-text">{linebreak_text(text)}</div>
    <p class="source-link">{link(article.get("official_url"), "공식 조문 열기")}</p>
  </div>
</details>'''


def render_law_map(rows: Any) -> str:
    if not isinstance(rows, list) or not rows:
        return '<p class="quiet">이 쟁점의 판단 지도는 아래 법령 원문과 학습 원고에서 확인합니다.</p>'
    table_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        table_rows.append(
            f'<tr><td data-label="조문">{esc(row.get("article_reference"))}</td>'
            f'<td data-label="규칙">{esc(row.get("rule_summary"))}</td></tr>'
        )
    return f'''<div class="table-wrap"><table class="decision-table"><thead><tr><th>조문 연결</th><th>이 단계에서 볼 것</th></tr></thead><tbody>{"".join(table_rows)}</tbody></table></div>'''


def render_related_references(rows: Any) -> str:
    if not isinstance(rows, list) or not rows:
        return ""
    items: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        items.append(
            f'<li><span>{esc(row.get("reference"))}</span> '
            f'{link(row.get("official_url"), "공식 법령 연결")}</li>'
        )
    if not items:
        return ""
    return f'''<div class="related-reference"><p class="source-label">시행령·시행규칙 및 연결 조문</p><p class="quiet">이 스냅샷에 전문이 포함된 조문은 위 원문으로, 나머지 연결은 공식 법령 페이지에서 사건 시점의 버전을 확인합니다.</p><ul class="source-list">{"".join(items)}</ul></div>'''


def render_audit_summary(items: Any) -> str:
    if not isinstance(items, list) or not items:
        return ""
    blocks: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        blocks.append(
            f'''<div class="audit-summary">
  <div><p class="mini-label">조사 가설</p><p>{esc(item.get("audit_hypothesis"))}</p></div>
  <div><p class="mini-label">반대 가설</p><p>{esc(item.get("counter_hypothesis"))}</p></div>
  <div><p class="mini-label">먼저 확인할 자료</p>{list_items(item.get("evidence_to_check"), "evidence-list")}</div>
</div>'''
        )
    return "".join(blocks)


def render_precedents(items: Any) -> str:
    if not isinstance(items, list) or not items:
        return '<p class="quiet">이 시안의 공식 판례 색인에서 직접 연결된 사건은 확인되지 않았습니다. 판례를 만들거나 추정하지 않고, 원문 조문과 사실관계를 기준으로 읽습니다.</p>'
    cards: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        facts = list_items(item.get("distinguishing_facts"), "case-facts")
        summary = item.get("holding_summary") or item.get("issue_summary") or "공식 판결문에서 판시내용을 확인하세요."
        title = item.get("title") or item.get("issue_summary") or "관련 판례"
        cards.append(
            f'''<li class="precedent-row">
  <div class="precedent-row__head"><span class="case-number">{esc(item.get("case_number") or item.get("precedent_id"))}</span><span>{esc(item.get("court") or "법원")} · {esc(item.get("decision_date") or "선고일 확인")}</span></div>
  <h3>{esc(title)}</h3>
  <p>{esc(summary)}</p>
  {facts}
  <p class="source-link">{link(item.get("official_source_url"), "공식 판결문 열기")}</p>
</li>'''
        )
    return f'<ol class="precedent-ledger">{"".join(cards)}</ol>'


def render_accounting(issue: dict[str, Any]) -> str:
    if not issue.get("modules", {}).get("accounting"):
        return ""
    items = issue.get("accounting_tax_adjustment", [])
    rows: list[str] = []
    for item in items:
        if not isinstance(item, dict) or item.get("status") in {None, "not_applicable"}:
            continue
        for label, key in (
            ("회계 처리", "accounting_treatment"),
            ("대사 포인트", "reconciliation"),
            ("세무조정 방향", "tax_adjustment"),
        ):
            if item.get(key):
                rows.append(f'<tr><th scope="row">{esc(label)}</th><td>{esc(item[key])}</td></tr>')
    if not rows:
        return ""
    return f'''<section class="reader-block reader-block--accounting" id="accounting" aria-labelledby="accounting-title">
  <h2 id="accounting-title"><span class="heading-sequence">선택 모듈</span>회계·세무조정 연결</h2>
  <p class="block-lead">장부 숫자가 세법상 과세표준과 신고서로 넘어가는 지점만 남겼습니다.</p>
  <div class="table-wrap"><table class="accounting-table"><tbody>{"".join(rows)}</tbody></table></div>
</section>'''


def render_sources(issue: dict[str, Any], article_by_id: dict[str, dict[str, Any]]) -> str:
    article_links = []
    seen: set[str] = set()
    for article_id in issue.get("article_ids", []):
        article = article_by_id.get(article_id)
        if not article or article_id in seen:
            continue
        seen.add(article_id)
        article_links.append(f'<li>{esc(article.get("article_number"))} {link(article.get("official_url"), "공식 원문")}</li>')
    lesson_path = issue.get("source", {}).get("lesson_path")
    return f'''<section class="reader-block reader-block--sources" id="sources" aria-labelledby="sources-title">
  <h2 id="sources-title"><span class="heading-sequence">검증 메모</span>출처와 기준일</h2>
  <p>법령 원문은 각 조문의 공식 링크에서, 학습 설명은 공개된 원자료 원고에서 가져왔습니다. 사건 당시 법령이 현행법과 다르면 판례 카드의 적용법 메모를 우선 확인하세요.</p>
  <dl class="provenance-list"><div><dt>법령 자료 기준일</dt><dd>{esc(issue.get("source", {}).get("curriculum_source_as_of") or "원자료 기록에 따름")}</dd></div><div><dt>학습 원고</dt><dd><code>{esc(lesson_path)}</code></dd></div><div><dt>판례 자료 수</dt><dd>{len(issue.get("precedents", []))}건 직접 연결</dd></div></dl>
  <ul class="source-list">{"".join(article_links)}</ul>
</section>'''


def render_issue(
    issue: dict[str, Any],
    law: dict[str, Any],
    all_issues_for_law: list[dict[str, Any]],
    article_by_id: dict[str, dict[str, Any]],
) -> str:
    position = issue["position"]
    previous = all_issues_for_law[position - 2] if position > 1 else None
    following = all_issues_for_law[position] if position < len(all_issues_for_law) else None
    nav_links = [
        '<a href="#law-source">법령 원문</a>',
        '<a href="#beginner">초보자 해설</a>',
        '<a href="#map">판단 지도</a>',
        '<a href="#example">합성 사례</a>',
        '<a href="#audit">증빙 실습</a>',
        '<a href="#precedents">관련 판례</a>',
    ]
    if issue.get("modules", {}).get("accounting"):
        nav_links.append('<a href="#accounting">회계·조정</a>')
    nav_links.append('<a href="#sources">출처</a>')

    sections = issue.get("sections", {})
    concept = sections.get("concept", "")
    legal_section = sections.get("legal-structure", "")
    example_section = sections.get("worked-example", "")
    audit_section = sections.get("audit-evidence", "")
    precedent_section = sections.get("precedent", "")
    recall_section = sections.get("recall", "")

    body = f'''{direction_contract()}
<a class="skip-link" href="#main-content">본문으로 건너뛰기</a>
<header class="site-header"><div class="site-header__inner"><a class="wordmark" href="../../"><span class="wordmark__mark">TAX</span><span>쟁점 대장</span></a><a class="header-back" href="../../">전체 대장으로</a></div></header>
<main id="main-content" class="page page--reader">
  <nav class="breadcrumb" aria-label="현재 위치"><a href="../../">쟁점 대장</a><span aria-hidden="true">/</span><a href="../../#law-{esc(law["law_code"])}">{esc(law["law_name"])}</a><span aria-hidden="true">/</span><span>{position:02d}</span></nav>
  <header class="reader-heading">
    <h1>{esc(issue["title"])}</h1>
    <p class="reader-context">{esc(law["law_code"])} · 쟁점 {position:02d} / 10 · {esc(level_label(issue.get("level")))}</p>
    <p class="reader-lead">법령 원문과 사실·증빙·판례의 연결로 읽는 자유열람 쟁점입니다.</p>
    <ul class="reader-meta"><li>{esc(issue.get("estimated_minutes") or "") }분 읽기</li><li>법령 {len(issue.get("article_ids", []))}개 연결</li><li>판례 {len(issue.get("precedents", []))}건 직접 연결</li></ul>
  </header>

  <section class="prompt-band" aria-labelledby="prompt-title">
    <h2 id="prompt-title"><span class="heading-sequence">답을 보기 전</span>먼저 이 질문에 답해 보세요</h2>
    <p class="prompt-question">{esc(issue["core_question"])}</p>
    <p class="prompt-caption">결론을 바꿀 날짜·당사자·거래흐름·증빙을 한 줄로 적은 뒤 아래 원문을 여세요.</p>
  </section>

  <nav class="reader-index" aria-label="이 쟁점 안에서 이동">{"".join(nav_links)}</nav>

  <section class="reader-block reader-block--law" id="law-source" aria-labelledby="law-source-title">
    <h2 id="law-source-title"><span class="heading-sequence">01 / 기준점</span>법령 원문과 기준일</h2>
    <p class="block-lead">현재 스냅샷의 시행 중 버전을 먼저 보여 줍니다. 과거 거래는 판례 카드와 사건 당시 법령을 분리해 대조합니다.</p>
    <div class="article-stack">{"".join(render_article(article_by_id[a]) for a in issue.get("article_ids", []) if a in article_by_id)}</div>
    {render_related_references(issue.get("related_references"))}
  </section>

  <section class="reader-block reader-block--beginner" id="beginner" aria-labelledby="beginner-title">
    <h2 id="beginner-title"><span class="heading-sequence">02 / 쉽게 말하면</span>초보자 해설</h2>
    <div class="beginner-callout"><p>{esc(issue.get("easy_explanation"))}</p></div>
    {concept}
  </section>

  <section class="reader-block reader-block--map" id="map" aria-labelledby="map-title">
    <h2 id="map-title"><span class="heading-sequence">03 / 판단 구조</span>법령과 쟁점의 판단 지도</h2>
    {render_law_map(issue.get("law_map"))}
    {legal_section}
  </section>

  <section class="reader-block reader-block--example" id="example" aria-labelledby="example-title">
    <h2 id="example-title"><span class="heading-sequence">04 / 사실에 대입하기</span>합성 사례와 결론의 이동</h2>
    <p class="synthetic-note">아래 사례는 학습을 위한 합성 사실입니다. 실제 사건이나 공식 판례의 사실로 읽지 마세요.</p>
    {example_section}
  </section>

  <section class="reader-block reader-block--audit" id="audit" aria-labelledby="audit-title">
    <h2 id="audit-title"><span class="heading-sequence">05 / 조사·증빙</span>세무조사 증빙 실습</h2>
    {render_audit_summary(issue.get("audit_application"))}
    {audit_section}
  </section>

  <section class="reader-block reader-block--precedent" id="precedents" aria-labelledby="precedents-title">
    <h2 id="precedents-title"><span class="heading-sequence">06 / 경계선</span>관련 중요 판례</h2>
    {render_precedents(issue.get("precedents"))}
    {precedent_section}
  </section>

  {render_accounting(issue)}

  <section class="reader-block reader-block--recall" id="recall" aria-labelledby="recall-title">
    <h2 id="recall-title"><span class="heading-sequence">07 / 다시 말하기</span>오늘의 회상</h2>
    <p class="block-lead">시험 답안처럼 외우기보다, 이 쟁점의 요건·결론을 바꾸는 사실·확인자료를 자신의 말로 다시 설명합니다.</p>
    {recall_section}
  </section>

  {render_sources(issue, article_by_id)}

  <nav class="issue-pager" aria-label="같은 법률의 다음 쟁점">
    <div>{f'<span class="pager-label">이전 쟁점</span><a href="../{esc(previous["issue_id"])}/">{esc(previous["title"])}</a>' if previous else '<span class="pager-label">이 법률의 첫 쟁점입니다</span><a href="../../#law-' + esc(law["law_code"]) + '">목록으로</a>'}</div>
    <div class="pager-next">{f'<span class="pager-label">다음 쟁점</span><a href="../{esc(following["issue_id"])}/">{esc(following["title"])}</a>' if following else '<span class="pager-label">이 법률을 다 읽었습니다</span><a href="../../#law-' + esc(law["law_code"]) + '">목록으로</a>'}</div>
  </nav>
</main>
<footer class="site-footer"><div><strong>세법 쟁점 대장</strong><span>이 페이지에는 로그인·진도 잠금·학습 완료 버튼이 없습니다. 필요한 곳부터 자유롭게 읽으세요.</span></div></footer>'''
    return page_shell(
        title=issue["title"],
        description=issue["core_question"],
        body=body,
        asset_prefix="../../",
        include_script=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DOCS)
    args = parser.parse_args()
    output = args.output.resolve()
    data = json.loads((CONTENT / "issues.json").read_text(encoding="utf-8"))
    article_data = json.loads((CONTENT / "articles.json").read_text(encoding="utf-8"))
    article_by_id = {item["article_id"]: item for item in article_data["articles"]}
    issue_by_id = {item["issue_id"]: item for item in data["issues"]}
    output.mkdir(parents=True, exist_ok=True)
    # Keep generated output deterministic and avoid stale issue directories.
    for child in output.iterdir():
        if child.is_dir() and child.name == "issues":
            shutil.rmtree(child)
        elif child.is_file() and child.name in {"index.html", "styles.css", "site.js", ".nojekyll"}:
            child.unlink()
    (output / "issues").mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(render_index(data), encoding="utf-8")
    shutil.copyfile(SOURCE / "site.css", output / "styles.css")
    shutil.copyfile(SOURCE / "site.js", output / "site.js")
    (output / ".nojekyll").write_text("", encoding="utf-8")

    for law in data["laws"]:
        law_issues = [issue_by_id[item] for item in law["issue_ids"]]
        for issue in law_issues:
            destination = output / "issues" / issue["issue_id"]
            destination.mkdir(parents=True, exist_ok=True)
            destination.joinpath("index.html").write_text(
                render_issue(issue, law, law_issues, article_by_id), encoding="utf-8"
            )
    print(f"built {len(data['issues'])} issue pages at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
