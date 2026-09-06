import issuesSnapshot from "../content/issues.json";
import articlesSnapshot from "../content/articles.json";
import precedentsSnapshot from "../content/precedents.json";
import learningNotesSnapshot from "../content/learning-notes.json";
import type {
  Article,
  ArticlesSnapshot,
  Issue,
  IssuesSnapshot,
  Law,
  Precedent,
  PrecedentsSnapshot,
  QuestionBlock,
} from "../types/content";

function fail(path: string, message: string): never {
  throw new Error(`Content validation failed: ${path} ${message}`);
}

function record(value: unknown, path: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(path, "must be an object");
  return value as Record<string, unknown>;
}

function stringValue(value: unknown, path: string): string {
  if (typeof value !== "string" || value.trim() === "") fail(path, "must be a non-empty string");
  return value;
}

function optionalString(value: unknown): string | null {
  return value == null ? null : typeof value === "string" ? value : null;
}

function arrayValue(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) fail(path, "must be an array");
  return value;
}

function stringArray(value: unknown, path: string): string[] {
  return arrayValue(value, path).map((item, index) => stringValue(item, `${path}[${index}]`));
}

function optionalStringArray(value: unknown, path: string): string[] {
  return value == null ? [] : stringArray(value, path);
}

function objectArray(value: unknown, path: string): Array<Record<string, unknown>> {
  return value == null ? [] : arrayValue(value, path).map((item, index) => record(item, `${path}[${index}]`));
}

export function mergeLearningNotes(rawSnapshot: unknown, rawLearningNotes: unknown): Record<string, unknown> {
  const snapshot = record(rawSnapshot, "snapshot");
  const baseIssues = arrayValue(snapshot.issues, "issues").map((issue, index) => record(issue, `issues[${index}]`));
  const learningNotes = record(rawLearningNotes, "learning_notes");
  const noteMap = new Map<string, Record<string, unknown>>();

  for (const [index, rawNote] of arrayValue(learningNotes.notes, "learning_notes.notes").entries()) {
    const note = record(rawNote, `learning_notes.notes[${index}]`);
    const issueId = stringValue(note.issue_id, `learning_notes.notes[${index}].issue_id`);
    if (noteMap.has(issueId)) fail(`learning_notes.notes[${index}].issue_id`, "is duplicated");
    noteMap.set(issueId, note);
  }

  const baseIds = new Set(baseIssues.map((issue, index) => stringValue(issue.issue_id, `issues[${index}].issue_id`)));
  for (const issueId of noteMap.keys()) if (!baseIds.has(issueId)) fail("learning_notes.notes", `references missing issue ${issueId}`);
  for (const issueId of baseIds) {
    if (!noteMap.has(issueId)) fail("learning_notes.notes", `is missing reviewed note ${issueId}`);
  }

  return {
    ...snapshot,
    issues: baseIssues.map((issue) => ({ ...issue, ...(noteMap.get(stringValue(issue.issue_id, "issue.issue_id")) ?? {}) })),
  };
}

function validateLaws(raw: unknown): Law[] {
  const laws = arrayValue(raw, "laws").map((item, index) => record(item, `laws[${index}]`)) as unknown as Law[];
  if (laws.length === 0) fail("laws", "must contain at least one law");
  const codes = new Set<string>();
  for (const [index, law] of laws.entries()) {
    stringValue(law.law_code, `laws[${index}].law_code`);
    stringValue(law.law_name, `laws[${index}].law_name`);
    if (codes.has(law.law_code)) fail(`laws[${index}].law_code`, "is duplicated");
    codes.add(law.law_code);
  }
  return laws;
}

function validateQuestionBlock(raw: unknown, path: string, fallbackNumber: number): QuestionBlock {
  const block = record(raw, path);
  const blockNo = block.block_no == null ? fallbackNumber : block.block_no;
  if (typeof blockNo !== "number") fail(`${path}.block_no`, "must be a number");
  const accountingNote = block.accounting_note ?? null;
  if (accountingNote !== null && typeof accountingNote !== "string") {
    fail(`${path}.accounting_note`, "must be a string or null");
  }
  const practicalNote = block.practical_note ?? null;
  if (practicalNote !== null && typeof practicalNote !== "string") fail(`${path}.practical_note`, "must be a string or null");
  return {
    block_no: blockNo,
    judgment_type: optionalString(block.judgment_type) ?? "direct",
    question: stringValue(block.question, `${path}.question`),
    fact_scope: optionalString(block.fact_scope) ?? "",
    legal_refs: optionalStringArray(block.legal_refs, `${path}.legal_refs`),
    article_ids: optionalStringArray(block.article_ids, `${path}.article_ids`),
    answer: stringValue(block.answer, `${path}.answer`),
    explanation: stringValue(block.explanation, `${path}.explanation`),
    evidence: optionalStringArray(block.evidence, `${path}.evidence`),
    precedent_refs: optionalStringArray(block.precedent_refs, `${path}.precedent_refs`),
    accounting_note: accountingNote,
    practical_note: practicalNote,
  };
}

function validateIssues(raw: unknown, laws: Law[], articleIds: Set<string>, precedentIds: Set<string>): Issue[] {
  const issues = arrayValue(raw, "issues").map((item, index) => record(item, `issues[${index}]`)) as unknown as Issue[];
  if (issues.length === 0) fail("issues", "must contain at least one issue");
  const ids = new Set<string>();
  const normalized: Issue[] = [];
  for (const [index, issue] of issues.entries()) {
    const path = `issues[${index}]`;
    stringValue(issue.issue_id, `${path}.issue_id`);
    if (ids.has(issue.issue_id)) fail(`${path}.issue_id`, "is duplicated");
    ids.add(issue.issue_id);
    stringValue(issue.law_code, `${path}.law_code`);
    if (!laws.some((law) => law.law_code === issue.law_code)) fail(`${path}.law_code`, "is unknown");
    const title = stringValue(issue.title, `${path}.title`);
    const articleIdsForIssue = optionalStringArray(issue.article_ids, `${path}.article_ids`);
    articleIdsForIssue.forEach((id) => {
      if (!articleIds.has(id)) fail(`${path}.article_ids`, `references missing article ${id}`);
    });
    const precedentIdsForIssue = optionalStringArray(issue.precedent_ids, `${path}.precedent_ids`);
    precedentIdsForIssue.forEach((id) => {
      if (!precedentIds.has(id)) fail(`${path}.precedent_ids`, `references missing precedent ${id}`);
    });
    const blocks = arrayValue(issue.question_blocks, `${path}.question_blocks`).map((block, blockIndex) =>
      validateQuestionBlock(block, `${path}.question_blocks[${blockIndex}]`, blockIndex + 1),
    );
    if (blocks.length === 0) fail(`${path}.question_blocks`, "must contain at least one direct question");
    for (const block of blocks) {
      block.article_ids.forEach((id) => {
        if (!articleIds.has(id)) fail(`${path}.question_blocks`, `references missing article ${id}`);
      });
    }
    const rawPracticalApplication = issue.practical_application;
    let practicalApplication: Issue["practical_application"] = null;
    if (rawPracticalApplication != null) {
      const application = record(rawPracticalApplication, `${path}.practical_application`);
      practicalApplication = {
        title: stringValue(application.title, `${path}.practical_application.title`),
        introduction: stringValue(application.introduction, `${path}.practical_application.introduction`),
        steps: stringArray(application.steps, `${path}.practical_application.steps`),
      };
    }
    normalized.push({
      issue_id: issue.issue_id,
      law_code: issue.law_code,
      law_name: stringValue(issue.law_name, `${path}.law_name`),
      position: typeof issue.position === "number" ? issue.position : index + 1,
      title,
      canonical_title: optionalString(issue.canonical_title) ?? title,
      level: optionalString(issue.level) ?? "beginner",
      core_question: stringValue(issue.core_question, `${path}.core_question`),
      easy_explanation: optionalString(issue.easy_explanation) ?? "",
      article_ids: articleIdsForIssue,
      law_map: objectArray(issue.law_map, `${path}.law_map`) as unknown as Issue["law_map"],
      related_references: objectArray(issue.related_references, `${path}.related_references`) as unknown as Issue["related_references"],
      audit_application: objectArray(issue.audit_application, `${path}.audit_application`),
      accounting_tax_adjustment: objectArray(issue.accounting_tax_adjustment, `${path}.accounting_tax_adjustment`),
      precedent_ids: precedentIdsForIssue,
      precedents: objectArray(issue.precedents, `${path}.precedents`),
      case_facts: stringValue(issue.case_facts, `${path}.case_facts`),
      question_blocks: blocks,
      transfer_case: optionalString(issue.transfer_case) ?? "",
      final_summary: optionalString(issue.final_summary) ?? "",
      recall_questions: optionalStringArray(issue.recall_questions, `${path}.recall_questions`),
      modules: record(issue.modules ?? {}, `${path}.modules`) as unknown as Issue["modules"],
      lesson_lead: optionalString(issue.lesson_lead) ?? "",
      estimated_minutes: typeof issue.estimated_minutes === "number" ? issue.estimated_minutes : 10,
      audience: optionalString(issue.audience) ?? "초급",
      material_metadata: record(issue.material_metadata ?? {}, `${path}.material_metadata`),
      practical_application: practicalApplication,
      takeaway: optionalString(issue.takeaway),
    });
  }
  return normalized;
}

const articles = (articlesSnapshot as ArticlesSnapshot).articles;
const precedents = (precedentsSnapshot as PrecedentsSnapshot).precedents;
const articleMap = new Map(articles.map((article) => [article.article_id, article]));
const precedentMap = new Map(precedents.map((precedent) => [precedent.precedent_id, precedent]));

export function validateContentSnapshot(rawSnapshot: unknown, rawArticles: unknown, rawPrecedents: unknown): IssuesSnapshot {
  const snapshot = record(rawSnapshot, "snapshot");
  const laws = validateLaws(snapshot.laws);
  const articleIds = new Set(arrayValue(rawArticles, "articles").map((article, index) => stringValue(record(article, `articles[${index}]`).article_id, `articles[${index}].article_id`)));
  const precedentIds = new Set(
    arrayValue(rawPrecedents, "precedents").map((precedent, index) =>
      stringValue(record(precedent, `precedents[${index}]`).precedent_id, `precedents[${index}].precedent_id`),
    ),
  );
  const issues = validateIssues(snapshot.issues, laws, articleIds, precedentIds);
  const normalizedLaws = laws.map((law) => {
    const lawIssues = issues.filter((issue) => issue.law_code === law.law_code);
    return { law_code: law.law_code, law_name: law.law_name, issue_count: lawIssues.length, issue_ids: lawIssues.map((issue) => issue.issue_id) };
  });
  return {
    schema_version: typeof snapshot.schema_version === "number" ? snapshot.schema_version : 1,
    generated_as_of: optionalString(snapshot.generated_as_of) ?? "",
    source_repository: optionalString(snapshot.source_repository) ?? "",
    laws: normalizedLaws,
    issues,
    article_count: articleIds.size,
    precedent_count: precedentIds.size,
  };
}

const snapshot = validateContentSnapshot(mergeLearningNotes(issuesSnapshot, learningNotesSnapshot), articles, precedents);
const laws = snapshot.laws;
const issues = snapshot.issues;

export function getCatalog(): { laws: Law[]; issues: Issue[] } {
  return { laws, issues };
}

export function getLaws(): Law[] {
  return laws;
}

export function getIssues(): Issue[] {
  return issues;
}

export function getIssue(issueId: string): Issue | undefined {
  return issues.find((issue) => issue.issue_id === issueId);
}

export function getArticle(articleId: string): Article | undefined {
  return articleMap.get(articleId);
}

export function getPrecedent(precedentId: string): Precedent | undefined {
  return precedentMap.get(precedentId);
}

export function getArticleText(articleId: string): string | null {
  const article = getArticle(articleId);
  const version = article?.versions[0];
  return version?.text ?? null;
}

export function getOptionalString(value: unknown): string | null {
  return optionalString(value);
}
