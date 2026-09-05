import issuesSnapshot from "../content/issues.json";
import articlesSnapshot from "../content/articles.json";
import precedentsSnapshot from "../content/precedents.json";
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

const JUDGMENT_TYPES = new Set(["rule", "calculation", "evidence", "change"]);

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

function validateLaws(raw: unknown): Law[] {
  const laws = arrayValue(raw, "laws").map((item, index) => record(item, `laws[${index}]`)) as unknown as Law[];
  if (laws.length !== 5) fail("laws", "must contain five laws");
  const codes = new Set<string>();
  for (const [index, law] of laws.entries()) {
    stringValue(law.law_code, `laws[${index}].law_code`);
    stringValue(law.law_name, `laws[${index}].law_name`);
    if (codes.has(law.law_code)) fail(`laws[${index}].law_code`, "is duplicated");
    codes.add(law.law_code);
    if (law.issue_count !== 10) fail(`laws[${index}].issue_count`, "must be ten");
    const ids = stringArray(law.issue_ids, `laws[${index}].issue_ids`);
    if (ids.length !== 10) fail(`laws[${index}].issue_ids`, "must contain ten issues");
  }
  return laws;
}

function validateQuestionBlock(raw: unknown, path: string): QuestionBlock {
  const block = record(raw, path) as unknown as QuestionBlock;
  if (typeof block.block_no !== "number") fail(`${path}.block_no`, "must be a number");
  if (!JUDGMENT_TYPES.has(block.judgment_type)) fail(`${path}.judgment_type`, "is not supported");
  stringValue(block.question, `${path}.question`);
  stringValue(block.fact_scope, `${path}.fact_scope`);
  stringArray(block.legal_refs, `${path}.legal_refs`);
  stringArray(block.article_ids, `${path}.article_ids`);
  stringValue(block.answer, `${path}.answer`);
  stringValue(block.explanation, `${path}.explanation`);
  stringArray(block.evidence, `${path}.evidence`);
  stringArray(block.precedent_refs, `${path}.precedent_refs`);
  if (block.accounting_note !== null && typeof block.accounting_note !== "string") {
    fail(`${path}.accounting_note`, "must be a string or null");
  }
  return block;
}

function validateIssues(raw: unknown, laws: Law[], articleIds: Set<string>, precedentIds: Set<string>): Issue[] {
  const issues = arrayValue(raw, "issues").map((item, index) => record(item, `issues[${index}]`)) as unknown as Issue[];
  if (issues.length !== 50) fail("issues", "must contain fifty issues");
  const lawCounts = new Map<string, number>();
  const ids = new Set<string>();
  for (const [index, issue] of issues.entries()) {
    const path = `issues[${index}]`;
    stringValue(issue.issue_id, `${path}.issue_id`);
    if (ids.has(issue.issue_id)) fail(`${path}.issue_id`, "is duplicated");
    ids.add(issue.issue_id);
    stringValue(issue.law_code, `${path}.law_code`);
    if (!laws.some((law) => law.law_code === issue.law_code)) fail(`${path}.law_code`, "is unknown");
    lawCounts.set(issue.law_code, (lawCounts.get(issue.law_code) ?? 0) + 1);
    stringValue(issue.title, `${path}.title`);
    stringValue(issue.core_question, `${path}.core_question`);
    stringValue(issue.case_facts, `${path}.case_facts`);
    stringArray(issue.article_ids, `${path}.article_ids`).forEach((id) => {
      if (!articleIds.has(id)) fail(`${path}.article_ids`, `references missing article ${id}`);
    });
    stringArray(issue.precedent_ids, `${path}.precedent_ids`).forEach((id) => {
      if (!precedentIds.has(id)) fail(`${path}.precedent_ids`, `references missing precedent ${id}`);
    });
    const blocks = arrayValue(issue.question_blocks, `${path}.question_blocks`).map((block, blockIndex) =>
      validateQuestionBlock(block, `${path}.question_blocks[${blockIndex}]`),
    );
    if (blocks.length < 2) fail(`${path}.question_blocks`, "must contain at least two blocks");
    for (const block of blocks) {
      block.article_ids.forEach((id) => {
        if (!articleIds.has(id)) fail(`${path}.question_blocks`, `references missing article ${id}`);
      });
    }
  }
  for (const law of laws) {
    if (lawCounts.get(law.law_code) !== 10) fail(`law:${law.law_code}`, "must have ten issues");
    for (const issueId of law.issue_ids) if (!ids.has(issueId)) fail(`law:${law.law_code}`, `references missing issue ${issueId}`);
  }
  return issues;
}

const articles = (articlesSnapshot as ArticlesSnapshot).articles;
const precedents = (precedentsSnapshot as PrecedentsSnapshot).precedents;
const articleMap = new Map(articles.map((article) => [article.article_id, article]));
const precedentMap = new Map(precedents.map((precedent) => [precedent.precedent_id, precedent]));
const snapshot = issuesSnapshot as IssuesSnapshot;
const laws = validateLaws(snapshot.laws);
const issues = validateIssues(snapshot.issues, laws, new Set(articleMap.keys()), new Set(precedentMap.keys()));

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
