/** @type {import('next').NextConfig} */
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

const nextConfig = {
  // Proxy /api/* → FastAPI: use `app/api/[[...path]]/route.ts` (lê API_PROXY_URL em runtime).
  // Rewrites aqui só avaliam env no build — no Railway/Docker isso gerava 404 se a var fosse só runtime.
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
