/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the Backend Core API, e.g. http://localhost:8100/api/v1 */
  readonly VITE_BACKEND_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
