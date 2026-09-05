import Link from "next/link";
import { ExternalLink, FileCheck2, FileText, Gavel, SearchCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { getArticle, getPrecedent } from "@/lib/content";
import type { Article, Issue, Precedent, QuestionBlock } from "@/types/content";

const judgmentLabels: Record<string, string> = {
  rule: "규칙 적용",
  calculation: "계산",
  evidence: "증거 확인",
  change: "조건 변경",
};

const levelLabels: Record<string, string> = {
  beginner: "기초",
  intermediate: "중급",
  advanced: "심화",
};

function textValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function textList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.length > 0) : [];
}

function safeOfficialUrl(value: string): string | null {
  try {
    const url = new URL(value);
    const allowedHosts = new Set(["law.go.kr", "www.law.go.kr", "scourt.go.kr", "www.scourt.go.kr"]);
    return allowedHosts.has(url.hostname) ? url.toString() : null;
  } catch {
    return null;
  }
}

function OfficialLink({ href, children }: { href: string; children: string }) {
  const safeHref = safeOfficialUrl(href);
  if (!safeHref) return null;
  return (
    <a
      className="inline-flex min-h-10 items-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 text-sm font-semibold text-primary hover:bg-muted"
      href={safeHref}
      target="_blank"
      rel="noreferrer"
    >
      {children}
      <ExternalLink aria-hidden="true" className="size-3.5" />
    </a>
  );
}

function ArticleCard({ articleId }: { articleId: string }) {
  const article = getArticle(articleId);
  if (!article) return null;
  const version = article.versions[0];
  if (!version) return null;

  return (
    <Card className="overflow-hidden">
      <CardHeader className="gap-3 border-b border-border bg-muted/40 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="outline">{article.article_number}</Badge>
            <span>{article.law_code}</span>
            <span aria-hidden="true">·</span>
            <span>{version.status === "current" ? "현행 확인본" : version.status}</span>
          </div>
          <CardTitle className="mt-2 text-lg">{article.title}</CardTitle>
        </div>
        <OfficialLink href={article.official_url}>법령 원문 열기</OfficialLink>
      </CardHeader>
      <CardContent className="space-y-4 pt-5">
        <p className="text-sm text-muted-foreground">
          시행일 {version.effective_date} · 확인일 {version.checked_at}
        </p>
        <div className="rounded-md border border-border bg-background p-4 text-[0.98rem] leading-8 whitespace-pre-wrap">
          {version.text}
        </div>
      </CardContent>
    </Card>
  );
}

function QuestionBlockCard({ block }: { block: QuestionBlock }) {
  return (
    <article id={`question-${block.block_no}`} className="border-t border-border py-7 first:border-t-0 first:pt-2">
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <Badge variant="secondary">질문 {block.block_no}</Badge>
        <span>{judgmentLabels[block.judgment_type] ?? block.judgment_type}</span>
      </div>
      <h3 className="mt-3 text-xl font-semibold leading-snug">{block.question}</h3>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">답</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{block.answer}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">왜 이렇게 판단하나</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{block.explanation}</p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid gap-5 border-l-2 border-primary/30 pl-4 lg:grid-cols-2">
        <div>
          <h4 className="font-semibold">연결 법령</h4>
          <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
            {block.legal_refs.map((reference) => (
              <li key={reference}>{reference}</li>
            ))}
          </ul>
        </div>
        {block.evidence.length > 0 && (
          <div>
            <h4 className="font-semibold">확인할 자료</h4>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {block.evidence.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {block.accounting_note && (
        <div className="mt-5 rounded-md bg-muted/60 p-4 text-sm">
          <p className="font-semibold">회계·세무조정 메모</p>
          <p className="mt-1 text-muted-foreground">{block.accounting_note}</p>
        </div>
      )}
    </article>
  );
}

function AuditCard({ item }: { item: Record<string, unknown> }) {
  const evidence = textList(item.evidence_to_check);
  return (
    <Card>
      <CardHeader className="flex-row items-center gap-3">
        <SearchCheck aria-hidden="true" className="size-5 text-secondary" />
        <CardTitle className="text-base">조사 가설과 반대 가설</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div>
          <p className="font-semibold">과세 가설</p>
          <p className="mt-1 text-muted-foreground">{textValue(item.audit_hypothesis)}</p>
        </div>
        <div>
          <p className="font-semibold">반대 가설</p>
          <p className="mt-1 text-muted-foreground">{textValue(item.counter_hypothesis)}</p>
        </div>
        {evidence.length > 0 && (
          <div>
            <p className="font-semibold">먼저 확보할 증거</p>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-muted-foreground">
              {evidence.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AccountingCard({ item }: { item: Record<string, unknown> }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center gap-3">
        <FileCheck2 aria-hidden="true" className="size-5 text-primary" />
        <CardTitle className="text-base">회계·세무조정 연결</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div>
          <p className="font-semibold">회계 처리</p>
          <p className="mt-1 text-muted-foreground">{textValue(item.accounting_treatment)}</p>
        </div>
        <div>
          <p className="font-semibold">신고서 대사</p>
          <p className="mt-1 text-muted-foreground">{textValue(item.reconciliation)}</p>
        </div>
        <div>
          <p className="font-semibold">세무조정</p>
          <p className="mt-1 text-muted-foreground">{textValue(item.tax_adjustment)}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function PrecedentCard({ precedent }: { precedent: Precedent }) {
  return (
    <Card>
      <CardHeader className="gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="outline">{precedent.court}</Badge>
            <span>{precedent.case_number}</span>
            <span aria-hidden="true">·</span>
            <span>{precedent.decision_date}</span>
          </div>
          <CardTitle className="mt-2 text-lg">{precedent.title ?? "판결문에서 확인할 쟁점"}</CardTitle>
        </div>
        <OfficialLink href={precedent.official_source_url}>공식 판결문</OfficialLink>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {precedent.issue_summary && (
          <div>
            <p className="font-semibold">쟁점</p>
            <p className="mt-1 text-muted-foreground">{precedent.issue_summary}</p>
          </div>
        )}
        {precedent.holding_summary && (
          <div>
            <p className="font-semibold">판단 요지</p>
            <p className="mt-1 text-muted-foreground">{precedent.holding_summary}</p>
          </div>
        )}
        {precedent.significance && (
          <div>
            <p className="font-semibold">이 쟁점에서의 의미</p>
            <p className="mt-1 text-muted-foreground">{precedent.significance}</p>
          </div>
        )}
        {precedent.distinguishing_facts.length > 0 && (
          <div>
            <p className="font-semibold">구별할 사실</p>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-muted-foreground">
              {precedent.distinguishing_facts.map((fact) => (
                <li key={fact}>{fact}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ArticleReferences({ issue }: { issue: Issue }) {
  return (
    <section aria-labelledby="articles-title" className="mt-12 scroll-mt-6">
      <div className="flex items-start gap-3">
        <FileText aria-hidden="true" className="mt-1 size-5 text-primary" />
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-secondary">근거 확인</p>
          <h2 id="articles-title" className="mt-1 text-2xl font-semibold tracking-tight">관련 법령 원문</h2>
          <p className="mt-2 text-muted-foreground">앞에서 판단한 질문에 연결된 조문만 순서대로 확인합니다.</p>
        </div>
      </div>
      <div className="mt-6 space-y-4">
        {issue.article_ids.map((articleId) => (
          <ArticleCard key={articleId} articleId={articleId} />
        ))}
      </div>
    </section>
  );
}

export function IssueReader({ issue, previousIssue, nextIssue }: { issue: Issue; previousIssue?: Issue; nextIssue?: Issue }) {
  const auditItems = issue.audit_application;
  const accountingItems = issue.accounting_tax_adjustment;
  const precedents = issue.precedent_ids.map((id) => getPrecedent(id)).filter((item): item is Precedent => Boolean(item));

  return (
    <>
      <header className="border-b border-border bg-card/80">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link className="font-semibold tracking-tight" href="/">
            세법 쟁점 아틀라스
          </Link>
          <Link className="text-sm font-semibold text-primary hover:underline" href="/#issues">
            전체 쟁점
          </Link>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-4xl px-4 pb-20 pt-8 sm:px-6 lg:pt-12">
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <Link className="hover:text-primary hover:underline" href="/">
            홈
          </Link>
          <span aria-hidden="true">/</span>
          <span>{issue.law_name}</span>
          <span aria-hidden="true">/</span>
          <span>{issue.position}번째 쟁점</span>
        </div>

        <header className="mt-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{issue.law_name}</Badge>
            <Badge variant="outline">{levelLabels[issue.level] ?? issue.level}</Badge>
            <span className="text-sm text-muted-foreground">약 {issue.estimated_minutes}분</span>
          </div>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-5xl sm:leading-tight">{issue.title}</h1>
        </header>

        <section aria-labelledby="facts-title" className="mt-10 rounded-md border-2 border-primary/25 bg-card p-5 sm:p-7">
          <div className="flex items-center gap-3">
            <Gavel aria-hidden="true" className="size-5 text-primary" />
            <h2 id="facts-title" className="text-xl font-semibold">사실관계 전문</h2>
          </div>
          <p className="mt-4 text-lg leading-8">{issue.case_facts}</p>
        </section>

        <section aria-labelledby="core-question-title" className="mt-8">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-secondary">이 사례의 중심</p>
          <h2 id="core-question-title" className="mt-1 text-2xl font-semibold tracking-tight">무엇을 판단해야 하나</h2>
          <p className="mt-3 text-lg leading-8 text-muted-foreground">{issue.core_question}</p>
        </section>

        <section aria-labelledby="questions-title" className="mt-12 scroll-mt-6">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-secondary">판단의 흐름</p>
              <h2 id="questions-title" className="mt-1 text-2xl font-semibold tracking-tight">질문별 판단</h2>
            </div>
            <span className="text-sm text-muted-foreground">{issue.question_blocks.length}단계</span>
          </div>
          <div className="mt-5 rounded-md border border-border bg-card px-4 sm:px-6">
            {issue.question_blocks.map((block) => (
              <QuestionBlockCard key={block.block_no} block={block} />
            ))}
          </div>
        </section>

        <ArticleReferences issue={issue} />

        {auditItems.length > 0 && (
          <section aria-labelledby="audit-title" className="mt-12 scroll-mt-6">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-secondary">현장 연결</p>
            <h2 id="audit-title" className="mt-1 text-2xl font-semibold tracking-tight">세무조사에 적용하기</h2>
            <p className="mt-2 text-muted-foreground">같은 규칙을 조사 자료와 반대 가설에 대입해 결론을 검증합니다.</p>
            <div className="mt-5 grid gap-4">
              {auditItems.map((item, index) => (
                <AuditCard key={index} item={item} />
              ))}
            </div>
          </section>
        )}

        {accountingItems.length > 0 && (
          <section aria-labelledby="accounting-title" className="mt-12 scroll-mt-6">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-secondary">실무 연결</p>
            <h2 id="accounting-title" className="mt-1 text-2xl font-semibold tracking-tight">회계·세무조정으로 옮기기</h2>
            <div className="mt-5 grid gap-4">
              {accountingItems.map((item, index) => (
                <AccountingCard key={index} item={item} />
              ))}
            </div>
          </section>
        )}

        {precedents.length > 0 && (
          <section aria-labelledby="precedents-title" className="mt-12 scroll-mt-6">
            <div className="flex items-start gap-3">
              <FileText aria-hidden="true" className="mt-1 size-5 text-primary" />
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-secondary">판단의 경계</p>
                <h2 id="precedents-title" className="mt-1 text-2xl font-semibold tracking-tight">관련 판례</h2>
                <p className="mt-2 text-muted-foreground">이 사실관계와 결론을 비교할 때 기준이 되는 판결입니다.</p>
              </div>
            </div>
            <div className="mt-5 grid gap-4">
              {precedents.map((precedent) => (
                <PrecedentCard key={precedent.precedent_id} precedent={precedent} />
              ))}
            </div>
          </section>
        )}

        {issue.transfer_case && (
          <section aria-labelledby="transfer-title" className="mt-12 rounded-md border border-secondary/30 bg-secondary/5 p-5 sm:p-7">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-secondary">결론의 조건</p>
            <h2 id="transfer-title" className="mt-1 text-2xl font-semibold tracking-tight">조건이 달라지면</h2>
            <p className="mt-4 leading-8">{issue.transfer_case}</p>
          </section>
        )}

        <section aria-labelledby="summary-title" className="mt-12 rounded-md bg-primary p-5 text-primary-foreground sm:p-7">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-primary-foreground/75">마지막 정리</p>
          <h2 id="summary-title" className="mt-1 text-2xl font-semibold tracking-tight">한 문장으로 답하기</h2>
          <p className="mt-4 leading-8">{issue.final_summary}</p>
          {issue.recall_questions.length > 0 && (
            <div className="mt-6 border-t border-primary-foreground/25 pt-5">
              <p className="font-semibold">다시 떠올릴 질문</p>
              <ul className="mt-2 list-disc space-y-2 pl-5 text-primary-foreground/85">
                {issue.recall_questions.map((question) => (
                  <li key={question}>{question}</li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <Separator className="my-10" />
        <nav aria-label="쟁점 이동" className="grid gap-3 sm:grid-cols-2">
          {previousIssue ? (
            <Link className="rounded-md border border-border bg-card p-4 hover:bg-muted" href={`/issues/${previousIssue.issue_id}/`}>
              <span className="block text-sm text-muted-foreground">이전 쟁점</span>
              <span className="mt-1 block font-semibold">{previousIssue.title}</span>
            </Link>
          ) : (
            <span />
          )}
          {nextIssue ? (
            <Link className="rounded-md border border-border bg-card p-4 text-left hover:bg-muted sm:text-right" href={`/issues/${nextIssue.issue_id}/`}>
              <span className="block text-sm text-muted-foreground">다음 쟁점</span>
              <span className="mt-1 block font-semibold">{nextIssue.title}</span>
            </Link>
          ) : null}
        </nav>
      </main>
    </>
  );
}
