// craco.config.js
const path = require("path");
require("dotenv").config();

// Environment variable overrides
const config = {
  disableHotReload: process.env.DISABLE_HOT_RELOAD === "true",
  enableHealthCheck: process.env.ENABLE_HEALTH_CHECK === "true",
};

// Conditionally load health check modules only if enabled
let WebpackHealthPlugin;
let setupHealthEndpoints;
let healthPluginInstance;

if (config.enableHealthCheck) {
  WebpackHealthPlugin = require("./plugins/health-check/webpack-health-plugin");
  setupHealthEndpoints = require("./plugins/health-check/health-endpoints");
  healthPluginInstance = new WebpackHealthPlugin();
}

const webpackConfig = {
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    configure: (webpackConfig) => {

      // Disable ESLint warnings/errors during build
      const eslintPlugin = webpackConfig.plugins.find(
        plugin => plugin.constructor.name === 'ESLintWebpackPlugin'
      );
      if (eslintPlugin) {
        eslintPlugin.options.failOnError = false;
        eslintPlugin.options.failOnWarning = false;
      }

      // ─── P2 Performance: Vendor chunk splitting (production only) ───
      const isProduction = webpackConfig.mode === 'production';
      if (isProduction) {
        webpackConfig.optimization = {
          ...webpackConfig.optimization,
          splitChunks: {
            chunks: 'all',
            maxInitialRequests: 10,
            minSize: 20000,
            cacheGroups: {
              reactVendor: {
                test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
                name: 'react-vendor',
                priority: 40,
                reuseExistingChunk: true,
              },
              uiVendor: {
                test: /[\\/]node_modules[\\/]@radix-ui[\\/]/,
                name: 'ui-vendor',
                priority: 30,
                reuseExistingChunk: true,
              },
              queryVendor: {
                test: /[\\/]node_modules[\\/]@tanstack[\\/]/,
                name: 'query-vendor',
                priority: 30,
                reuseExistingChunk: true,
              },
              chartsVendor: {
                test: /[\\/]node_modules[\\/](recharts|d3-[^/]+|victory-[^/]+)[\\/]/,
                name: 'charts-vendor',
                priority: 25,
                reuseExistingChunk: true,
              },
              defaultVendors: {
                test: /[\\/]node_modules[\\/]/,
                name: 'vendors',
                priority: 10,
                reuseExistingChunk: true,
              },
            },
          },
        };
      }

      // Disable hot reload completely if environment variable is set
      if (config.disableHotReload) {
        // Remove hot reload related plugins
        webpackConfig.plugins = webpackConfig.plugins.filter(plugin => {
          return !(plugin.constructor.name === 'HotModuleReplacementPlugin');
        });

        // Disable watch mode
        webpackConfig.watch = false;
        webpackConfig.watchOptions = {
          ignored: /.*/, // Ignore all files
        };
      } else {
        // Add ignored patterns to reduce watched directories
        webpackConfig.watchOptions = {
          ...webpackConfig.watchOptions,
          ignored: [
            '**/node_modules/**',
            '**/.git/**',
            '**/build/**',
            '**/dist/**',
            '**/coverage/**',
            '**/public/**',
          ],
        };
      }

      // Add health check plugin to webpack if enabled
      if (config.enableHealthCheck && healthPluginInstance) {
        webpackConfig.plugins.push(healthPluginInstance);
      }

      return webpackConfig;
    },
  },
};

// Setup dev server with health check
if (config.enableHealthCheck) {
  webpackConfig.devServer = (devServerConfig) => {
    if (setupHealthEndpoints && healthPluginInstance) {
      const originalSetupMiddlewares = devServerConfig.setupMiddlewares;

      devServerConfig.setupMiddlewares = (middlewares, devServer) => {
        if (originalSetupMiddlewares) {
          middlewares = originalSetupMiddlewares(middlewares, devServer);
        }
        setupHealthEndpoints(devServer, healthPluginInstance);
        return middlewares;
      };
    }

    devServerConfig.webSocketServer = false;
    devServerConfig.allowedHosts = "all";
    devServerConfig.host = "0.0.0.0";
    devServerConfig.proxy = {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    };

    return devServerConfig;
  };
} else {
  webpackConfig.devServer = (devServerConfig) => {
    devServerConfig.webSocketServer = false;
    devServerConfig.allowedHosts = "all";
    devServerConfig.host = "0.0.0.0";
    devServerConfig.proxy = {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    };
    return devServerConfig;
  };
}

module.exports = webpackConfig;
