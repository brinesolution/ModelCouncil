import type { Metadata } from "next";
import Link from "next/link";

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
          <Link className="brand" href="/">
            ModelCouncil
          </Link>
          <nav className="nav" aria-label="Primary navigation">
            <Link href="/simulate">New simulation</Link>
            <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
              API docs
            </a>
          </nav>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
