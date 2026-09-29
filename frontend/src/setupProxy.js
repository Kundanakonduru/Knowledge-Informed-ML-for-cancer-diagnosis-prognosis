/**
 * Proxy only /api to backend. Other requests (favicon, hot-update) stay on dev server.
 * Prevents "Proxy error: ECONNREFUSED" when backend is down for non-API requests.
 */
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function (app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
    })
  );
};
