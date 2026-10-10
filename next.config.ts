import path from "node:path";
import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.join(__dirname),
  },
  // Where some bots and older tools look for these two files.
  async redirects() {
    return [
      { source: "/security.txt", destination: "/.well-known/security.txt", permanent: true },
      { source: "/en/favicon.ico", destination: "/favicon.ico", permanent: true },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
