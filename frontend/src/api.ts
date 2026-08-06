const configuredApiUrl = import.meta.env.VITE_PIPELINEPILOT_API_URL?.trim() ?? "";
const defaultProductionApiUrl = "https://pipelinepilot-api.onrender.com";
const apiBaseUrl = (
  configuredApiUrl || (import.meta.env.DEV ? "" : defaultProductionApiUrl)
).replace(/\/+$/, "");

export function apiUrl(path: string): string {
  return `${apiBaseUrl}${path}`;
}
