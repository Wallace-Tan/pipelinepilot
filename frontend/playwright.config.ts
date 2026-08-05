import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const backendPort = 8100;
const frontendPort = 5178;
const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const databasePath = path.join(process.env.TEMP ?? ".", "pipelinepilot-playwright.sqlite3");
const uvCommand = process.env.PIPELINEPILOT_UV ?? "uv";
const recordVideo = process.env.PIPELINEPILOT_RECORD_VIDEO === "1";
const outputDir = process.env.PIPELINEPILOT_VIDEO_DIR ?? "test-results";
const externalRuntime = process.env.PIPELINEPILOT_EXTERNAL_SERVERS === "1";
const baseURL = process.env.PIPELINEPILOT_BASE_URL ?? `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: "./tests",
  outputDir,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    video: recordVideo ? "on" : "off",
    ...devices["Desktop Chrome"],
  },
  webServer: externalRuntime ? undefined : [
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
