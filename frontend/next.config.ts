import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
      {
        source: "/api_root",
        destination: "http://127.0.0.1:8000/",
      },
    ];
  },
  // Increase timeout for long-running requests like video generation
  experimental: {
    proxyTimeout: 180000, // 3 minutes in milliseconds
  },
};

export default nextConfig;
