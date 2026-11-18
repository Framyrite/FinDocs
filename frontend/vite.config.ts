/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  server: {
    proxy: {
      // Браузер обращается к своему Vite-серверу по /api/… .
      // Vite передаёт запрос локальному FastAPI, поэтому CORS не требуется.
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,

        // У backend маршруты /documents, /chat/ask и /health без /api.
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },

  // Существующую конфигурацию тестов сохраняем.
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
