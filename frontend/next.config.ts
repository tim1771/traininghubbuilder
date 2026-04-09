import type { NextConfig } from "next";

// Railway backend URL in production, localhost for dev
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/media/:path*",
        destination: `${backendUrl}/media/:path*`,
      },
      {
        source: "/api_root",
        destination: `${backendUrl}/`,
      },
    ];
  },
  // Increase timeout for long-running requests like video generation
  experimental: {
    proxyTimeout: 600000, // 10 minutes in milliseconds
  },
};

export default nextConfig;
