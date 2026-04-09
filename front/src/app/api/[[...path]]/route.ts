import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

/**
 * Proxy em tempo de execução para o FastAPI.
 * Os `rewrites()` do next.config só usam env no *build*; no Docker/Railway a API_PROXY_URL
 * costuma existir só em runtime — daí 404 em /api/*. Este handler lê API_PROXY_URL a cada pedido.
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
  res.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (HOP_BY_HOP.has(k)) return;
    if (k === "set-cookie") out.append(key, value);
    else out.set(key, value);
  });
  return out;
}

async function proxy(req: NextRequest, segments: string[]): Promise<NextResponse> {
  const target = upstreamUrl(req, segments);
  if (!target) {
    return NextResponse.json({ detail: "API_PROXY_URL não configurado" }, { status: 503 });
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
    return NextResponse.json({ detail: `Falha ao contactar API: ${msg}` }, { status: 502 });
  }

  return new NextResponse(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: forwardResponseHeaders(res),
  });
}

async function handle(req: NextRequest, ctx: { params: Promise<{ path?: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path ?? []);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const HEAD = handle;
export const OPTIONS = handle;
