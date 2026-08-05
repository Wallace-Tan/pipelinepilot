import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.PIPELINEPILOT_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/v1": apiTarget,
      "/health": apiTarget,
    },
  },
});
