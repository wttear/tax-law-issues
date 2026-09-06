export type JudgmentType = string;

export interface Law {
  law_code: string;
  law_name: string;
  issue_count: number;
  issue_ids: string[];
}

export interface QuestionBlock {
  block_no: number;
  judgment_type: JudgmentType;
  question: string;
  fact_scope: string;
  legal_refs: string[];
  article_ids: string[];
  answer: string;
  explanation: string;
  evidence: string[];
  precedent_refs: string[];
  accounting_note: string | null;
  practical_note?: string | null;
}

export interface IssueModules {
  audit: boolean;
  accounting: boolean;
  exam: boolean;
}

export interface PracticalApplication {
  title: string;
  introduction: string;
  steps: string[];
}

export interface RelatedReference {
  reference: string;
  law_name: string;
  official_url: string;
  text_status: string;
}

export interface Issue {
  issue_id: string;
  law_code: string;
  law_name: string;
  position: number;
  title: string;
  canonical_title: string;
  level: string;
  core_question: string;
  easy_explanation: string;
  article_ids: string[];
  law_map: Array<Record<string, string>>;
  related_references: RelatedReference[];
  audit_application: Array<Record<string, unknown>>;
  accounting_tax_adjustment: Array<Record<string, unknown>>;
  precedent_ids: string[];
  precedents: Array<Record<string, unknown>>;
  case_facts: string;
  question_blocks: QuestionBlock[];
  transfer_case: string;
  final_summary: string;
  recall_questions: string[];
  modules: IssueModules;
  lesson_lead: string;
  estimated_minutes: number;
  audience: string;
  material_metadata: Record<string, unknown>;
  practical_application?: PracticalApplication | null;
  takeaway?: string | null;
}

export interface ArticleVersion {
  version_id: string;
  official_url: string;
  effective_date: string;
  checked_at: string;
  source_sha256: string;
  status: string;
  text: string;
}

export interface Article {
  article_id: string;
  law_code: string;
  article_number: string;
  title: string;
  official_url: string;
  source_url: string;
  source_as_of: string;
  content_status: string;
  versions: ArticleVersion[];
}

export interface Precedent {
  precedent_id: string;
  case_number: string;
  decision_date: string;
  court: string;
  title: string | null;
  issue_summary: string | null;
  holding_summary: string | null;
  significance: string | null;
  distinguishing_facts: string[];
  disposition_summary: string | null;
  official_source_url: string;
  source_as_of: string | null;
  source_provenance: string[];
}

export interface IssuesSnapshot {
  schema_version: number;
  generated_as_of: string;
  source_repository: string;
  laws: Law[];
  issues: Issue[];
  article_count: number;
  precedent_count: number;
}

export interface ArticlesSnapshot {
  schema_version: number;
  generated_as_of: string;
  articles: Article[];
}

export interface PrecedentsSnapshot {
  schema_version: number;
  generated_as_of: string;
  precedents: Precedent[];
}
