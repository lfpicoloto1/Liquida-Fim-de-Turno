"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

/**
 * OAuth redirect do Magalu ID (teste local, sem iframe Geraldo).
 * Cadastre no Magalu a mesma URL que NEXT_PUBLIC_MAGALU_REDIRECT_URI, ex.:
 * http://localhost:3000/auth/magalu/callback
 */
function CallbackInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [message, setMessage] = useState("Concluindo login…");

  useEffect(() => {
    const err = searchParams.get("error");
    const code = searchParams.get("code");
    const oauthState = searchParams.get("state");
    const redirectUri = (process.env.NEXT_PUBLIC_MAGALU_REDIRECT_URI ?? "").trim();

    if (err) {
      setMessage(searchParams.get("error_description") ?? err);
      return;
    }
    if (!code) {
      setMessage("Resposta sem código de autorização.");
      return;
    }
    if (!redirectUri) {
      setMessage("Configure NEXT_PUBLIC_MAGALU_REDIRECT_URI (e MAGALU_REDIRECT_URI no servidor).");
      return;
    }

    let cancelled = false;
    (async () => {
      const res = await fetch("/api/auth/magalu/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          code,
          redirectUri,
          ...(oauthState ? { oauthState } : {}),
        }),
      });
      if (cancelled) return;
      if (!res.ok) {
        const j = (await res.json().catch(() => ({}))) as { error?: string; detail?: string };
        const msg =
          typeof j.detail === "string" ? j.detail : j.error ?? "Falha ao trocar o code pelo token.";
        setMessage(msg);
        return;
      }
      const targetOrigin = window.location.origin;
      if (window.opener && !window.opener.closed) {
        try {
          window.opener.postMessage({ type: "magaluAuthDone" }, targetOrigin);
        } catch {
          //
        }
        window.close();
        return;
      }
      router.replace("/");
    })();

    return () => {
      cancelled = true;
    };
  }, [searchParams, router]);

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1.5rem",
      }}
    >
      <p style={{ textAlign: "center", maxWidth: "28rem" }}>{message}</p>
    </main>
  );
}

export default function MagaluOAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p>Carregando…</p>
        </main>
      }
    >
      <CallbackInner />
    </Suspense>
  );
}
