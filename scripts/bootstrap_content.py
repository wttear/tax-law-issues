#!/usr/bin/env python3
"""Extract the first 50 issue records from the public tax-study sources.

The new site keeps a small, reviewable JSON snapshot instead of depending on
the existing site's runtime data.  This script is the one place where the
source repository is read; the static builder only reads ``content/``.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlsplit


LAW_NAMES = {
    "NTBA": "국세기본법",
    "NCTA": "국세징수법",
    "CTA": "법인세법",
    "ITA": "소득세법",
    "VAT": "부가가치세법",
}
LAW_FILE_CODES = tuple(LAW_NAMES)
OFFICIAL_HOSTS = {
    "law.go.kr",
    "www.law.go.kr",
    "scourt.go.kr",
    "www.scourt.go.kr",
    "kasb.or.kr",
    "www.kasb.or.kr",
}
ARTICLE_ID_PATTERN = re.compile(r"^(?P<law>[A-Z]+)-(?P<number>[0-9]+(?:-[0-9]+)*)$")
ARTICLE_REF_PATTERN = re.compile(r"(?P<law>국세기본법|국세징수법|법인세법|소득세법|부가가치세법)\s*제")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def is_official_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("https://"):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return parsed.hostname in OFFICIAL_HOSTS


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def issue_memberships(article: dict[str, Any]) -> set[str]:
    """Return issue/topic IDs attached to a learning article row."""
    values: set[str] = set()
    for key in (
        "issue_ids",
        "direct_topic_ids",
        "related_topic_ids",
        "catalog_issue_ids",
        "catalog_topic_ids",
        "direct_topic_ids",
    ):
        raw = article.get(key, [])
        if isinstance(raw, list):
            values.update(str(item) for item in raw if isinstance(item, str))
    for issue in article.get("issues", []):
        if isinstance(issue, dict) and isinstance(issue.get("issue_id"), str):
            values.add(issue["issue_id"])
    return values


def values_for_issue(article: dict[str, Any], key: str, issue_id: str) -> list[Any]:
    """Extract issue-scoped values from the shared learning article index."""
    raw = article.get(key, [])
    if not isinstance(raw, list):
        return []
    result: list[Any] = []
    for item in raw:
        if isinstance(item, dict) and item.get("issue_id") == issue_id:
            result.append(item.get("value", item))
    return result


def extract_prompt(document: Any) -> str:
    """Use the lesson's own pre-reading prompt when no structured question exists."""
    if not document.sections:
        return "이 쟁점에서 결론을 바꾸는 사실과 문서는 무엇인가?"
    lines = list(document.sections[0].lines)
    for index, line in enumerate(lines):
        if line.strip().startswith("### 시작 전 판단"):
            collected: list[str] = []
            for candidate in lines[index + 1 :]:
                if candidate.strip().startswith("### ") or candidate.strip().startswith("## "):
                    break
                if candidate.strip():
                    collected.append(candidate.strip())
            if collected:
                return " ".join(collected)
    return "이 쟁점에서 결론을 바꾸는 사실과 문서는 무엇인가?"


def extract_easy_explanation(document: Any) -> str:
    if not document.sections:
        return document.lead
    lines = list(document.sections[0].lines)
    for index, line in enumerate(lines):
        if line.strip().startswith("### 30초 쉬운 설명"):
            collected: list[str] = []
            for candidate in lines[index + 1 :]:
                if candidate.strip().startswith("### ") or candidate.strip().startswith("## "):
                    break
                if candidate.strip():
                    collected.append(candidate.strip())
            if collected:
                return " ".join(collected)
    return document.lead


_STEP_SENTENCE_PATTERN = re.compile(
    r"(?<=[다요죠음임됨함]\.)\s+|(?<=[!?])\s+"
)


def clean_learning_text(value: Any) -> str:
    """Remove Markdown presentation from learner-facing step text."""
    if not isinstance(value, str):
        return ""
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    return " ".join(value.split()).strip()


def split_learning_sentences(value: Any) -> list[str]:
    """Split Korean prose at sentence endings without splitting dotted dates."""
    text = clean_learning_text(value)
    if not text:
        return []
    parts = [clean_learning_text(item) for item in _STEP_SENTENCE_PATTERN.split(text)]
    return [item for item in parts if item]


def extract_heading_text(document: Any, heading: str) -> str:
    """Return prose directly under the first matching Markdown H3."""
    lines = [line for section in document.sections for line in section.lines]
    target = f"### {heading}"
    collected: list[str] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if not started:
            if stripped == target:
                started = True
            continue
        if stripped.startswith("### ") or stripped.startswith("## "):
            break
        if not stripped or "|" in stripped:
            continue
        if stripped.startswith("-"):
            stripped = stripped[1:].strip()
        if stripped:
            collected.append(stripped)
    return " ".join(collected)


def extract_heading_paragraphs(document: Any, heading: str) -> list[str]:
    """Return prose paragraphs under a heading without splitting sentences."""
    lines = [line for section in document.sections for line in section.lines]
    target = f"### {heading}"
    paragraphs: list[str] = []
    current: list[str] = []
    started = False

    def flush() -> None:
        if current:
            paragraphs.append(clean_learning_text(" ".join(current)))
            current.clear()

    for line in lines:
        stripped = line.strip()
        if not started:
            if stripped == target:
                started = True
            continue
        if stripped.startswith("### ") or stripped.startswith("## "):
            break
        if not stripped or "|" in stripped:
            flush()
            continue
        if stripped.startswith("-"):
            stripped = stripped[1:].strip()
        if stripped:
            current.append(stripped)
    flush()
    return [paragraph for paragraph in paragraphs if paragraph]


def clean_learner_copy(value: Any) -> str:
    """Remove authoring instructions and workflow labels from learner copy."""
    text = clean_learning_text(value)
    if not text:
        return ""

    text = re.sub(r"(?:완전 안내|부분 안내형|독립 해결형)\s*:\s*", "", text)
    text = re.sub(r"\s*책임선\s*:\s*[^.?!]*(?:[.?!]|$)", " ", text)
    text = re.sub(r"\s*단위는 학습용이다\.?", " ", text)
    text = re.sub(r"[^.?!]*학습용\s*(?:회계)?분개[^.?!]*(?:[.?!]|$)", " ", text)
    text = re.sub(r"[^.?!]*별도 회계기준 분개[^.?!]*(?:[.?!]|$)", " ", text)
    text = re.sub(r"[^.?!]*시가 차이를 별도 회계분개로 억지로 만들지 않는다\.?", " ", text)
    text = re.sub(r"\s*\d[\d,]*은[^.?!]*학습값이다\.?", " ", text)
    text = re.sub(r"\s*①[^.?!]*역할을 먼저 작성한다\.?", " ", text)
    text = re.sub(r"\s*수출 0% 증빙과 수입세액 공제 증빙을 먼저 선택한다\.?", " ", text)
    text = re.sub(r"\s*(?:불공제\s+[\d,]+원은 산식으로 확인하고|세 차감액은 제공하지만)\s*", " ", text)
    text = text.replace(" 해설은 ", ". ")
    text = re.sub(r"법정 잔존가치\s+([\d,]+원)은\s+제시한다", r"법정 잔존가치 \1을 적용한다", text)
    text = re.sub(r"\s*기한은 제시한다\.?", " ", text)
    text = re.sub(
        r"\s*다만 하급심이라는 심급과 항소 표기를 (?:학습)?자료에서 항상 함께 보여 줘야 한다\.?",
        " ",
        text,
    )
    text = text.replace(
        "교육문제는 법인세법 시행령 제69조에 따라",
        "세무상 계산은 법인세법 시행령 제69조에 따라",
    )
    text = text.replace(
        "이 예제는 수정하지 않은 오류 장부로 신고하는 경우만 보여 준다.",
        "수정분개가 반영되지 않은 장부는 익금산입 유보로 조정한다.",
    )
    text = text.replace("이 예제에서는", "이 사례에서는")
    text = text.replace("예제 불공제", "사례의 불공제")
    text = text.replace("학습 전제에서", "조건에서")
    text = text.replace("학습금액", "금액")
    text = text.replace("학습자료", "자료")
    text = text.replace("학습 원천징수율", "적용 원천징수율")
    text = text.replace("학습상", "계산상")
    text = text.replace("현행 학습 기준", "현행 기준")
    text = text.replace("교육금액", "금액")
    text = text.replace("문제에 제시된", "제시된")
    text = text.replace(" 학습 레슨", " 레슨")
    text = text.replace("을 학습하게 한다", "을 기준으로 판단한다")
    text = text.replace("를 학습하게 한다", "를 기준으로 판단한다")
    text = text.replace("을 학습하므로", "을 다루므로")
    text = text.replace("를 학습하므로", "를 다루므로")
    text = text.replace("갑은 국내법상 비거주자로 전제한다.", "갑은 국내법상 비거주자다.")
    text = text.replace(
        "문제는 학습을 위해 조약 적용 전 국내법상 원천징수율을 20퍼센트로 제시한다.",
        "조약 적용 전 국내법상 원천징수율은 20퍼센트로 둔다.",
    )
    text = text.replace("문제 제시 원천징수율", "적용 원천징수율")

    # Workflow-only chains are useful to an author but not to a learner.
    if "VAT 실무 bridge:" in text:
        before, after = text.split("VAT 실무 bridge:", 1)
        continuation = re.search(
            r"(사업자는|실제 공급자가|폐업자는|양도자가|수출자는|매입자는|공급자가|공통매입)" ,
            after,
        )
        text = before + (after[continuation.start() :] if continuation else "")
    text = re.sub(
        r"(?:입력|원시증빙)\s+[^.?!]*?(?:→[^.?!]*?){1,}[^.?!]*?"
        r"(?:순서(?:로)?\s*(?:잇는다|대사한다|연결한다)|순서다)\.?",
        "관련 자료를 순서대로 대조한다.",
        text,
    )
    text = re.sub(
        r"\s*학습자(?:는|가|를|도|에게)?\s+[^.?!]*(?:먼저|대조|작성|완성|답)[^.?!]*[.?!]?",
        " ",
        text,
    )
    text = re.sub(r"\s*분개를 억지로 만들지 않고\s*", " ", text)
    text = re.sub(r"\s*억지로\s+", " ", text)
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip(" ·")
    return text


def clean_question_text(value: Any) -> str:
    """Make source prompts read as direct questions rather than author notes."""
    text = clean_learner_copy(value)
    if not text:
        return ""
    text = re.sub(r"^(?:법리 구분|증빙 선택|새 사실 전이)\s*:\s*", "", text)
    text = re.sub(r"\b[A-Z]+-AUDIT-\d+의?\s*", "", text)
    text = text.replace("독립 원본 세 가지", "주요 원본 자료")
    text = text.replace("푸는 조문 순서는 무엇인가요?", "어떤 순서로 판단할까요?")
    text = text.replace("푸는 조문 순서는 무엇일까요?", "어떤 순서로 판단할까요?")
    text = text.replace("무엇인가요?", "무엇일까요?")
    text = text.replace("설명해 보세요", "어떻게 설명할까요?")
    text = text.replace("설명해 보라", "어떻게 설명할까요?")
    text = text.replace("말해 보세요", "어떻게 설명할까요?")
    text = re.sub(r"구분해 보세요\??", "어떻게 구분할까요?", text)
    text = re.sub(r"판단해 보세요\??", "어떻게 판단할까요?", text)
    text = re.sub(r"계산해 보세요\??", "어떻게 계산할까요?", text)
    text = text.replace("어떤 순서로 가르치나요?", "어떤 순서로 구별할까요?")
    text = text.replace("어떤 순서로 가르나요?", "어떤 순서로 구별할까요?")
    text = text.replace("자료를 고르세요", "자료를 고를까요")
    text = text.replace("고르겠나요?", "고를까요?")
    text = text.replace("무엇부터 보나요?", "무엇부터 확인할까요?")
    text = text.replace("무엇을 먼저 보나요?", "무엇부터 확인할까요?")
    text = text.replace("추가된 변형사례", "조건이 바뀐 사례")
    text = text.replace("변형사례", "조건이 바뀐 사례")
    text = text.replace("위 변형사실을 적용하면", "조건이 바뀌면")
    text = text.replace("새 사실이 추가되면", "조건이 추가되면")
    text = text.replace("새 사실이 나오면", "조건이 확인되면")
    text = re.sub(r"\?{2,}$", "?", text)
    text = re.sub(r"[.。．]+$", "", text).strip()
    text = re.sub(r"\s+", " ", text).strip()
    if text and not text.endswith(("?", "？")):
        text += "?"
    return text


def clean_records(value: Any) -> Any:
    """Recursively clean learner-facing source records while preserving shape."""
    if isinstance(value, str):
        return clean_learner_copy(value)
    if isinstance(value, list):
        return [clean_records(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_records(item) for key, item in value.items()}
    return value


def clean_precedent_records(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Clean explanatory precedent copy without touching IDs or URLs."""
    copy_keys = {
        "title",
        "issue_summary",
        "holding_summary",
        "significance",
        "distinguishing_facts",
        "disposition_summary",
    }
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cleaned = dict(item)
        for key in copy_keys:
            if key in cleaned:
                cleaned[key] = clean_records(cleaned[key])
        result.append(cleaned)
    return result


def extract_case_facts(document: Any) -> str:
    """Keep the complete case narrative as one learner-facing context block."""
    paragraphs = [clean_learner_copy(value) for value in extract_heading_paragraphs(document, "사실")]
    paragraphs = [value for value in paragraphs if value]
    facts = "\n\n".join(paragraphs)
    facts = re.sub(r"\b비식별\s+", "", facts)
    facts = re.sub(r"^(?:비식별\s+)?(?:가상|합성)\s*사례(?:다|이다)\.?\s*", "", facts)
    if facts:
        return facts.strip()
    fallback = clean_learner_copy(extract_easy_explanation(document))
    return fallback or "원자료에 제시된 사실관계를 기준으로 판단한다."


def extract_numbered_items(document: Any, heading: str) -> list[str]:
    """Keep short numbered recall prompts without importing the old layout."""
    lines = [line for section in document.sections for line in section.lines]
    target = f"### {heading}"
    result: list[str] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if not started:
            if stripped == target:
                started = True
            continue
        if stripped.startswith("### ") or stripped.startswith("## "):
            break
        match = re.match(r"^[0-9]+\.\s+(.+)$", stripped)
        if match:
            result.append(clean_learning_text(match.group(1)))
    return result


def article_display_label(
    article_id: str,
    law_name: str,
    selected_articles: list[dict[str, Any]],
) -> str:
    """Build a stable human label while retaining article IDs for rendering."""
    for article in selected_articles:
        if article.get("article_id") != article_id:
            continue
        source_law = article.get("source_law", {})
        number = source_law.get("article_number")
        if number:
            return f"{law_name} {number}"
    suffix_parts = article_id.split("-", 1)[-1].split("-")
    if len(suffix_parts) > 1:
        number = f"제{suffix_parts[0]}조의{suffix_parts[1]}"
    else:
        number = f"제{suffix_parts[0]}조"
    return f"{law_name} {number}"


def build_question_blocks(
    *,
    issue_id: str,
    core_question: str,
    law_name: str,
    article_ids: list[str],
    selected_articles: list[dict[str, Any]],
    law_map: list[dict[str, Any]],
    beginner: list[dict[str, Any]],
    audit: list[dict[str, Any]],
    accounting: list[dict[str, Any]],
    resolved_precedents: list[dict[str, Any]],
    document: Any,
    topic: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], str, str, list[str]]:
    """Build a case-first narrative with self-contained question blocks.

    The source lesson may contain many short sentences, but those sentences
    are not independent facts.  Keep the complete ``사실`` section together
    and let each question point back to the relevant semantic part of it.
    """
    case_facts = extract_case_facts(document)

    rules = [
        clean_learner_copy(item.get("rule_summary"))
        for item in law_map
        if isinstance(item, dict) and clean_learner_copy(item.get("rule_summary"))
    ]
    if not rules:
        rules = [f"{law_name}의 해당 조문에서 요건과 효과를 순서대로 확인한다."]

    reasoning = split_learning_sentences(
        clean_learner_copy(extract_heading_text(document, "전문가 판단 과정"))
    )
    reasoning = [
        item
        for item in reasoning
        if item not in {"관련 자료를 순서대로 대조한다."}
    ]
    easy = split_learning_sentences(
        clean_learner_copy(
            beginner[0].get("text") if beginner and isinstance(beginner[0], dict) else ""
        )
    )
    if not easy:
        easy = split_learning_sentences(clean_learner_copy(extract_easy_explanation(document)))

    article_labels = {
        article_id: article_display_label(article_id, law_name, selected_articles)
        for article_id in article_ids
    }
    evidence: list[str] = []
    for item in audit:
        if isinstance(item, dict) and isinstance(item.get("evidence_to_check"), list):
            evidence.extend(
                clean_learner_copy(value)
                for value in item["evidence_to_check"]
                if clean_learner_copy(value)
            )
    evidence = list(dict.fromkeys(evidence))
    precedent_refs = [
        str(item.get("precedent_id") or item.get("case_number"))
        for item in resolved_precedents
        if item.get("precedent_id") or item.get("case_number")
    ]
    accounting_item = next(
        (
            item
            for item in accounting
            if isinstance(item, dict) and item.get("status") not in {None, "not_applicable"}
        ),
        None,
    )

    recall_questions = [
        clean_question_text(item)
        for item in extract_numbered_items(document, "오늘의 회상 3문항")
        if clean_question_text(item)
    ]
    candidates = [clean_question_text(core_question)]
    candidates.extend(recall_questions)
    candidates.extend(
        clean_question_text(
            f"{item.get('article_reference') or article_labels.get(article_ids[index], law_name)}의 요건과 예외를 이 사실관계에 어떻게 적용할까요?"
        )
        for index, item in enumerate(law_map)
        if isinstance(item, dict)
    )
    candidates = list(dict.fromkeys(item for item in candidates if item))
    if len(candidates) < 2:
        candidates.append("이 사실관계에서 최종 세무상 결론은 무엇일까요?")
    block_count = min(max(2, len(reasoning) or 2), len(candidates), 4)
    questions = candidates[:block_count]

    # The last answer can carry the remaining reasoning so the reader gets a
    # complete conclusion without being forced through artificial transitions.
    answers: list[str] = []
    for index in range(block_count):
        if reasoning and index == block_count - 1 and index < len(reasoning):
            answer = " ".join(reasoning[index:])
        elif index < len(reasoning):
            answer = reasoning[index]
        elif accounting_item and accounting_item.get("tax_adjustment") and index == block_count - 1:
            answer = accounting_item["tax_adjustment"]
        elif index < len(rules):
            answer = rules[index]
        else:
            answer = rules[index % len(rules)]
        answers.append(clean_learner_copy(answer))

    blocks: list[dict[str, Any]] = []
    for index, question in enumerate(questions):
        lowered = question.lower()
        if any(token in question for token in ("증빙", "자료", "원본")):
            fact_scope = "사실관계 중 증빙·신고 자료"
        elif any(token in question for token in ("조건", "바뀌", "변형")):
            fact_scope = "사실관계에서 결론을 바꾸는 조건"
        elif any(token in question for token in ("법리", "조문", "요건", "구분", "분류", "순서")):
            fact_scope = "사실관계 중 법적 요건과 예외"
        else:
            fact_scope = "사실관계의 핵심 거래와 처분"

        step_article_ids: list[str] = []
        legal_refs: list[str] = []
        if article_ids and index < len(article_ids):
            article_id = article_ids[index]
            step_article_ids = [article_id]
            legal_refs = [article_labels[article_id]]
        elif law_map:
            rule_item = law_map[index % len(law_map)]
            reference = clean_learner_copy(rule_item.get("article_reference"))
            legal_refs = [reference or law_name]
        else:
            legal_refs = [law_name]

        step_evidence: list[str] = []
        if evidence:
            if index < len(evidence):
                step_evidence.append(evidence[index])
            if index == block_count - 1 and len(evidence) > block_count:
                step_evidence.extend(evidence[block_count:])

        accounting_note: str | None = None
        if accounting_item and index == block_count - 1:
            parts = [
                accounting_item.get("accounting_treatment"),
                accounting_item.get("reconciliation"),
                accounting_item.get("tax_adjustment"),
            ]
            parts = [clean_learner_copy(part) for part in parts if clean_learner_copy(part)]
            if parts:
                accounting_note = " ".join(parts)

        explanation = easy[index] if index < len(easy) else (easy[0] if easy else legal_refs[0])
        blocks.append(
            {
                "block_no": index + 1,
                "question": question,
                "fact_scope": fact_scope,
                "legal_refs": legal_refs,
                "article_ids": step_article_ids,
                "answer": answers[index] or legal_refs[0],
                "explanation": clean_learner_copy(explanation),
                "evidence": step_evidence,
                "precedent_refs": precedent_refs if index == block_count - 1 else [],
                "accounting_note": accounting_note,
            }
        )

    transfer = clean_learner_copy(extract_heading_text(document, "변형사례"))
    concept = clean_learner_copy(
        topic.get("concept_key") or topic.get("canonical_title") or law_name
    )
    rule_chain = " → ".join(rule.rstrip(". ") for rule in rules[:3])
    summary_answer = next((value for value in reversed(answers) if value), "")
    if not summary_answer:
        summary_answer = clean_learner_copy(rules[-1])
    summary = clean_learner_copy(
        f"{concept}: {rule_chain}. 이 사실관계의 결론은 {summary_answer}"
    )
    return case_facts, blocks, transfer, summary, recall_questions


def references_from_topic(topic: dict[str, Any]) -> list[str]:
    """Fallback article IDs for topics not expanded into learning.articles."""
    references: list[str] = []
    for value in topic.get("laws_and_articles", []):
        if not isinstance(value, str):
            continue
        match = ARTICLE_REF_PATTERN.search(value)
        if not match:
            continue
        code = next(
            (key for key, name in LAW_NAMES.items() if name == match.group("law")),
            None,
        )
        if not code:
            continue
        for number in re.findall(r"제\s*([0-9]+(?:의[0-9]+)?)", value):
            references.append(f"{code}-{number.replace('의', '-')}")
    return unique(references)


def related_references_from_topic(topic: dict[str, Any]) -> list[dict[str, str]]:
    """Keep decree/rule citations visible even when a full-text snapshot is absent."""
    result: list[dict[str, str]] = []
    for value in topic.get("laws_and_articles", []):
        if not isinstance(value, str):
            continue
        matched_name = None
        for law_name in LAW_NAMES.values():
            if law_name in value:
                matched_name = law_name
                break
        if matched_name is None:
            continue
        if value == matched_name:
            continue
        if "시행령" in value:
            linked_name = matched_name + "시행령"
        elif "시행규칙" in value:
            linked_name = matched_name + "시행규칙"
        else:
            linked_name = matched_name
        result.append(
            {
                "reference": value,
                "law_name": linked_name,
                "official_url": f"https://www.law.go.kr/법령/{linked_name}",
                "text_status": "selected article text" if value.startswith(matched_name + " 제") else "reference link",
            }
        )
    return unique(result)


def index_precedents(
    source_root: Path,
    learning: dict[str, Any],
    curriculum: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Merge the curriculum, learning, current and latest public case indexes."""
    merged: dict[str, dict[str, Any]] = {}
    aliases: dict[str, str] = {}

    def add(raw: dict[str, Any], source: str) -> None:
        if not isinstance(raw, dict):
            return
        case_id = raw.get("case_id") or raw.get("precedent_id")
        case_number = raw.get("case_number")
        if not isinstance(case_id, str) and not isinstance(case_number, str):
            return
        canonical = case_id if isinstance(case_id, str) else f"case:{case_number}"
        current = merged.setdefault("" if canonical is None else canonical, {})
        for key, value in raw.items():
            if value not in (None, "", [], {}):
                current[key] = value
        current.setdefault("source_indexes", []).append(source)
        if isinstance(case_number, str):
            aliases[case_number] = canonical
        if isinstance(raw.get("precedent_id"), str):
            aliases[raw["precedent_id"]] = canonical
        if isinstance(raw.get("case_id"), str):
            aliases[raw["case_id"]] = canonical

    for value in curriculum.get("cases", []):
        add(value, "curriculum.json/cases")
    for value in learning.get("precedents", []):
        add(value, "laws/learning.json/precedents")
    for filename in ("data/latest-precedents.json", "data/exam-important-precedents.json"):
        path = source_root / filename
        if path.exists():
            for value in read_json(path):
                add(value, filename)

    # Alias resolution is kept in the output so the bootstrap remains auditable.
    for key, value in aliases.items():
        if value in merged:
            merged[value].setdefault("aliases", []).append(key)
    return merged


def selected_precedent_ids(
    issue_id: str,
    topic: dict[str, Any],
    matching_articles: list[dict[str, Any]],
) -> list[str]:
    ids: list[str] = []
    ids.extend(
        value
        for value in topic.get("related_case_ids", [])
        if isinstance(value, str)
    )
    for article in matching_articles:
        for key in (
            "case_ids",
            "precedent_ids",
            "direct_precedent_ids",
            "related_precedent_ids",
            "catalog_precedent_ids",
        ):
            raw = article.get(key, [])
            if isinstance(raw, list):
                ids.extend(str(value) for value in raw if isinstance(value, str))
        for issue in article.get("issues", []):
            if isinstance(issue, dict) and issue.get("issue_id") == issue_id:
                for key in ("case_ids", "precedent_ids"):
                    raw = issue.get(key, [])
                    if isinstance(raw, list):
                        ids.extend(str(value) for value in raw if isinstance(value, str))
    return list(dict.fromkeys(ids))


def resolve_precedents(
    ids: list[str],
    issue_id: str,
    merged: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    aliases: dict[str, str] = {}
    for canonical, value in merged.items():
        for alias in value.get("aliases", []):
            aliases[str(alias)] = canonical
        for key in ("case_id", "precedent_id", "case_number"):
            if isinstance(value.get(key), str):
                aliases[value[key]] = canonical
    # Newer records are also discoverable by topic even when the article index
    # has not yet been assigned a direct case ID.
    for canonical, value in merged.items():
        if issue_id in value.get("related_topic_ids", []):
            ids.append(canonical)

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in ids:
        canonical = aliases.get(value, value)
        record = merged.get(canonical)
        if record is None and ":" in value:
            parts = value.split(":")
            record = merged.get(aliases.get(parts[1], parts[1]))
            canonical = aliases.get(parts[1], parts[1])
        if record is None or canonical in seen:
            continue
        official = record.get("official_source_url") or record.get("official_url")
        if not is_official_url(official):
            continue
        dedupe_key = str(record.get("case_number") or official or canonical)
        if dedupe_key in seen:
            continue
        seen.add(canonical)
        seen.add(dedupe_key)
        result.append(
            {
                "precedent_id": record.get("precedent_id") or record.get("case_id") or canonical,
                "case_number": record.get("case_number"),
                "decision_date": record.get("decision_date"),
                "court": record.get("court", "대법원"),
                "title": record.get("canonical_title"),
                "issue_summary": record.get("issue_summary"),
                "holding_summary": record.get("holding_summary"),
                "significance": record.get("significance"),
                "distinguishing_facts": record.get("distinguishing_facts", []),
                "disposition_summary": record.get("disposition_summary"),
                "official_source_url": official,
                "source_as_of": record.get("source_as_of"),
                "source_provenance": unique(record.get("source_indexes", [])),
            }
        )
    return result


def article_records(
    source_root: Path, article_ids: list[str]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    for code in LAW_FILE_CODES:
        path = source_root / "data" / "laws" / f"{code.lower()}.json"
        if not path.exists():
            continue
        law = read_json(path)
        for article in law.get("articles", []):
            by_id[article["article_id"]] = article
    result: list[dict[str, Any]] = []
    for article_id in article_ids:
        article = by_id.get(article_id)
        if article is None:
            raise ValueError(f"article source missing: {article_id}")
        official = article.get("official_url")
        if not is_official_url(official):
            raise ValueError(f"article has no official URL: {article_id}")
        current_versions = [
            version
            for version in article.get("versions", [])
            if version.get("status") == "current"
        ] or article.get("versions", [])[:1]
        result.append(
            {
                "article_id": article_id,
                "law_code": article_id.split("-", 1)[0],
                "article_number": article.get("article_number"),
                "title": article.get("title"),
                "official_url": official,
                "source_url": article.get("source_url"),
                "source_as_of": article.get("source_as_of"),
                "content_status": article.get("content_status"),
                "versions": current_versions,
            }
        )
    return result, by_id


def build_content(source_root: Path, output_root: Path) -> dict[str, Any]:
    selection = read_json(output_root / "content" / "issue-selection.json")
    learning = read_json(source_root / "data" / "laws" / "learning.json")
    curriculum = read_json(source_root / "data" / "curriculum.json")
    curriculum_topics = {
        item["topic_id"]: item for item in curriculum.get("topics", [])
    }
    learning_articles = learning.get("articles", [])
    memberships: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for article in learning_articles:
        for issue_id in issue_memberships(article):
            memberships[issue_id].append(article)

    # Import the canonical safe Markdown renderer from the existing site.
    source_src = (source_root / "src").resolve()
    if str(source_src) not in sys.path:
        sys.path.insert(0, str(source_src))
    from tax_study.lesson_reader import (  # type: ignore
        _render_section,
        parse_curriculum_material_markdown,
    )

    precedents = index_precedents(source_root, learning, curriculum)
    issues: list[dict[str, Any]] = []
    all_article_ids: list[str] = []
    all_precedents: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}

    for law in selection.get("laws", []):
        law_code = law["law_code"]
        issue_ids = law.get("issue_ids", [])
        if len(issue_ids) != 10 or len(set(issue_ids)) != 10:
            raise ValueError(f"{law_code} must contain exactly 10 unique issues")
        counts[law_code] = len(issue_ids)
        for position, issue_id in enumerate(issue_ids, start=1):
            topic = curriculum_topics.get(issue_id)
            if topic is None:
                raise ValueError(f"curriculum topic missing: {issue_id}")
            material_path = topic.get("material_path")
            if not isinstance(material_path, str):
                raise ValueError(f"material path missing: {issue_id}")
            markdown_path = source_root / material_path
            if not markdown_path.exists():
                raise ValueError(f"lesson source missing: {material_path}")
            markdown = markdown_path.read_text(encoding="utf-8")
            document = parse_curriculum_material_markdown(markdown)
            selected_articles = memberships.get(issue_id, [])
            article_ids: list[str] = []
            for article in selected_articles:
                article_ids.append(article["article_id"])
            if not article_ids:
                article_ids = references_from_topic(topic)
            article_ids = list(dict.fromkeys(article_ids))
            if not article_ids:
                raise ValueError(f"article mapping missing: {issue_id}")
            all_article_ids.extend(article_ids)

            nested: list[dict[str, Any]] = []
            for article in selected_articles:
                for item in article.get("issues", []):
                    if isinstance(item, dict) and item.get("issue_id") == issue_id:
                        nested.append(item)
            core_question = clean_question_text(
                nested[0].get("core_question")
                if nested and nested[0].get("core_question")
                else extract_prompt(document)
            )
            law_map: list[dict[str, Any]] = []
            for item in nested:
                law_map.extend(item.get("law_map", []))
            if not law_map:
                law_map = [
                    {
                        "article_reference": value,
                        "law_name": law["law_name"],
                        "provenance": "curriculum_topic_and_official_article",
                        "rule_summary": "해당 조문의 현행 원문과 사건 당시 적용법을 나란히 대조한다.",
                    }
                    for value in topic.get("laws_and_articles", [])
                    if isinstance(value, str) and value != law["law_name"]
                ]
            law_map = unique(law_map)

            beginner = []
            audit = []
            accounting = []
            for article in selected_articles:
                beginner.extend(values_for_issue(article, "beginner_explanation", issue_id))
                audit.extend(values_for_issue(article, "audit_application", issue_id))
                accounting.extend(values_for_issue(article, "accounting_tax_adjustment", issue_id))
            for item in nested:
                # Some older rows keep issue-scoped values on the issue itself.
                for key, target in (
                    ("beginner_explanation", beginner),
                    ("audit_application", audit),
                    ("accounting_tax_adjustment", accounting),
                ):
                    if item.get(key):
                        target.extend(item[key] if isinstance(item[key], list) else [item[key]])
            beginner = unique(beginner)
            audit = unique(audit)
            accounting = unique(accounting)
            # The source index contains a few author-facing workflow labels.
            # Keep the data shape intact, but remove those labels before the
            # records reach the public learner-facing snapshot.
            law_map = clean_records(law_map)
            beginner = clean_records(beginner)
            audit = clean_records(audit)
            accounting = clean_records(accounting)

            rendered_sections = {
                section.anchor: _render_section(section)
                for section in document.sections
                if section.anchor != "exam"
            }
            precedent_ids = selected_precedent_ids(issue_id, topic, selected_articles)
            resolved_precedents = clean_precedent_records(
                resolve_precedents(precedent_ids, issue_id, precedents)
            )
            for item in resolved_precedents:
                key = item.get("precedent_id") or item.get("case_number")
                if key:
                    all_precedents[str(key)] = item

            case_facts, question_blocks, transfer_case, final_summary, recall_questions = build_question_blocks(
                issue_id=issue_id,
                core_question=core_question,
                law_name=law["law_name"],
                article_ids=article_ids,
                selected_articles=selected_articles,
                law_map=law_map,
                beginner=beginner,
                audit=audit,
                accounting=accounting,
                resolved_precedents=resolved_precedents,
                document=document,
                topic=topic,
            )

            # Preserve useful source metadata without exposing the old fixed ratio.
            material_meta = clean_records(dict(document.metadata))
            material_meta.pop("source_as_of", None)
            material_meta.pop("tax_as_of", None)
            material_meta.pop("accounting_as_of", None)
            issues.append(
                {
                    "issue_id": issue_id,
                    "law_code": law_code,
                    "law_name": law["law_name"],
                    "position": position,
                    # The curriculum title is the stable public label.  The
                    # Markdown H1 may carry a source-specific suffix such as
                    # “학습 레슨”, which is provenance rather than navigation
                    # copy.
                    "title": topic.get("canonical_title") or document.title,
                    "canonical_title": topic.get("canonical_title"),
                    "level": topic.get("level"),
                    "core_question": core_question,
                    "easy_explanation": clean_learner_copy(
                        beginner[0].get("text")
                        if beginner and isinstance(beginner[0], dict) and beginner[0].get("text")
                        else extract_easy_explanation(document)
                    ),
                    "article_ids": article_ids,
                    "law_map": law_map,
                    "related_references": related_references_from_topic(topic),
                    "beginner_explanation": beginner,
                    "audit_application": audit,
                    "accounting_tax_adjustment": accounting,
                    "precedent_ids": [
                        item.get("precedent_id") or item.get("case_number")
                        for item in resolved_precedents
                    ],
                    "precedents": resolved_precedents,
                    "case_facts": case_facts,
                    "question_blocks": question_blocks,
                    "transfer_case": transfer_case,
                    "final_summary": final_summary,
                    "recall_questions": recall_questions,
                    "modules": {
                        "audit": bool(audit) or bool(rendered_sections.get("audit-evidence")),
                        "accounting": any(
                            isinstance(item, dict)
                            and item.get("status") not in {None, "not_applicable"}
                            for item in accounting
                        ),
                        "exam": False,
                    },
                    "source": {
                        "lesson_path": material_path,
                        "lesson_title": document.title,
                        "lesson_source_as_of": document.metadata.get("source_as_of"),
                        "lesson_material_id": document.metadata.get("material_id"),
                        "topic_id": topic.get("topic_id"),
                        "curriculum_source_as_of": topic.get("source_as_of"),
                        "source_root": "tax-study 공개 원천",
                    },
                    "lesson_lead": re.sub(
                        r"\s*비중:\s*.*$", "", clean_learner_copy(document.lead)
                    ).strip(" ·"),
                    "estimated_minutes": document.estimated_minutes,
                    "audience": document.audience,
                    "material_metadata": material_meta,
                }
            )

    issues.sort(key=lambda item: (item["law_code"], item["position"]))
    article_list, article_index = article_records(
        source_root, list(dict.fromkeys(all_article_ids))
    )
    article_list.sort(key=lambda item: (item["law_code"], item["article_id"]))
    output = {
        "schema_version": 3,
        "generated_as_of": selection.get("selection_as_of"),
        "source_repository": "tax-study",
        "laws": [
            {
                "law_code": item["law_code"],
                "law_name": item["law_name"],
                "issue_count": counts[item["law_code"]],
                "issue_ids": item["issue_ids"],
            }
            for item in selection["laws"]
        ],
        "issues": issues,
        "article_count": len(article_list),
        "precedent_count": len(all_precedents),
    }
    write_json(output_root / "content" / "issues.json", output)
    write_json(
        output_root / "content" / "articles.json",
        {
            "schema_version": 1,
            "generated_as_of": selection.get("selection_as_of"),
            "articles": article_list,
        },
    )
    write_json(
        output_root / "content" / "precedents.json",
        {
            "schema_version": 1,
            "generated_as_of": selection.get("selection_as_of"),
            "precedents": sorted(
                all_precedents.values(),
                key=lambda item: (item.get("decision_date") or "", item.get("case_number") or ""),
                reverse=True,
            ),
        },
    )

    if len(issues) != 50 or len({item["issue_id"] for item in issues}) != 50:
        raise ValueError(f"expected 50 unique issues, got {len(issues)}")
    for code, count in counts.items():
        actual = sum(1 for item in issues if item["law_code"] == code)
        if actual != count:
            raise ValueError(f"{code}: expected {count}, got {actual}")
    for item in article_list:
        if not is_official_url(item.get("official_url")):
            raise ValueError(f"article URL is not official: {item['article_id']}")
    for item in all_precedents.values():
        if not is_official_url(item.get("official_source_url")):
            raise ValueError(f"precedent URL is not official: {item}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("../tax-study"),
        help="path to the existing public tax-study source repository",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    result = build_content(source_root, output_root)
    print(f"generated {len(result['issues'])} issues")
    for law in result["laws"]:
        print(f"{law['law_code']} {law['law_name']}: {law['issue_count']}")
    print(f"articles: {result['article_count']}; precedents: {result['precedent_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
