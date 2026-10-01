import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    optimizePackageImports: ["lucide-react", "framer-motion"],
  },
  devIndicators: false,
  typescript: { ignoreBuildErrors: true },
};

export default nextConfig;
