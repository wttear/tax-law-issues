import Link from "next/link";
import { ExternalLink, FileText, Gavel } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { getArticle, getPrecedent } from "@/lib/content";
import type { Article, Issue, Precedent, QuestionBlock } from "@/types/content";

const levelLabels: Record<string, string> = {
  beginner: "기초",
  intermediate: "중급",
  advanced: "심화",
};

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
      <CardHeader className="gap-3 bg-muted/40 sm:flex-row sm:items-start sm:justify-between">
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
      <CardContent className="pt-0">
        <details className="border-t border-border pt-4">
          <summary className="cursor-pointer font-semibold text-sm">조문과 기준일 보기</summary>
          <p className="mt-4 text-sm text-muted-foreground">
            시행일 {version.effective_date} · 확인일 {version.checked_at}
          </p>
          <div className="mt-4 rounded-md border border-border bg-background p-4 text-[0.98rem] leading-8 whitespace-pre-wrap">
            {version.text}
          </div>
        </details>
      </CardContent>
    </Card>
  );
}

function QuestionBlockCard({ block }: { block: QuestionBlock }) {
  return (
    <article id={`question-${block.block_no}`} className="border-t border-border py-7 first:border-t-0 first:pt-2">
      <Badge variant="secondary">질문 {block.block_no}</Badge>
      <h3 className="mt-3 text-xl font-semibold leading-snug">{block.question}</h3>

      <div className="mt-5 rounded-md bg-muted/45 p-5">
        <p className="font-semibold">답</p>
        <p className="mt-2 text-lg leading-8">{block.answer}</p>
        <p className="mt-4 leading-8 text-muted-foreground">{block.explanation}</p>
      </div>

      {(block.legal_refs.length > 0 || block.evidence.length > 0 || block.practical_note) && (
        <div className="mt-5 grid gap-5 border-l-2 border-primary/30 pl-4 lg:grid-cols-2">
          {block.legal_refs.length > 0 && (
            <div>
          <h4 className="font-semibold">연결 법령</h4>
          <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
            {block.legal_refs.map((reference) => (
              <li key={reference}>{reference}</li>
            ))}
          </ul>
            </div>
          )}
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
          {block.practical_note && (
            <div className="lg:col-span-2">
              <h4 className="font-semibold">실무에서 볼 점</h4>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{block.practical_note}</p>
            </div>
          )}
        </div>
      )}

      {block.accounting_note && (
        <div className="mt-5 rounded-md bg-muted/60 p-4 text-sm">
          <p className="font-semibold">회계·세무조정 메모</p>
          <p className="mt-1 text-muted-foreground">{block.accounting_note}</p>
        </div>
      )}
    </article>
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
  if (issue.article_ids.length === 0) return null;
  return (
    <section aria-labelledby="articles-title" className="mt-12 scroll-mt-6">
      <div className="flex items-start gap-3">
        <FileText aria-hidden="true" className="mt-1 size-5 text-primary" />
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-secondary">근거 확인</p>
          <h2 id="articles-title" className="mt-1 text-2xl font-semibold tracking-tight">관련 법령</h2>
          <p className="mt-2 text-muted-foreground">본문에서 사용한 조문만 모았습니다. 원문은 필요할 때 펼쳐 보세요.</p>
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
  const precedents = issue.precedent_ids
    .map((id) => getPrecedent(id))
    .filter((item): item is Precedent => Boolean(item?.title && item.holding_summary));

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
        </div>

        <header className="mt-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{issue.law_name}</Badge>
            <Badge variant="outline">{levelLabels[issue.level] ?? issue.level}</Badge>
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

        <section aria-labelledby="questions-title" className="mt-10 scroll-mt-6">
          <h2 id="questions-title" className="sr-only">질문과 답</h2>
          <div className="mt-5 rounded-md border border-border bg-card px-4 sm:px-6">
            {issue.question_blocks.map((block) => (
              <QuestionBlockCard key={block.block_no} block={block} />
            ))}
          </div>
        </section>

        <ArticleReferences issue={issue} />

        {issue.practical_application && (
          <section aria-labelledby="practical-title" className="mt-12 rounded-md border border-secondary/30 bg-secondary/5 p-5 sm:p-7">
            <h2 id="practical-title" className="text-2xl font-semibold tracking-tight">{issue.practical_application.title}</h2>
            <p className="mt-3 leading-8">{issue.practical_application.introduction}</p>
            {issue.practical_application.steps.length > 0 && (
              <ol className="mt-5 list-decimal space-y-2 pl-5 leading-7 text-muted-foreground">
                {issue.practical_application.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            )}
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

        {issue.takeaway && (
          <section aria-labelledby="summary-title" className="mt-12 rounded-md bg-primary p-5 text-primary-foreground sm:p-7">
            <h2 id="summary-title" className="text-2xl font-semibold tracking-tight">핵심 정리</h2>
            <p className="mt-4 leading-8">{issue.takeaway}</p>
          </section>
        )}

        <Separator className="my-10" />
        <nav aria-label="쟁점 이동" className="space-y-3">
          <Link className="flex min-h-11 items-center justify-between rounded-md border border-border bg-card px-4 py-3 hover:bg-muted" href="/#issues">
            <span className="text-sm text-muted-foreground">다른 주제로 이동</span>
            <span className="font-semibold text-primary">전체 쟁점 목록으로</span>
          </Link>
          <div className="grid gap-3 sm:grid-cols-2">
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
          </div>
        </nav>
      </main>
    </>
  );
}
