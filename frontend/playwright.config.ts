import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const backendPort = 8100;
const frontendPort = 5178;
const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const databasePath = path.join(process.env.TEMP ?? ".", "pipelinepilot-playwright.sqlite3");
const uvCommand = process.env.PIPELINEPILOT_UV ?? "uv";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: [
    {
      command: `"${uvCommand}" run uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: path.join(frontendRoot, "..", "backend"),
      url: `http://127.0.0.1:${backendPort}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { ...process.env, PIPELINEPILOT_DATABASE_PATH: databasePath },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      cwd: frontendRoot,
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { ...process.env, PIPELINEPILOT_API_URL: `http://127.0.0.1:${backendPort}` },
    },
  ],
});
