import type { Metadata } from "next";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Debug env (Liquida)",
  robots: { index: false, follow: false },
};

/**
 * Diagnóstico em produção: fora de `/api/*`, não passa pelo rewrite.
 * Abre: https://teu-front.up.railway.app/liquida-debug-env
 * Remove ou protege esta rota quando não precisares.
 */
export default function LiquidaDebugEnvPage() {
  const raw = process.env.API_PROXY_URL ?? "";
  const trimmed = String(raw).trim();
  let hostname: string | null = null;
  let parseError: string | null = null;
  try {
    if (trimmed) {
      const u = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
      hostname = new URL(u).hostname;
    }
  } catch {
    parseError = "URL inválida";
  }

  const payload = {
    NODE_ENV: process.env.NODE_ENV,
    API_PROXY_URL_defined: Boolean(trimmed),
    API_PROXY_URL_length: trimmed.length,
    API_PROXY_URL_hostname: hostname,
    API_PROXY_URL_parseError: parseError,
    note:
      "O tráfego /api/* vai para o FastAPI via app/api/[[...path]]/route.ts (runtime). Se defined for false, esse proxy devolve 503.",
  };

  return (
    <main style={{ padding: 24, fontFamily: "system-ui, sans-serif", maxWidth: 720 }}>
      <h1 style={{ fontSize: "1.25rem" }}>Liquida — debug de ambiente (Next servidor)</h1>
      <pre
        style={{
          marginTop: 16,
          padding: 16,
          background: "#111",
          color: "#e6e6e6",
          borderRadius: 8,
          overflow: "auto",
          fontSize: 13,
        }}
      >
        {JSON.stringify(payload, null, 2)}
      </pre>
      <p style={{ marginTop: 16, color: "#444", fontSize: 14 }}>
        Logs no browser: define <code>NEXT_PUBLIC_DEBUG_API=true</code> no serviço do <strong>front</strong> e
        vê a consola ao carregar a home (pedidos <code>/api/me</code>, etc.).
      </p>
    </main>
  );
}
