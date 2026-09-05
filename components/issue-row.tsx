import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Issue } from "@/types/content";

const levelLabels: Record<string, string> = {
  beginner: "기초",
  intermediate: "중급",
  advanced: "심화",
};

export function IssueRow({ issue }: { issue: Issue }) {
  const searchable = [issue.title, issue.canonical_title, issue.core_question, issue.law_name].join(" ");

  return (
    <article
      className="issue-row grid gap-4 border-t border-border py-5 md:grid-cols-[1fr_auto] md:items-center"
      data-issue-row="true"
      data-law-code={issue.law_code}
      data-search={searchable}
    >
      <div className="min-w-0">
        <div className="mb-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <Badge variant="secondary">{issue.law_name}</Badge>
          <span>{levelLabels[issue.level] ?? issue.level}</span>
          <span aria-hidden="true">·</span>
          <span>{issue.estimated_minutes}분</span>
        </div>
        <h3 className="text-lg font-semibold leading-snug text-foreground">
          <Link className="underline decoration-transparent underline-offset-4 hover:decoration-current" href={`/issues/${issue.issue_id}/`}>
            {issue.title}
          </Link>
        </h3>
        <p className="mt-2 max-w-3xl text-[0.98rem] text-muted-foreground">{issue.core_question}</p>
      </div>
      <Link
        className={cn(buttonVariants({ variant: "outline", size: "sm" }), "w-full shrink-0 md:w-auto")}
        href={`/issues/${issue.issue_id}/`}
        aria-label={`${issue.title} 학습 열기`}
      >
        학습 열기
        <ArrowUpRight aria-hidden="true" className="size-4" />
      </Link>
    </article>
  );
}
