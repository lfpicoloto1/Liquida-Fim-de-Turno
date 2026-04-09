import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

/**
 * Proxy em tempo de execução para o FastAPI.
 * Os `rewrites()` do next.config só usam env no *build*; no Docker/Railway a API_PROXY_URL
 * costuma existir só em runtime — daí 404 em /api/*. Este handler lê API_PROXY_URL a cada pedido.
 *
 * CORS: fetch com credentials a partir do Geraldo (origem diferente do front) precisa de
 * Access-Control-Allow-* + cookie de sessão SameSite=None no backend.
 *
 * Set-Cookie: usar getSetCookie() — forEach em Headers pode juntar mal vários Set-Cookie.
 */
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
]);

function backendOrigin(): string | null {
  const raw = process.env.API_PROXY_URL?.trim();
  if (raw) {
    const b = raw.replace(/\/$/, "");
    return /^https?:\/\//i.test(b) ? b : `https://${b}`;
  }
  if (process.env.NODE_ENV === "development") return "http://127.0.0.1:8000";
  return null;
}

function upstreamUrl(req: NextRequest, segments: string[]): string | null {
  const origin = backendOrigin();
  if (!origin) return null;
  const search = new URL(req.url).search;
  if (segments.length === 0) return `${origin}/api${search}`;
  return `${origin}/api/${segments.join("/")}${search}`;
}

function allowedCorsOrigins(): Set<string> {
  const raw =
    process.env.CORS_ALLOWED_ORIGINS?.trim() ||
    process.env.NEXT_PUBLIC_POSTMESSAGE_ORIGINS?.trim() ||
    "";
  return new Set(
    raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );
}

function corsHeadersForPreflight(req: NextRequest): Headers {
  const h = new Headers();
  const origin = req.headers.get("origin");
  if (origin && allowedCorsOrigins().has(origin)) {
    h.set("Access-Control-Allow-Origin", origin);
    h.set("Access-Control-Allow-Credentials", "true");
    h.set("Access-Control-Allow-Methods", "GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS");
    const reqHdrs = req.headers.get("access-control-request-headers");
    h.set(
      "Access-Control-Allow-Headers",
      reqHdrs ?? "Content-Type, Authorization, Cookie",
    );
    h.set("Access-Control-Max-Age", "86400");
    h.append("Vary", "Origin");
  }
  return h;
}

function applyCorsToResponse(req: NextRequest, res: NextResponse): NextResponse {
  const origin = req.headers.get("origin");
  if (origin && allowedCorsOrigins().has(origin)) {
    res.headers.set("Access-Control-Allow-Origin", origin);
    res.headers.set("Access-Control-Allow-Credentials", "true");
    res.headers.append("Vary", "Origin");
  }
  return res;
}

function forwardRequestHeaders(req: NextRequest): Headers {
  const out = new Headers();
  req.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (HOP_BY_HOP.has(k)) return;
    if (k === "host") return;
    if (k === "content-length") return;
    if (k.startsWith("x-middleware")) return;
    out.set(key, value);
  });
  return out;
}

function forwardResponseHeaders(res: Response): Headers {
  const out = new Headers();
  const setCookies =
    typeof res.headers.getSetCookie === "function" ? res.headers.getSetCookie() : null;
  if (setCookies && setCookies.length > 0) {
    for (const c of setCookies) {
      out.append("set-cookie", c);
    }
  }
  res.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (HOP_BY_HOP.has(k)) return;
    if (k === "set-cookie") return;
    out.set(key, value);
  });
  return out;
}

async function proxy(req: NextRequest, segments: string[]): Promise<NextResponse> {
  const target = upstreamUrl(req, segments);
  if (!target) {
    return applyCorsToResponse(
      req,
      NextResponse.json({ detail: "API_PROXY_URL não configurado" }, { status: 503 }),
    );
  }

  const init: RequestInit = {
    method: req.method,
    headers: forwardRequestHeaders(req),
    redirect: "manual",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    const buf = await req.arrayBuffer();
    if (buf.byteLength > 0) init.body = buf;
  }

  let res: Response;
  try {
    res = await fetch(target, init);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return applyCorsToResponse(
      req,
      NextResponse.json({ detail: `Falha ao contactar API: ${msg}` }, { status: 502 }),
    );
  }

  const out = new NextResponse(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: forwardResponseHeaders(res),
  });
  return applyCorsToResponse(req, out);
}

async function handle(req: NextRequest, ctx: { params: Promise<{ path?: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path ?? []);
}

export async function OPTIONS(req: NextRequest) {
  return new NextResponse(null, { status: 204, headers: corsHeadersForPreflight(req) });
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const HEAD = handle;
