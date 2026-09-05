import { notFound } from "next/navigation";
import { IssueReader } from "@/components/issue-reader";
import { getIssue, getIssues } from "@/lib/content";

export const dynamicParams = false;

export function generateStaticParams() {
  return getIssues().map((issue) => ({ issueId: issue.issue_id }));
}

export default async function IssuePage({ params }: { params: Promise<{ issueId: string }> }) {
  const { issueId } = await params;
  const issues = getIssues();
  const index = issues.findIndex((issue) => issue.issue_id === issueId);
  const issue = index >= 0 ? issues[index] : undefined;
  if (!issue) notFound();

  return <IssueReader issue={issue} previousIssue={issues[index - 1]} nextIssue={issues[index + 1]} />;
}
