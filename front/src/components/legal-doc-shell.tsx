import Link from "next/link";
import type { ReactNode } from "react";

type LegalDocShellProps = {
  title: string;
  lastUpdated?: string;
  children: ReactNode;
};

export function LegalDocShell({ title, lastUpdated, children }: LegalDocShellProps) {
  return (
    <main className="xepa-dashboard xepa-legal-page">
      <div className="xepa-legal-inner">
        <nav className="xepa-legal-back" aria-label="Navegação">
          <Link href="/">← Voltar ao app</Link>
        </nav>
        <article className="xepa-legal-doc">
          <header className="xepa-legal-doc-header">
            <h1>{title}</h1>
            {lastUpdated ? <p className="xepa-legal-doc-updated">Última atualização: {lastUpdated}</p> : null}
          </header>
          <div className="xepa-legal-doc-body">{children}</div>
        </article>
        <nav className="xepa-legal-cross" aria-label="Outros documentos">
          <Link href="/privacidade">Política de privacidade</Link>
          <span className="xepa-legal-cross-sep" aria-hidden>
            |
          </span>
          <Link href="/termos">Termos de uso</Link>
        </nav>
      </div>
    </main>
  );
}
