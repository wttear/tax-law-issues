import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "세법 쟁점 아틀라스",
  description: "국세 5개 법령의 핵심 쟁점을 법령·판례·세무조사·회계 흐름으로 읽는 학습 사이트",
  other: {
    "atlas-contract": "THESIS: one issue, one connected reading path | FIRST VIEWPORT: orientation before source text | FINISH: summary and next issue",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <a
          href="#main-content"
          className="sr-only fixed left-3 top-3 z-50 rounded-md bg-primary px-4 py-3 font-semibold text-primary-foreground focus:not-sr-only"
        >
          본문으로 건너뛰기
        </a>
        {children}
      </body>
    </html>
  );
}
