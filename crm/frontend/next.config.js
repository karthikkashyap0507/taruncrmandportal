/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/crm/:path*",
        destination: `${process.env.NEXT_PUBLIC_CRM_API_URL || "http://localhost:8001"}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
