import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "StaleCheck — catch stale answers before users do",
  description:
    "Detect outdated, time-sensitive claims in AI answers and auto-refresh them before users see them.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="nav">
          <div className="brand">
            <span className="dot" />
            <Link href="/">StaleCheck</Link>
            <span className="tag">v0.1</span>
          </div>
          <nav>
            <Link href="/">Check</Link>
            <Link href="/runs/">Runs</Link>
            <span className="muted">Tavily challenge</span>
          </nav>
        </header>
        <main>{children}</main>
        <footer className="footer">
          API · Python SDK · CLI · JS SDK · Dashboard — built for the Global AI Hackathon
          (Tavily).
        </footer>
      </body>
    </html>
  );
}
