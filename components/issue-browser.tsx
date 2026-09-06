"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { Law } from "@/types/content";

export function IssueBrowser({ laws, issueCount, children }: { laws: Law[]; issueCount: number; children: ReactNode }) {
  const listRef = useRef<HTMLDivElement>(null);
  const queryRef = useRef<HTMLInputElement>(null);
  const lawRef = useRef<HTMLSelectElement>(null);
  const [visibleCount, setVisibleCount] = useState(issueCount);

  const updateRows = useCallback(() => {
    const root = listRef.current;
    if (!root) return;
    const query = queryRef.current?.value.trim().toLocaleLowerCase("ko-KR") ?? "";
    const selectedLaw = lawRef.current?.value ?? "all";
    const rows = Array.from(root.querySelectorAll<HTMLElement>("[data-issue-row]"));
    let nextCount = 0;

    for (const row of rows) {
      const matchesQuery = !query || (row.dataset.search ?? "").toLocaleLowerCase("ko-KR").includes(query);
      const matchesLaw = selectedLaw === "all" || row.dataset.lawCode === selectedLaw;
      const visible = matchesQuery && matchesLaw;
      row.hidden = !visible;
      if (visible) nextCount += 1;
    }

    for (const group of Array.from(root.querySelectorAll<HTMLElement>("[data-law-group]"))) {
      group.hidden = group.querySelectorAll<HTMLElement>("[data-issue-row]:not([hidden])").length === 0;
    }
    setVisibleCount(nextCount);
  }, []);

  useEffect(() => {
    updateRows();
  }, [updateRows]);

  return (
    <section aria-labelledby="issue-browser-title" className="mt-12">
      <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-secondary">탐색</p>
          <h2 id="issue-browser-title" className="mt-1 text-2xl font-semibold tracking-tight">
            {issueCount}개 쟁점에서 골라 읽기
          </h2>
        </div>
        <p className="text-sm text-muted-foreground" aria-live="polite">
          전체 {visibleCount}개 표시
        </p>
      </div>

      <div className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-[minmax(0,1fr)_15rem]">
        <label className="block" htmlFor="issue-search">
          <span className="mb-2 block text-sm font-semibold">쟁점 검색</span>
          <span className="relative block">
            <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              ref={queryRef}
              id="issue-search"
              className="pl-10"
              type="search"
              placeholder="예: 손금, 납세의무, 세금계산서"
              onInput={updateRows}
            />
          </span>
        </label>
        <label className="block" htmlFor="law-filter">
          <span className="mb-2 block text-sm font-semibold">법령 필터</span>
          <Select ref={lawRef} id="law-filter" defaultValue="all" onChange={updateRows}>
            <option value="all">전체 법령</option>
            {laws.map((law) => (
              <option key={law.law_code} value={law.law_code}>
                {law.law_name}
              </option>
            ))}
          </Select>
        </label>
      </div>

      <div ref={listRef} className="mt-8">
        {children}
      </div>
    </section>
  );
}
