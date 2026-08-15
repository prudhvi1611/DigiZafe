/// <reference types="vite/client" />
declare module 'react-cytoscapejs';

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_APP_NAME: string;
  readonly VITE_SSE_USE_FETCH: string;
  readonly VITE_XPOSEDORNOT_ATTRIBUTION: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
