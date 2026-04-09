import type { NextConfig } from "next";

const frameAncestors =
  process.env.ALLOWED_FRAME_ANCESTORS ??
  "'self' https://geraldo-restaurantes.aiqfome.digital";

const securityHeaders = [
  {
    key: "Content-Security-Policy",
    value: `frame-ancestors ${frameAncestors}`,
  },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
];

const apiProxyBase =
  process.env.API_PROXY_URL ??
  (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");

const nextConfig: NextConfig = {
  async rewrites() {
    if (!apiProxyBase) {
      return [];
    }
    const base = apiProxyBase.replace(/\/$/, "");
    return [{ source: "/api/:path*", destination: `${base}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
