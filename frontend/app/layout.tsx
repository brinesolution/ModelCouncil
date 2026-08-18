import type { Metadata } from "next";
import Link from "next/link";

import { LedStatus } from "@/components/industrial/led-status";

import "./globals.css";

export const metadata: Metadata = {
  title: "ModelCouncil",
  description: "Synthetic consumer society and product opinion simulator",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="siteHeader">
          <Link className="brand" href="/" aria-label="ModelCouncil home">
            Model<span className="brandAccent">Council</span>
          </Link>
          <div className="navCluster">
            <nav className="nav" aria-label="Primary navigation">
              <Link href="/">Home</Link>
              <Link href="/simulate">Simulate</Link>
              <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
                API docs
              </a>
            </nav>
            <div className="headerStatus">
              <LedStatus label="Local mode" tone="red" compact />
            </div>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
