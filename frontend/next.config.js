/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  turbopack: { root: __dirname },
  outputFileTracingRoot: __dirname,
  experimental: { cpus: 2 },
  async rewrites() {
    const backend = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
    return [{ source: '/api/v1/:path*', destination: `${backend}/api/v1/:path*` }]
  },
}

module.exports = nextConfig
