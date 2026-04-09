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
  return getTrustedPostMessageOrigins().includes(origin);
}
