/** Origens permitidas para aceitar postMessage do callback Geraldo (browser). */
export function getTrustedPostMessageOrigins(): string[] {
  const raw =
    process.env.NEXT_PUBLIC_POSTMESSAGE_ORIGINS ??
    "https://geraldo-restaurantes.aiqfome.digital,http://localhost:3000";
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function isTrustedOrigin(origin: string): boolean {
  // Popup OAuth (callback em /auth/magalu/callback) envia de window.location.origin da app;
  // esse origin não costuma estar em NEXT_PUBLIC_POSTMESSAGE_ORIGINS (lista = Geraldo, dev).
  if (typeof window !== "undefined" && origin === window.location.origin) {
    return true;
  }
  return getTrustedPostMessageOrigins().includes(origin);
}
