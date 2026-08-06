const configuredApiUrl = import.meta.env.VITE_PIPELINEPILOT_API_URL?.trim() ?? "";
const apiBaseUrl = configuredApiUrl.replace(/\/+$/, "");

export function apiUrl(path: string): string {
  return `${apiBaseUrl}${path}`;
}
