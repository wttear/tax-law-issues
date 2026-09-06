import Link from "next/link";
import { ArrowDown, BookOpen, Scale } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { IssueBrowser } from "@/components/issue-browser";
import { IssueRow } from "@/components/issue-row";
import { getCatalog } from "@/lib/content";

export default function HomePage() {
  const { laws, issues } = getCatalog();
  const issuesByLaw = new Map<string, typeof issues>();
  for (const law of laws) issuesByLaw.set(law.law_code, issues.filter((issue) => issue.law_code === law.law_code));

  return (
    <>
      <header className="border-b border-border bg-card/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <Link className="font-semibold tracking-tight" href="/">
            세법 쟁점 아틀라스
          </Link>
          <nav aria-label="주요 메뉴" className="flex items-center gap-1 text-sm">
            <Link className="rounded-md px-3 py-2 text-muted-foreground hover:bg-muted hover:text-foreground" href="#laws">
              법령
            </Link>
            <Link className="rounded-md px-3 py-2 text-muted-foreground hover:bg-muted hover:text-foreground" href="#issues">
              쟁점
            </Link>
          </nav>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-6xl px-4 pb-20 pt-8 sm:px-6 lg:px-8 lg:pt-14">
        <section className="grid gap-8 border-b border-border pb-12 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
          <div>
            <Badge variant="outline">국세 {laws.length}개 법령 · {issues.length}개 쟁점</Badge>
            <h1 className="mt-5 max-w-3xl text-3xl font-semibold tracking-tight sm:text-5xl sm:leading-[1.12]">
              법령을 읽고, 쟁점을 판단하고,
              <br className="hidden sm:block" /> 실제 조사에 적용합니다.
            </h1>
            <p className="mt-5 max-w-2xl text-lg text-muted-foreground">
              하나의 사실관계를 중심으로 관련 조문, 질문별 답, 판례와 세무조사 증거를 한 흐름으로 연결해 읽습니다.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link className="inline-flex min-h-11 items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90" href="#issues">
                쟁점 고르기
                <ArrowDown aria-hidden="true" className="size-4" />
              </Link>
              <Link className="inline-flex min-h-11 items-center gap-2 rounded-md border border-border bg-card px-4 py-2 text-sm font-semibold hover:bg-muted" href="#laws">
                법령부터 보기
              </Link>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <Card>
              <CardHeader className="flex-row items-center gap-3">
                <BookOpen aria-hidden="true" className="size-5 text-primary" />
                <CardTitle className="text-base">읽는 순서</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">사실관계 전문 → 질문별 판단 → 법령·판례 → 조사·회계 연결</CardContent>
            </Card>
            <Card>
              <CardHeader className="flex-row items-center gap-3">
                <Scale aria-hidden="true" className="size-5 text-secondary" />
                <CardTitle className="text-base">현재 범위</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">국세기본법·국세징수법·법인세법·소득세법·부가가치세법</CardContent>
            </Card>
          </div>
        </section>

        <section id="laws" aria-labelledby="law-directory-title" className="scroll-mt-6 pt-10">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-secondary">법령별 쟁점</p>
              <h2 id="law-directory-title" className="mt-1 text-2xl font-semibold tracking-tight">먼저 법령을 고르세요</h2>
            </div>
            <span className="text-sm text-muted-foreground">법령별 실제 개수</span>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {laws.map((law) => (
              <a key={law.law_code} className="rounded-md border border-border bg-card p-4 transition-colors hover:border-primary hover:bg-muted" href={`#law-${law.law_code}`}>
                <span className="block text-sm text-muted-foreground">{law.law_code}</span>
                <span className="mt-1 block font-semibold">{law.law_name}</span>
                <span className="mt-3 block text-sm text-secondary">{law.issue_count}개 쟁점</span>
              </a>
            ))}
          </div>
        </section>

        <div id="issues" className="scroll-mt-6">
          <IssueBrowser laws={laws} issueCount={issues.length}>
            {laws.map((law) => (
              <section key={law.law_code} id={`law-${law.law_code}`} data-law-group className="mb-10 scroll-mt-6">
                <div className="mb-1 flex items-baseline justify-between gap-4">
                  <h3 className="text-xl font-semibold">{law.law_name}</h3>
                  <span className="text-sm text-muted-foreground">{law.issue_count}개</span>
                </div>
                {(issuesByLaw.get(law.law_code) ?? []).map((issue) => (
                  <IssueRow key={issue.issue_id} issue={issue} />
                ))}
              </section>
            ))}
          </IssueBrowser>
        </div>
      </main>

      <footer className="border-t border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-muted-foreground sm:px-6 lg:px-8">
          <p>세법 쟁점 아틀라스 · 학습용 정적 콘텐츠</p>
          <p>법령·판례 원문은 각 읽기 화면의 공식 출처 링크에서 확인하세요.</p>
        </div>
      </footer>
    </>
  );
}
