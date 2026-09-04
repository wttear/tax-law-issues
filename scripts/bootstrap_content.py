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
    target = f"### {heading}"
    collected: list[str] = []
    started = False
    for section in document.sections:
        if started and str(getattr(section, "heading", "")).startswith("## "):
            break
        for line in section.lines:
            stripped = line.strip()
            if not started:
                if stripped == target:
                    started = True
                continue
            if stripped.startswith("### ") or stripped.startswith("## "):
                return " ".join(collected)
            if not stripped or "|" in stripped:
                continue
            if stripped.startswith("-"):
                stripped = stripped[1:].strip()
            if stripped:
                collected.append(stripped)
    return " ".join(collected)


def extract_heading_paragraphs(document: Any, heading: str) -> list[str]:
    """Return prose paragraphs under a heading without splitting sentences."""
    target = f"### {heading}"
    paragraphs: list[str] = []
    current: list[str] = []
    started = False

    def flush() -> None:
        if current:
            paragraphs.append(clean_learning_text(" ".join(current)))
            current.clear()

    for section in document.sections:
        if started and str(getattr(section, "heading", "")).startswith("## "):
            break
        for line in section.lines:
            stripped = line.strip()
            if not started:
                if stripped == target:
                    started = True
                continue
            if stripped.startswith("### ") or stripped.startswith("## "):
                flush()
                return [paragraph for paragraph in paragraphs if paragraph]
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
    target = f"### {heading}"
    result: list[str] = []
    started = False
    for section in document.sections:
        if started and str(getattr(section, "heading", "")).startswith("## "):
            break
        for line in section.lines:
            stripped = line.strip()
            if not started:
                if stripped == target:
                    started = True
                continue
            if stripped.startswith("### ") or stripped.startswith("## "):
                return result
            match = re.match(r"^[0-9]+\.\s+(.+)$", stripped)
            if match:
                result.append(clean_learning_text(match.group(1)))
    return result


JUDGMENT_TYPE_BY_LABEL = {
    "법리 구분": "rule",
    "증빙 선택": "evidence",
    "새 사실 전이": "change",
}
JUDGMENT_TYPE_LABELS = {
    "rule": "법리",
    "calculation": "계산",
    "evidence": "증빙",
    "change": "조건 변경",
}
ALIGNMENT_STOPWORDS = {
    "그리고",
    "그러나",
    "따라서",
    "통해",
    "대해",
    "대한",
    "관련",
    "해당",
    "이때",
    "이상",
    "이하",
    "경우",
    "부분",
    "방법",
    "자료",
    "원본",
    "확인",
    "검토",
    "판단",
    "기준",
    "요건",
    "결론",
    "적용",
    "계산",
    "금액",
    "내용",
    "사례",
    "사실",
    "법리",
    "구분",
    "증빙",
    "선택",
    "전이",
    "새",
    "보면",
    "살펴",
    "먼저",
    "다시",
    "각각",
    "어떤",
    "무엇",
    "어떻게",
    "필요",
    "가능",
    "별도",
    "대상",
    "여부",
    "세무상",
    "법정",
    "실제",
    "관계",
    "처분",
    "신고",
}
VAGUE_QUESTION_PHRASES = (
    "어떤 순서",
    "어떻게 설명",
    "어떻게 연결할",
    "무엇을 고를",
    "어떤 자료로 결론낼",
)


def extract_answer_core_units(document: Any) -> list[dict[str, str]]:
    """Parse the source lesson's three labelled answer anchors.

    ``답안 핵심요소`` is intentionally treated as data rather than prose to
    be distributed by list index.  Each label becomes one judgment unit, so
    its question and answer can be generated from the same claim.
    """
    raw = clean_learner_copy(extract_heading_text(document, "답안 핵심요소"))
    if not raw:
        return []
    marker = re.compile(r"(법리 구분|증빙 선택|새 사실 전이)\s*:\s*")
    matches = list(marker.finditer(raw))
    if not matches:
        return []
    units: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        answer = clean_learner_copy(raw[match.end() : end]).strip(" .")
        if not answer:
            continue
        # Source lessons use author-facing verbs in this section.  Keep the
        # substantive conclusion but phrase it as something the learner can
        # apply immediately.
        answer = re.sub(r"\s*포함해야 한다\.?", " 적용한다.", answer)
        answer = re.sub(r"\s*확인해야 한다\.?", " 확인한다.", answer)
        answer = re.sub(r"\s*검토해야 한다\.?", " 검토한다.", answer)
        answer = re.sub(r"\s*고른다\.?", " 확인한다.", answer)
        answer = re.sub(r"\s*써야 한다\.?", " 적용한다.", answer)
        answer = re.sub(r"\s*말해야 한다\.?", " 판단한다.", answer)
        answer = re.sub(r"계산을 제시해야 한다\.?", "계산이다.", answer)
        answer = answer.replace("해야 한다", "한다")
        answer = re.sub(r"\s+", " ", answer).strip(" .")
        units.append(
            {
                "label": match.group(1),
                "judgment_type": JUDGMENT_TYPE_BY_LABEL[match.group(1)],
                "answer": answer,
            }
        )
    return units


def extract_recall_questions_by_type(document: Any) -> dict[str, str]:
    """Return the source recall prompts keyed by their labelled purpose."""
    result: dict[str, str] = {}
    fallback_types = ("rule", "evidence", "change")
    for index, raw in enumerate(extract_numbered_items(document, "오늘의 회상 3문항")):
        label_match = re.match(r"^(법리 구분|증빙 선택|새 사실 전이)\s*:", raw)
        judgment_type = (
            JUDGMENT_TYPE_BY_LABEL[label_match.group(1)]
            if label_match
            else fallback_types[min(index, len(fallback_types) - 1)]
        )
        question = clean_question_text(raw)
        if question and judgment_type not in result:
            result[judgment_type] = question
    return result


def extract_focus_terms(text: str, *, limit: int = 4) -> list[str]:
    """Pick concrete words/numbers that let a question point to its answer."""
    tokens = re.findall(r"제\s*\d+조(?:의\d+)?|[가-힣A-Za-z]{2,}|\d[\d,\.]*", text)
    result: list[str] = []
    for token in tokens:
        normalized = token.strip(".,")
        if not normalized or normalized in ALIGNMENT_STOPWORDS:
            continue
        if normalized not in result:
            result.append(normalized)
        if len(result) >= limit:
            break
    return result


def format_focus_terms(terms: list[str], *, limit: int = 3) -> str:
    """Render answer nouns as a readable phrase, retaining concrete tokens."""
    rendered: list[str] = []
    for token in terms:
        if (
            rendered
            and re.fullmatch(r"\d[\d,\.]*", rendered[-1])
            and re.fullmatch(r"[가-힣]{1,4}", token)
        ):
            rendered[-1] += token
        else:
            rendered.append(token)
    return " ".join(rendered[:limit])


def focus_subject(terms: list[str]) -> str:
    """Prefer article references together when a rule answer starts with them."""
    article_terms = [term for term in terms if term.startswith("제") and "조" in term]
    if len(article_terms) >= 2:
        return "·".join(article_terms[:2])
    return format_focus_terms(terms)


def object_particle(phrase: str) -> str:
    """Choose a readable 을/를 after a formula or noun phrase."""
    compact = re.sub(r"[^가-힣A-Za-z0-9]", "", phrase)
    if not compact:
        return "을"
    if "%" in phrase:
        return "를"
    last = compact[-1]
    if "가" <= last <= "힣":
        jongseong = (ord(last) - ord("가")) % 28
        return "을" if jongseong else "를"
    return "을"


def subject_particle(phrase: str) -> str:
    """Choose 이/가 for a noun phrase used as a changed fact."""
    compact = re.sub(r"[^가-힣A-Za-z0-9]", "", phrase)
    if not compact:
        return "이"
    last = compact[-1]
    if "가" <= last <= "힣":
        return "이" if (ord(last) - ord("가")) % 28 else "가"
    return "이"


def topic_particle(phrase: str) -> str:
    """Choose 은/는 for a result noun used as a question topic."""
    compact = re.sub(r"[^가-힣A-Za-z0-9]", "", phrase)
    if not compact:
        return "은"
    last = compact[-1]
    if "가" <= last <= "힣":
        return "은" if (ord(last) - ord("가")) % 28 else "는"
    return "은"


def with_object_particle(phrase: str) -> str:
    """Add 을/를 unless the source phrase already carries an object marker."""
    if phrase.endswith(("을", "를")):
        return phrase
    phrase = re.sub(r"(으로|로|은|는|이|가|에|의|와|과)$", "", phrase)
    return f"{phrase}{object_particle(phrase)}"


def make_rule_question_from_answer(answer: str) -> str:
    """Turn the first rule clause into a single, readable judgment prompt."""
    if all(term in answer for term in ("성립", "확정", "소멸")):
        return "사업연도 말에 납세의무가 성립하고 신고로 확정되며 납부·충당으로 소멸하는 기준은 무엇인가?"
    if "사업장 전체 소득금액" in answer:
        return "사업장 전체 소득금액을 먼저 계산한 뒤 구성원별 귀속을 판단하는 기준은 무엇인가?"
    if "권리의 법률상 성립" in answer:
        return "권리의 법률상 성립·실현가능성·법정 대손요건을 단계별로 구분하는 기준은 무엇인가?"
    if "법 제40조" in answer and "실지귀속" in answer:
        return "법 제40조·영 제81조의 실지귀속·공통분 안분 순서는 무엇인가?"
    if "소득종류와 비과세" in answer:
        return "소득종류와 비과세 여부를 먼저 판단하는 기준은 무엇인가?"
    if "제16조" in answer and "제17조" in answer:
        return "제16조·제17조의 이자·배당 판정 기준은 무엇인가?"
    if "영구적 차이" in answer and "일시적 차이" in answer:
        return "영구적 차이와 일시적 차이의 소득처분·후속관리 기준은 무엇인가?"
    if "기대신용손실" in answer and "충당금" in answer:
        return "기대신용손실은 회계상 추정이고 대손금은 법정 요건에 따른 손실일 때 두 항목의 구분 기준은 무엇인가?"
    if "익금산입은 과세소득 조정" in answer:
        return "익금산입은 과세소득 조정이고 소득처분은 귀속 표시일 때 유보·상여를 구분하는 기준은 무엇인가?"
    if "거래일 특수관계" in answer:
        return "거래일 특수관계 확인부터 시가·대가·조세부담 감소를 판단하는 기준은 무엇인가?"
    if "K-IFRS" in answer and "문단 35" in answer:
        return "K-IFRS 문단 35의 기간 이행 요건과 세법상 작업진행률을 어떻게 구분하는가?"
    if "법률의 구체적 위임" in answer:
        return "법률의 구체적 위임과 내부지침의 과세요건 창설 여부를 판단하는 기준은 무엇인가?"
    if "순자산 감소" in answer:
        return "순자산 감소·사업관련성·통상성·수익 직접관련성의 손금 요건은 무엇인가?"
    if "자산의 실제 용도" in answer and "지급이자" in answer:
        return "자산의 실제 용도·객관적 사업진행을 먼저 확인한 뒤 지급이자 적수를 계산하는 기준은 무엇인가?"
    if "특수관계 확인 뒤" in answer:
        return "특수관계 확인 후 실제 대가·비교가능 시가·조세부담 감소를 판단하는 기준은 무엇인가?"
    if "현금 유입일" in answer:
        return "현금 유입일과 계약상 권리 확정 시점을 구분해 소득 귀속시기를 판단하는 기준은 무엇인가?"
    if "장부를 출발점" in answer:
        return "장부와 관계 증거를 기준으로 부분 오류를 보정하는 근거과세의 판단 기준은 무엇인가?"
    if "과세관청의 초기 입증" in answer:
        return "과세관청의 초기 입증과 납세자의 반증을 나누는 기준은 무엇인가?"
    if "신고·무신고·부정행위" in answer:
        return "신고·무신고·부정행위별 제척기간의 기산일과 만료일을 구분하는 기준은 무엇인가?"
    if "본세와 가산세" in answer:
        return "본세와 가산세를 구분하고 정당한 사유를 판단하는 기준은 무엇인가?"
    if "후속 질문" in answer:
        return "후속 접촉이 세무조사인지와 재조사 예외 여부를 판단하는 기준은 무엇인가?"
    if "사전통지의 기재사항" in answer:
        return "사전통지의 기재사항·20일 요건·예외사유를 판단하는 기준은 무엇인가?"
    if "중복조사는" in answer:
        return "중복조사와 미통지의 절차상 하자가 처분에 미치는 효과는 무엇인가?"
    if "수익적 지출 후보" in answer and "취득가액" in answer:
        return "정상 기능 유지·원상회복과 가치·수명·생산능력 증가분을 자본적·수익적 지출로 구분하는 기준은 무엇인가?"
    if "상각부인액" in answer and "시인부족" in answer:
        return "회사계상액이 한도를 넘거나 모자랄 때 유보액과 전기 부인액을 조정하는 기준은 무엇인가?"
    if "익금산입은 과세소득 조정" in answer:
        return "익금산입과 소득처분(유보·상여)을 구분하는 기준은 무엇인가?"
    if "과세요건상 입증" in answer:
        return "필요경비의 과세요건상 입증과 특별사실의 자료요구를 구분하는 기준은 무엇인가?"

    first = re.split(r"[.!?]", answer, maxsplit=1)[0].strip()
    article_terms = list(dict.fromkeys(re.findall(r"제\s*\d+조(?:의\d+)?", answer)))
    if article_terms:
        references = "·".join(article_terms[:5])
        if "책임한도" in answer:
            return "구 제39조와 현행 제39조의 제2차 납세의무·책임한도 적용 기준은 무엇인가?"
        if "신고납부" in answer and "강제징수" in answer:
            return f"{references}의 신고납부·납부고지·독촉·강제징수 절차는 어떻게 이어지는가?"
        if "재화 공급" in answer and "용역 공급" in answer:
            return f"{references}의 재화·용역 공급 주체와 책임은 어떻게 판단하는가?"
        if "압류" in answer and "통지" in answer:
            return f"{references}의 압류·통지 요건과 효력은 어떻게 연결되는가?"
        if "법정기일" in answer:
            return f"{references}의 법정기일·담보·특별보호 우선순위는 어떻게 정하는가?"
        if "불공제" in answer:
            return f"{references}의 불공제 요건과 예외는 무엇인가?"
        if "수출" in answer and "수입" in answer:
            return f"{references}의 수출 영세율과 수입세액 적용 요건은 무엇인가?"
        return f"이 사례에서 {references}를 적용할 때 충족해야 할 요건과 세무상 효과는 무엇인가?"

    # Stop at the first action verb so the question contains the concrete
    # facts but not the answer's whole procedural sentence.
    if " 종합하고" in first or " 종합하며" in first:
        subject = re.split(r"\s+종합하고|\s+종합하며", first, maxsplit=1)[0].strip(" ,")
        return f"{with_object_particle(subject)} 종합해 소득을 구분하는 기준은 무엇인가?"
    if " 차례로" in first:
        subject = first.split(" 차례로", 1)[0].strip(" ,")
        return f"{subject} 차례로 구분하는 기준은 무엇인가?"
    if re.search(r"(?:으로|로)\s+먼저", first):
        left = re.split(r"(?:으로|로)\s+먼저", first, maxsplit=1)[0].strip(" ,")
        particle = "를" if re.search(r"문단\s*\d+$", left) else object_particle(left)
        return f"{left}{particle} 기준으로 판단하는 요건은 무엇인가?"
    if " 먼저" in first:
        subject = first.split(" 먼저", 1)[0].strip(" ,")
        return f"{with_object_particle(subject)} 먼저 판단하고 이후 결론을 정하는 기준은 무엇인가?"
    if "으로" in first and "으로써" not in first:
        left, right = first.split("으로", 1)
        target = right.strip().split("을", 1)[0].split("를", 1)[0].strip(" ,")
        if left.strip() and target:
            return f"{with_object_particle(left.strip())} 기준으로 {target}을 판단하는 기준은 무엇인가?"
    if first:
        first = re.sub(
            r"\s*(?:적용한다|판단한다|검토한다|설명한다|구분한다|나눈다|정한다|연결한다|기록한다|맞춰야 한다|핵심이다|다르다|한다|이다)\.?$",
            "",
            first,
        ).strip(" ,")
        first = re.sub(r"[을를]$", "", first)
        if any(term in first for term in ("인지", "여부", "요건", "기준")):
            first = re.sub(r"[을를]$", "", first)
            return f"{first}의 구분 기준은 무엇인가?"
        return f"{first}의 판단 기준은 무엇인가?"
    subject = format_focus_terms(extract_focus_terms(answer)) or "이 쟁점"
    return f"{subject}의 판단 기준은 무엇인가?"


EVIDENCE_ACTION_PATTERN = re.compile(
    r"(?:함께\s+)?(?:보고|확인하고|확인|선택하고|선택|검토하고|검토|"
    r"입증하고|입증|증명하고|증명|대사하고|대사|교차검증하고|교차검증|"
    r"재구성하고|재구성|정리하고|정리|기록하고|기록|검증하고|검증|"
    r"비교하고|비교|맞춰|맞추고|맞춘다)"
    r"(?=(?:한다|한다며|하고|하며|해|하여|\s|$))"
)


def strip_case_marker(value: str) -> str:
    """Remove a final Korean case particle before composing a new sentence."""
    value = value.strip(" .")
    # ``의`` is intentionally omitted: words such as ``변경합의`` and
    # ``주의`` legitimately end with that syllable and are common evidence
    # labels.  The remaining particles are unambiguous in these short
    # source phrases.
    value = re.sub(r"(?:으로써|으로|로|에서|에게|부터|까지|보다|처럼|만큼|은|는|이|가|을|를|에|도|만|와|과)$", "", value)
    return value.strip(" .")


def clean_evidence_part(value: str) -> str:
    """Trim source verbs left after an evidence bundle or target."""
    value = value.strip(" ,.")
    value = re.sub(r"\s+(?:먼저|우선)$", "", value)
    value = re.sub(
        r"\s*(?:확인|선택|검토|입증|증명|대사|교차검증|재구성|정리|기록|검증|비교|맞춰|맞추고|맞춘다)"
        r"(?:한다|하고|하며|해|하여|한다며|맞춰)$",
        "",
        value,
    )
    value = re.sub(r"\s+(?:먼저|우선)$", "", value)
    value = re.sub(r"\s*(?:한다|하고|하며|이다|다)$", "", value)
    return strip_case_marker(value)


def parse_evidence_clause(clause: str) -> tuple[str, str]:
    """Return a document bundle and the fact it is used to check."""
    clause = clause.strip(" .")
    if not clause:
        return "", ""

    # ``A와 별도로 B를 먼저 확인한다`` names an initial document bundle
    # and then the fact that must be checked.  Handle this construction
    # before the shorter ``로`` matcher can mistake ``별도로`` for a verb.
    if "와 별도로" in clause:
        before, after = clause.split("와 별도로", 1)
        return clean_evidence_part(before), clean_evidence_part(after)

    # Phrases such as ``장부를 ... 맞추고 오류가 ...`` put the document
    # bundle before the action; keep the trailing target as a separate cue.
    action = EVIDENCE_ACTION_PATTERN.search(clause)
    marker = re.match(r"^(.+?)(?:은|는|이|가)\s+(.+)$", clause)
    preposition = re.match(r"^(.+?)(?:으로|로)\s+(.+)$", clause)
    joining = re.match(r"^(.+?)(?:에|에는)\s+(.+)$", clause)

    # A noun particle at the start of a clause should win over an action
    # found later (``대조표는 동일성 ... 증명한다``).  Conversely, an
    # action wins when a lexical word such as ``같은`` creates a false
    # ``은`` match after it (``표준을 선택하고 같은 ...``).
    candidates = [item for item in (marker, preposition, joining) if item]
    earliest = min(candidates, key=lambda item: len(item.group(1))) if candidates else None
    earliest_pos = len(earliest.group(1)) if earliest else None
    earliest_delimiter_end = None
    if earliest:
        delimiter_length = len(earliest.group(0)) - len(earliest.group(1)) - len(earliest.group(2))
        earliest_delimiter_end = len(earliest.group(1)) + delimiter_length
    if earliest and (
        not action
        or (
            earliest_pos is not None
            and earliest_delimiter_end is not None
            and earliest_pos < action.start()
            and earliest_delimiter_end < action.start()
        )
    ):
        return clean_evidence_part(earliest.group(1)), clean_evidence_part(earliest.group(2))

    if action:
        before = clause[: action.start()].strip()
        after = clause[action.end() :].strip(" ,.")
        # ``A와 별도로 B를 먼저 확인`` has two evidence targets; prefer
        # the first bundle as the anchor and the second phrase as the fact.
        if "와 별도로" in before:
            before, after_before = before.split("와 별도로", 1)
            after = f"{after_before} {after}".strip()
        # ``장부를 PG·금융과 거래단위로 맞추고`` has a document bundle,
        # an intermediate comparison set, and then the verb.  Keep both
        # comparison sets as targets instead of attaching them to the
        # document name.
        object_bundle = re.match(r"^(.+?)(?:을|를)\s+(.+?)(?:으로|로)$", before)
        if object_bundle:
            before = object_bundle.group(1)
            after = f"{object_bundle.group(2)} {after}".strip()
        else:
            before = re.sub(r"(?:을|를)$", "", before).strip()
        if before:
            return clean_evidence_part(before), clean_evidence_part(after)

    if earliest:
        return clean_evidence_part(earliest.group(1)), clean_evidence_part(earliest.group(2))

    return clean_evidence_part(clause), ""


def make_evidence_question_from_answer(
    answer: str,
    evidence: list[str] | None = None,
) -> str:
    """Ask how the named evidence proves the concrete fact in the answer."""
    sentence = re.split(r"[.!?]", answer, maxsplit=1)[0].strip()
    clauses = [part.strip() for part in re.split(r",\s*", sentence) if part.strip()]
    documents: list[str] = []

    def anchor(clause: str) -> str:
        """Take the document bundle before the first evidence action."""
        clause = clause.strip(" .")
        if not clause:
            return ""
        if "대사해야" in clause and "압류대상과 효력시점" in answer:
            return "세 문서의 체납자·지번"
        if "와 별도로" in clause:
            clause = clause.split("와 별도로", 1)[0]
        # Find the earliest reliable boundary.  For ``계약으로 활동 실질을``
        # the preposition comes before the object particle; for
        # ``자료를 계약·계좌와 맞춰`` the object particle comes first.
        object_match = re.match(r"^(.+?)(?:을|를)\s+", clause)
        preposition = re.match(r"^(.+?)(?<!서)(?:으로|로|에)\s+", clause)
        marker = re.match(r"^(.+?)(?:은|는|이|가)\s+", clause)
        candidates: list[tuple[int, str]] = []
        if object_match:
            candidates.append((len(object_match.group(1)), object_match.group(1)))
        if preposition:
            candidates.append((len(preposition.group(1)), preposition.group(1)))
        if marker:
            candidate = marker.group(1).strip(" .")
            if not candidate.endswith(("같", "인허", "가능", "없", "있", "하", "되")):
                candidates.append((len(marker.group(1)), candidate))
        if candidates:
            return min(candidates, key=lambda item: item[0])[1].strip(" .")
        return re.sub(r"(?:\s+(?:먼저|우선))$", "", clause).strip(" .")

    for clause in clauses[:4]:
        document = anchor(clause)
        if document and document not in documents:
            documents.append(document)

    # When the source sentence is only ``자료를 확인한다`` use the audit
    # evidence list as a concrete fallback rather than returning a vague
    # prompt.  The answer itself remains the primary source of wording.
    if evidence:
        documents.extend(item.strip(" .") for item in evidence[:3] if item)
    documents = [item for item in documents if item]
    if "압류대상과 효력시점을 특정" in answer:
        documents = ["세 문서의 체납자·지번"]
    if "결과를 갈랐" in answer:
        documents = ["폐기물 사건의 계약·정산", "파산관재인 사건의 신고이력·해명요구"]
    if "장부·기장자료" in answer:
        documents = ["장부·기장자료"]
    if "등록 명의와 실제 경영" in answer:
        documents = ["동업계약·출자 금융·의사결정 기록·손익분배표"]

    # Keep the prompt short while guaranteeing at least two concrete nouns
    # are shared with the answer.  A second document is added only when the
    # first bundle is a single short label such as ``접수증``.
    selected: list[str] = []
    for document in documents:
        if document not in selected:
            selected.append(document)
        if len(question_answer_tokens(" ".join(selected))) >= 2:
            break
    document_text = "·".join(selected[:2]) or format_focus_terms(extract_focus_terms(answer)) or "관련"
    return f"{document_text} 등 자료는 사실관계의 어느 부분을 입증하는가?"


def make_change_question_from_answer(answer: str) -> str:
    """Ask how the conclusion moves when the answer's changed fact is true."""
    match = re.match(
        r"(.+?(?:되면|하면|이면|나오면|충족되면|확인되면|바뀌면|강해지면|늘면|줄면|사라지면|일치하면|추가되면|제거되면|않으면|없으면|가까우면|라면|다면|지면))",
        answer,
    )
    if match:
        return f"{match.group(1)} 결론은 어떻게 달라지는가?"
    new_fact = re.match(r"(.+?)(이라는|라는) 새 사실은", answer)
    if new_fact:
        subject = f"{new_fact.group(1).strip()}{new_fact.group(2)} 사실"
        return f"{subject}이 확인되면 결론은 어떻게 달라지는가?"
    if "소멸사유를 제거" in answer:
        return "충당 취소는 소멸사유를 제거하므로 충당 대상 1천만 원이 남는지 확인하면 결론은 어떻게 달라지는가?"
    first = re.split(r"[,.]", answer, maxsplit=1)[0].strip(" .")
    if "이므로" in first:
        first = first.split("이므로", 1)[0].strip() + "이면"
        return f"{first} 결론은 어떻게 달라지는가?"
    first = re.sub(r"\s*(?:따라|바꾼다|바뀐다|이어진다|만든다|검토한다|판단한다)\.?$", "", first).strip()
    if "제거하므로" in first:
        first = first.replace("는 소멸사유를 제거하므로", "로 소멸사유가 제거되면")
    if first:
        return f"{first}에 따라 결론은 어떻게 달라지는가?"
    subject = format_focus_terms(extract_focus_terms(answer)) or "사실관계의 조건"
    return f"{subject} 조건이 바뀌면 결론은 어떻게 달라지는가?"


KOREAN_CASE_SUFFIXES = (
    "으로써",
    "으로",
    "에서",
    "에게",
    "부터",
    "까지",
    "보다",
    "처럼",
    "만큼",
    "로",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "도",
    "만",
    "와",
    "과",
)


def alignment_token_stem(token: str) -> str:
    """Normalize a token's final case particle for question/answer matching."""
    if not re.search(r"[가-힣]", token):
        return token
    for suffix in KOREAN_CASE_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 2:
            return token[: -len(suffix)]
    return token


def question_answer_tokens(text: str) -> set[str]:
    return {
        alignment_token_stem(token)
        for token in re.findall(r"[가-힣A-Za-z]{2,}|\d[\d,\.]*", text)
    }


def concrete_answer_tokens(text: str, *, limit: int = 4) -> list[str]:
    """Keep answer tokens that can be reused verbatim in a short prompt."""
    tokens = re.findall(r"[가-힣A-Za-z]{2,}|\d[\d,\.]*", text)
    result: list[str] = []
    for token in tokens:
        token = alignment_token_stem(token)
        if token in ALIGNMENT_STOPWORDS or token in {"한다", "해야", "한다며", "한다는"}:
            continue
        # A noun without a case particle is easier to join with · in a
        # fallback question and still appears verbatim in the answer.
        if token.endswith(("은", "는", "이", "가", "을", "를", "에", "의", "로", "와", "과")):
            continue
        if token not in result:
            result.append(token)
        if len(result) >= limit:
            break
    return result


def normalize_recall_question(question: str, judgment_type: str) -> str:
    """Remove author prompts while preserving a useful source question."""
    text = clean_question_text(question)
    # Apply compound endings before the generic ``어떻게 설명`` rewrite;
    # otherwise ``구분해 무엇인가?`` is left behind.
    text = text.replace("구분해 어떻게 설명할까요?", "구분 기준은 무엇인가?")
    text = text.replace("계산과 결론을 어떻게 설명할까요?", "계산과 결론은 무엇인가?")
    text = text.replace("이유를 어떻게 설명할까요?", "이유는 무엇인가?")
    text = text.replace("을 어떻게 설명할까요?", "은 무엇인가?")
    text = text.replace("를 어떻게 설명할까요?", "는 무엇인가?")
    replacements = {
        "어떤 순서로 판단할까요?": "어떤 요건을 기준으로 판단하는가?",
        "어떤 순서로 구별할까요?": "어떤 요건을 기준으로 구별하는가?",
        "어떻게 설명할까요?": "무엇인가?",
        "무엇을 고를까요?": "어떤 자료가 필요한가?",
        "무엇부터 확인할까요?": "어떤 자료가 필요한가?",
        "어떻게 구분할까요?": "어떤 요건으로 구분하는가?",
        "어떻게 판단할까요?": "어떤 요건으로 판단하는가?",
        "어떻게 계산할까요?": "계산 결과는 얼마인가?",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # A source prompt can still contain a workflow phrase in the middle.
    text = text.replace("어떤 순서로", "어떤 요건을 기준으로")
    text = text.replace("어떻게 설명할", "무엇인지")
    if judgment_type == "evidence":
        text = text.replace("자료를 고를까요", "확인할 자료는 무엇인가")
    if judgment_type == "change":
        text = text.replace("새 사실", "조건")
    text = re.sub(r"\?{2,}$", "?", text)
    return text


def make_question_from_unit(
    unit: dict[str, str],
    recall_question: str,
    evidence: list[str] | None = None,
) -> str:
    """Generate one focused prompt from the very answer it will reveal."""
    judgment_type = unit["judgment_type"]
    answer = unit["answer"]
    focus = extract_focus_terms(answer, limit=8 if judgment_type == "change" else 4)

    # Each question is generated from its own answer unit.  The source recall
    # prompt is retained in the JSON as a reference, but is not allowed to
    # pull an unrelated topic into this block.
    if judgment_type == "calculation":
        formula = answer.split("=", 1)[0].strip() if "=" in answer else ""
        result_match = re.search(
            r"=\s*(?:[△▲]\s*)?(?P<label>[가-힣A-Za-z][가-힣A-Za-z·\s]{0,24}?)"
            r"\s+(?=[\d,]+(?:\.\d+)?)",
            answer,
        )
        result_name = "세무상 금액"
        if result_match:
            result_name = re.sub(r"\s+", " ", result_match.group("label")).strip()
            result_name = re.sub(r"(?:이다|이다\.)$", "", result_name).strip()
        if result_name == "세무상 금액":
            result_name = next(
                (
                    term
                    for term in ("과세표준", "과세소득", "불공제액", "손금불산입", "세액", "손금", "소득금액")
                    if term in answer
                ),
                result_name,
            )
        if result_name == "세무상 금액":
            fallback_match = re.search(
                r"=\s*(?:[△▲]\s*)?([가-힣A-Za-z][가-힣A-Za-z·\s]{0,24}?)\s+[\d,]+",
                answer,
            )
            if fallback_match:
                result_name = re.sub(r"\s+", " ", fallback_match.group(1)).strip()
        if result_name.endswith("금액") and "합계" in answer:
            result_name = f"{result_name} 합계"
        if "익금산입" in answer and "유보" in answer and "상여" in answer:
            question = f"{with_object_particle(formula or '익금산입')} 유보와 상여로 어떻게 나누는가?"
        else:
            result_topic = f"{result_name}{topic_particle(result_name)}"
            if formula:
                question = f"{with_object_particle(formula)} 계산하면 {result_topic} 얼마인가?"
            else:
                subject = format_focus_terms(focus) or "이 거래"
                question = f"{with_object_particle(subject)} 적용하면 {result_topic} 얼마인가?"
    elif judgment_type == "evidence":
        question = make_evidence_question_from_answer(answer, evidence)
    elif judgment_type == "change":
        question = make_change_question_from_answer(answer)
    else:
        question = make_rule_question_from_answer(answer)

    # Keep a concrete lexical link even when a source sentence ends in a
    # particle that the regex cannot share.  This is a final safety net, not
    # the normal path for any of the four unit types above.
    shared = question_answer_tokens(question) & question_answer_tokens(answer)
    if len(shared) < 2:
        anchors = concrete_answer_tokens(answer)
        focus = focus or ["해당 쟁점", "판단"]
        subject = "·".join(anchors[:3]) if anchors else format_focus_terms(focus)
        if judgment_type == "calculation":
            question = f"{with_object_particle(subject)} 계산하면 세무상 금액은 얼마인가?"
        elif judgment_type == "evidence":
            question = f"{subject} 등 자료는 사실관계의 어느 부분을 입증하는가?"
        elif judgment_type == "change":
            question = f"{subject} 조건이 바뀌면 결론은 어떻게 달라지는가?"
        else:
            question = f"{subject}의 판단 기준은 무엇인가?"
    return clean_question_text(question)


def extract_calculation_claims(reasoning: list[str]) -> list[str]:
    """Keep concrete formula/result sentences for a dedicated calculation unit."""
    # A date or a sentence that merely mentions a later adjustment is not a
    # calculation.  Require an explicit arithmetic operator so that the
    # calculation question really has a number to work out.
    markers = re.compile(r"=|×|÷")
    claims: list[str] = []
    for sentence in reasoning:
        if not markers.search(sentence):
            continue
        if sentence in {"관련 자료를 순서대로 대조한다."}:
            continue
        if sentence not in claims:
            claims.append(sentence)
    return claims


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
    """Build case-first blocks where every prompt and answer share one unit.

    The source lesson has three labelled answer anchors (rule, evidence and
    changed facts), and often a concrete calculation in the expert reasoning.
    We turn those anchors into small judgment units first, then write each
    question from the same unit.  This avoids the old index-based pairing in
    which a broad question was followed by an unrelated sentence.
    """
    case_facts = extract_case_facts(document)

    rules = [
        clean_learner_copy(item.get("rule_summary"))
        for item in law_map
        if isinstance(item, dict) and clean_learner_copy(item.get("rule_summary"))
    ]
    if not rules:
        rules = [f"{law_name}의 해당 조문에서 요건과 효과를 확인한다."]

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
    recall_by_type = extract_recall_questions_by_type(document)
    core_units = extract_answer_core_units(document)
    calculation_claims = extract_calculation_claims(reasoning)

    units: list[dict[str, str]] = []
    if calculation_claims:
        units.append(
            {
                "judgment_type": "calculation",
                "answer": clean_learner_copy(" ".join(calculation_claims[:2])),
                "source_label": "전문가 판단 과정",
            }
        )
    for item in core_units:
        unit = {
            "judgment_type": item["judgment_type"],
            "answer": clean_learner_copy(item["answer"]),
            "source_label": item["label"],
        }
        if unit["answer"] and unit["answer"] not in {existing["answer"] for existing in units}:
            units.append(unit)

    # A few older lessons do not have labelled answer anchors.  Use their
    # concrete reasoning sentences as a fallback, still keeping one sentence
    # per unit rather than distributing them by list index.
    if len(units) < 2:
        for sentence in reasoning:
            answer = clean_learner_copy(sentence)
            if not answer or answer in {unit["answer"] for unit in units}:
                continue
            units.append(
                {
                    "judgment_type": "change" if any(word in answer for word in ("조건", "추인", "다음", "바뀌")) else "rule",
                    "answer": answer,
                    "source_label": "전문가 판단 과정",
                }
            )
            if len(units) >= 2:
                break
    if len(units) < 2:
        units.append(
            {
                "judgment_type": "rule",
                "answer": rules[0],
                "source_label": "법령 요약",
            }
        )
    units = units[:4]

    blocks: list[dict[str, Any]] = []
    for index, unit in enumerate(units):
        judgment_type = unit["judgment_type"]
        recall_question = "" if judgment_type == "calculation" else recall_by_type.get(judgment_type, "")
        question = make_question_from_unit(unit, recall_question, evidence)

        if judgment_type == "calculation":
            fact_scope = "사실관계 중 금액·기간·산식"
        elif judgment_type == "evidence":
            fact_scope = "사실관계 중 결론을 입증하는 자료"
        elif judgment_type == "change":
            fact_scope = "사실관계에서 결론을 바꾸는 조건"
        else:
            fact_scope = "사실관계 중 법적 요건과 예외"

        step_article_ids: list[str] = []
        legal_refs: list[str] = []
        if article_ids:
            article_id = article_ids[index % len(article_ids)]
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
            if judgment_type == "evidence":
                step_evidence = evidence[:]
            elif index < len(evidence):
                step_evidence = [evidence[index]]

        accounting_note: str | None = None
        if accounting_item and (judgment_type == "calculation" or index == len(units) - 1):
            parts = [
                accounting_item.get("accounting_treatment"),
                accounting_item.get("reconciliation"),
                accounting_item.get("tax_adjustment"),
            ]
            parts = [clean_learner_copy(part) for part in parts if clean_learner_copy(part)]
            if parts:
                accounting_note = " ".join(parts)

        explanation = easy[index % len(easy)] if easy else legal_refs[0]
        blocks.append(
            {
                "block_no": index + 1,
                "judgment_type": judgment_type,
                "question": question,
                "fact_scope": fact_scope,
                "legal_refs": legal_refs,
                "article_ids": step_article_ids,
                "answer": unit["answer"] or legal_refs[0],
                "explanation": clean_learner_copy(explanation),
                "evidence": step_evidence,
                "precedent_refs": precedent_refs if index == len(units) - 1 else [],
                "accounting_note": accounting_note,
            }
        )

    transfer = clean_learner_copy(extract_heading_text(document, "변형사례"))
    concept = clean_learner_copy(
        topic.get("concept_key") or topic.get("canonical_title") or law_name
    )
    rule_chain = " → ".join(rule.rstrip(". ") for rule in rules[:3])
    summary_answer = next(
        (block["answer"] for block in reversed(blocks) if block.get("answer")),
        rules[-1],
    )
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
