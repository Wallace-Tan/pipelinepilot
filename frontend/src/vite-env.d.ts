/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PIPELINEPILOT_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
