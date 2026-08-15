# DigiZafe — Sprint 9 Frontend Core  
**Complete Implementation Guide from Sprint 8 Baseline + All File Contents**

**Document version:** 1.0  
**Based on:** MASTER_ENGINEERING_CONTEXT.md v2.1  
**Depends on:** Sprint 0–8 green (API: Auth, Identifiers, Scans+SSE, Findings, PDSS, Recommendations, Identity graph, Remediation, Privacy)  
**Goal:** From completed Sprint 8 → **Frontend Core**: Vite + React 18 + TS + Tailwind + shadcn-style UI + TanStack Query + React Router; **Auth** (register/login/MFA/refresh), **identifiers** + verification, **scan start + SSE progress**, **findings**, **PDSS breakdown + vector**, **recommendations**, **basic identity graph**.  

**Effort estimate:** ~10 days (solo)  
**Critical path next:** Sprint 10 Frontend Creative + Remediation UX  

> **Load MASTER_ENGINEERING_CONTEXT.md first.**  
> Frontend talks **only** to versioned `/api/v1` DTOs. Never bypass G1 (verified-only scans). Surface XposedOrNot attribution. Zero paid keys.  
> No `localStorage` for secrets beyond access/refresh tokens (httpOnly cookies ideal later; MVP: memory + sessionStorage refresh with clear disclosure). Prefer in-memory access token + sessionStorage refresh for SPA simplicity under free self-host.

---

# PART A — Pre-Sprint 9 (from DigiZafe monorepo root)

```bash
# 1. Backend must be green
docker compose ps
curl -s http://localhost:8000/api/v1/health | jq .
# Auth, identifiers, scans, scores, recommendations, identity must work

# 2. Scaffold frontend (if empty)
cd frontend 2>/dev/null || mkdir -p frontend && cd frontend

# If not already a Vite app:
# npm create vite@latest . -- --template react-ts
# (or paste package.json + configs below into existing frontend/)

mkdir -p src/{app,features/{auth,identifiers,scans,findings,scores,recommendations,identity,dashboard},components/{ui,layout,charts,graph},lib,hooks,styles}
mkdir -p public

# 3. From DigiZafe root after files are pasted:
# cd frontend && npm install
# Update docker-compose + Caddy for frontend (see PART B)

echo "✅ Pre-Sprint 9 dirs ready. Apply file contents below."
```

**CORS:** Ensure backend `.env` includes:

```bash
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:8000"]
```

---

# PART B — Sprint 9 File Contents

---

## 1. UPDATE: Root `.env.example` (append)

```bash
# === Sprint 9: Frontend ===
# Vite env (also copy to frontend/.env)
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_NAME=DigiZafe
VITE_SSE_USE_FETCH=true
# Attribution footer
VITE_XPOSEDORNOT_ATTRIBUTION=Breach data: XposedOrNot (https://xposedornot.com)
```

Create `frontend/.env`:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_NAME=DigiZafe
VITE_SSE_USE_FETCH=true
VITE_XPOSEDORNOT_ATTRIBUTION=Breach data: XposedOrNot (https://xposedornot.com)
```

---

## 2. NEW/REPLACE: `frontend/package.json`

```json
{
  "name": "digizafe-frontend",
  "private": true,
  "version": "0.9.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 5173",
    "build": "tsc -b && vite build",
    "preview": "vite preview --host 0.0.0.0 --port 5173",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
  },
  "dependencies": {
    "@radix-ui/react-dialog": "^1.1.2",
    "@radix-ui/react-dropdown-menu": "^2.1.2",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-progress": "^1.1.0",
    "@radix-ui/react-select": "^2.1.2",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-tabs": "^1.1.1",
    "@radix-ui/react-toast": "^1.2.2",
    "@tanstack/react-query": "^5.59.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "cytoscape": "^3.30.2",
    "lucide-react": "^0.454.0",
    "react": "^18.3.1",
    "react-cytoscapejs": "^2.0.0",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "recharts": "^2.13.0",
    "tailwind-merge": "^2.5.4",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@types/cytoscape": "^3.21.8",
    "@types/node": "^22.9.0",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.14",
    "typescript": "~5.6.3",
    "vite": "^5.4.10"
  }
}
```

---

## 3. NEW: `frontend/vite.config.ts`

```typescript
import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      // Optional: same-origin API in dev
      // "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
```

---

## 4. NEW: `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

---

## 5. NEW: `frontend/tsconfig.node.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler"
  },
  "include": ["vite.config.ts"]
}
```

---

## 6. NEW: `frontend/tailwind.config.js`

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        severity: {
          none: "#64748b",
          low: "#22c55e",
          medium: "#eab308",
          high: "#f97316",
          critical: "#ef4444",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
};
```

---

## 7. NEW: `frontend/postcss.config.js`

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

---

## 8. NEW: `frontend/index.html`

```html
<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="DigiZafe — Personal Digital Exposure Intelligence & Remediation" />
    <title>DigiZafe</title>
  </head>
  <body class="min-h-screen bg-background text-foreground antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

---

## 9. NEW: `frontend/public/favicon.svg`

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#0f172a"/>
  <path d="M18 36c6-14 22-14 28 0" stroke="#38bdf8" stroke-width="4" fill="none" stroke-linecap="round"/>
  <circle cx="32" cy="28" r="6" fill="#22d3ee"/>
  <path d="M20 44h24" stroke="#64748b" stroke-width="3" stroke-linecap="round"/>
</svg>
```

---

## 10. NEW: `frontend/src/styles/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: 222 47% 6%;
  --foreground: 210 40% 98%;
  --card: 222 47% 9%;
  --card-foreground: 210 40% 98%;
  --primary: 199 89% 48%;
  --primary-foreground: 222 47% 6%;
  --secondary: 217 33% 17%;
  --secondary-foreground: 210 40% 98%;
  --muted: 217 33% 14%;
  --muted-foreground: 215 20% 65%;
  --accent: 217 33% 17%;
  --accent-foreground: 210 40% 98%;
  --destructive: 0 72% 51%;
  --destructive-foreground: 210 40% 98%;
  --border: 217 33% 18%;
  --input: 217 33% 18%;
  --ring: 199 89% 48%;
  --radius: 0.75rem;
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

---

## 11. NEW: `frontend/src/lib/utils.ts`

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function severityColor(sev: string | undefined): string {
  const s = (sev || "info").toLowerCase();
  if (s === "critical") return "text-severity-critical";
  if (s === "high") return "text-severity-high";
  if (s === "medium") return "text-severity-medium";
  if (s === "low") return "text-severity-low";
  return "text-severity-none";
}

export function severityBg(sev: string | undefined): string {
  const s = (sev || "info").toLowerCase();
  if (s === "critical") return "bg-red-500/15 border-red-500/40";
  if (s === "high") return "bg-orange-500/15 border-orange-500/40";
  if (s === "medium") return "bg-yellow-500/15 border-yellow-500/40";
  if (s === "low") return "bg-green-500/15 border-green-500/40";
  return "bg-slate-500/15 border-slate-500/40";
}

export function redactEmail(email: string): string {
  const [local, domain] = email.split("@");
  if (!domain) return "***";
  if (local.length <= 2) return `${local[0]}***@${domain}`;
  return `${local.slice(0, 2)}***@${domain}`;
}

export function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
```

---

## 12. NEW: `frontend/src/lib/types.ts`

```typescript
export type IdentifierType =
  | "email"
  | "phone"
  | "username"
  | "domain"
  | "github_username";

export interface UserPublic {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  mfa_enabled: boolean;
  created_at: string;
  last_login_at?: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  mfa_required?: boolean;
}

export interface IdentifierPublic {
  id: string;
  type: string;
  value_display: string;
  value_canonical: string;
  is_verified: boolean;
  verified_at?: string | null;
  verification_method?: string | null;
  last_revalidated_at?: string | null;
  created_at: string;
}

export interface VerificationStartResponse {
  challenge_id: string;
  method: string;
  expires_at: string;
  instructions: Record<string, unknown>;
  dev_code?: string | null;
}

export interface ScanPublic {
  id: string;
  identifier_id: string;
  status: string;
  layer_scope: string;
  connector_ids?: string[] | null;
  progress_pct: number;
  message?: string | null;
  error?: string | null;
  observation_count: number;
  finding_count: number;
  deadline_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  meta?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  connector_runs?: ScanConnectorRun[];
}

export interface ScanConnectorRun {
  id: string;
  connector_id: string;
  status: string;
  skip_reason?: string | null;
  error?: string | null;
  cache_hit: boolean;
  observation_count: number;
  finding_count: number;
  result_meta?: Record<string, unknown> | null;
}

export interface FindingPublic {
  id: string;
  identifier_id: string;
  kind: string;
  source: string;
  title: string;
  summary: string;
  severity_hint: string;
  confidence: number;
  layer: string;
  track: string;
  raw_ref?: string | null;
  attributes?: Record<string, unknown> | null;
  attribution?: string | null;
  first_seen_at: string;
  last_seen_at: string;
  times_seen: number;
  status: string;
  created_at: string;
}

export interface ScorePublic {
  id?: string | null;
  identifier_id?: string | null;
  model_version: string;
  score_confirmed: number;
  score_possible: number;
  score_combined: number;
  severity: string;
  vector: string;
  metrics?: Record<string, number> | null;
  contributions?: Contribution[] | null;
  counterfactuals?: Counterfactual[] | null;
  attributions?: string[] | null;
  explanation_summary: string;
  finding_count: number;
  trigger?: string;
  created_at?: string | null;
  meta?: Record<string, unknown> | null;
}

export interface Contribution {
  finding_id: string;
  kind: string;
  source: string;
  track: string;
  title: string;
  base: number;
  temporal: number;
  environmental: number;
  surprisal: number;
  reuse: number;
  raw_score: number;
  weighted_score: number;
  drivers?: Record<string, unknown>[];
  vector_fragment?: string;
}

export interface Counterfactual {
  action?: string;
  finding_id?: string;
  title?: string;
  source?: string;
  score_before?: number;
  score_after?: number;
  delta?: number;
  narrative?: string;
}

export interface RecommendationPublic {
  id: string;
  plan_id: string;
  identifier_id?: string | null;
  code: string;
  lane: string;
  title: string;
  summary: string;
  urgency: number;
  effort_hours: number;
  roi: number;
  priority: number;
  sort_order: number;
  depends_on?: string[] | null;
  related_finding_ids?: string[] | null;
  steps?: string[] | null;
  links?: { label: string; url: string }[] | null;
  playbook_key: string;
  meta?: Record<string, unknown> | null;
  status: string;
  model_version: string;
  created_at: string;
}

export interface PlanPublic {
  id: string;
  identifier_id?: string | null;
  model_version: string;
  score_snapshot_id?: string | null;
  freeze_recommended: boolean;
  dag_order?: string[] | null;
  summary: string;
  meta?: Record<string, unknown> | null;
  created_at: string;
  recommendations: RecommendationPublic[];
}

export interface IdentityGraphPublic {
  nodes: { id: string; type: string; value_display: string; is_verified: boolean }[];
  edges: {
    id: string;
    left_identifier_id: string;
    right_identifier_id: string;
    match_weight: number;
    match_prob: number;
    decision: string;
    review_status: string;
  }[];
  collisions?: { id: string; reason: string }[];
  model_version: string;
}

export interface ApiError {
  detail?: string | unknown;
  title?: string;
  code?: string;
}
```

---

## 13. NEW: `frontend/src/lib/auth-store.ts`

```typescript
import { create } from "zustand";
import type { UserPublic } from "./types";

const REFRESH_KEY = "digizafe_refresh";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserPublic | null;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: UserPublic | null) => void;
  clear: () => void;
  hydrateFromSession: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  setTokens: (access, refresh) => {
    try {
      sessionStorage.setItem(REFRESH_KEY, refresh);
    } catch {
      /* ignore */
    }
    set({ accessToken: access, refreshToken: refresh });
  },
  setUser: (user) => set({ user }),
  clear: () => {
    try {
      sessionStorage.removeItem(REFRESH_KEY);
    } catch {
      /* ignore */
    }
    set({ accessToken: null, refreshToken: null, user: null });
  },
  hydrateFromSession: () => {
    try {
      const r = sessionStorage.getItem(REFRESH_KEY);
      if (r) set({ refreshToken: r });
    } catch {
      /* ignore */
    }
  },
}));

export function getRefreshFromSession(): string | null {
  try {
    return sessionStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}
```

---

## 14. NEW: `frontend/src/lib/api.ts`

```typescript
import { useAuthStore, getRefreshFromSession } from "./auth-store";
import type { TokenPair } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export class ApiClientError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    const detail =
      typeof body === "object" && body && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `HTTP ${status}`;
    super(detail);
    this.status = status;
    this.body = body;
  }
}

async function parseJson(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const store = useAuthStore.getState();
  const refresh = store.refreshToken || getRefreshFromSession();
  if (!refresh) return null;

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) {
          store.clear();
          return null;
        }
        const data = (await res.json()) as TokenPair;
        store.setTokens(data.access_token, data.refresh_token);
        return data.access_token;
      } catch {
        store.clear();
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  auth = true
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (auth) {
    let token = useAuthStore.getState().accessToken;
    if (!token) {
      token = await refreshAccessToken();
    }
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  let res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401 && auth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(`${BASE}${path}`, { ...options, headers });
    }
  }

  const body = await parseJson(res);
  if (!res.ok) {
    throw new ApiClientError(res.status, body);
  }
  return body as T;
}

export const api = {
  get: <T>(path: string, auth = true) => apiFetch<T>(path, { method: "GET" }, auth),
  post: <T>(path: string, body?: unknown, auth = true) =>
    apiFetch<T>(
      path,
      { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined },
      auth
    ),
  patch: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  del: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};

export { BASE as API_BASE };
```

---

## 15. NEW: `frontend/src/lib/sse.ts`

```typescript
/**
 * Fetch-based SSE (supports Authorization header; native EventSource cannot).
 */
import { useAuthStore } from "./auth-store";
import { API_BASE } from "./api";

export type SseHandlers = {
  onEvent?: (event: string, data: unknown, id?: string) => void;
  onError?: (err: Error) => void;
  onDone?: () => void;
};

export function openScanSse(scanId: string, handlers: SseHandlers): () => void {
  const controller = new AbortController();
  const token = useAuthStore.getState().accessToken;

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/scans/${scanId}/events`, {
        method: "GET",
        headers: {
          Accept: "text/event-stream",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        throw new Error(`SSE HTTP ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let eventName = "message";
      let eventId: string | undefined;
      let dataLines: string[] = [];

      const flush = () => {
        if (!dataLines.length) {
          eventName = "message";
          eventId = undefined;
          return;
        }
        const raw = dataLines.join("\n");
        dataLines = [];
        let parsed: unknown = raw;
        try {
          parsed = JSON.parse(raw);
        } catch {
          /* keep string */
        }
        handlers.onEvent?.(eventName, parsed, eventId);
        if (eventName === "done") handlers.onDone?.();
        eventName = "message";
        eventId = undefined;
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split(/\r?\n/);
        buffer = parts.pop() ?? "";
        for (const line of parts) {
          if (line === "") {
            flush();
            continue;
          }
          if (line.startsWith(":")) continue; // comment / ping
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("id:")) {
            eventId = line.slice(3).trim();
          } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trimStart());
          }
        }
      }
      flush();
      handlers.onDone?.();
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      handlers.onError?.(e as Error);
    }
  })();

  return () => controller.abort();
}
```

---

## 16. NEW: `frontend/src/components/ui/*` (minimal shadcn-style)

### `frontend/src/components/ui/button.tsx`

```tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        outline: "border border-input bg-transparent hover:bg-accent",
        ghost: "hover:bg-accent",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  }
);
Button.displayName = "Button";
```

### `frontend/src/components/ui/card.tsx`

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-xl border bg-card text-card-foreground shadow-sm", className)}
      {...props}
    />
  );
}
export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />;
}
export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-lg font-semibold leading-none tracking-tight", className)} {...props} />;
}
export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-muted-foreground", className)} {...props} />;
}
export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-6 pt-0", className)} {...props} />;
}
```

### `frontend/src/components/ui/input.tsx`

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      ref={ref}
      {...props}
    />
  )
);
Input.displayName = "Input";
```

### `frontend/src/components/ui/label.tsx`

```tsx
import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { cn } from "@/lib/utils";

export const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn("text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70", className)}
    {...props}
  />
));
Label.displayName = "Label";
```

### `frontend/src/components/ui/badge.tsx`

```tsx
import { cn } from "@/lib/utils";

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { variant?: "default" | "secondary" | "outline" | "destructive" }) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
        variant === "default" && "border-transparent bg-primary text-primary-foreground",
        variant === "secondary" && "border-transparent bg-secondary text-secondary-foreground",
        variant === "destructive" && "border-transparent bg-destructive text-destructive-foreground",
        variant === "outline" && "text-foreground",
        className
      )}
      {...props}
    />
  );
}
```

### `frontend/src/components/ui/progress.tsx`

```tsx
import * as ProgressPrimitive from "@radix-ui/react-progress";
import { cn } from "@/lib/utils";

export function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <ProgressPrimitive.Root
      className={cn("relative h-2 w-full overflow-hidden rounded-full bg-secondary", className)}
      value={value}
    >
      <ProgressPrimitive.Indicator
        className="h-full w-full flex-1 bg-primary transition-all"
        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
      />
    </ProgressPrimitive.Root>
  );
}
```

### `frontend/src/components/ui/tabs.tsx`

```tsx
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;
export function TabsList({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn("inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground", className)}
      {...props}
    />
  );
}
export function TabsTrigger({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow",
        className
      )}
      {...props}
    />
  );
}
export const TabsContent = TabsPrimitive.Content;
```

---

## 17. NEW: `frontend/src/components/layout/AppShell.tsx`

```tsx
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Fingerprint,
  Radar,
  AlertTriangle,
  Gauge,
  ListChecks,
  Network,
  LogOut,
  Shield,
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/identifiers", label: "Identifiers", icon: Fingerprint },
  { to: "/app/scans", label: "Scans", icon: Radar },
  { to: "/app/findings", label: "Findings", icon: AlertTriangle },
  { to: "/app/scores", label: "PDSS Score", icon: Gauge },
  { to: "/app/recommendations", label: "Plan", icon: ListChecks },
  { to: "/app/identity", label: "Identity graph", icon: Network },
];

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);
  const navigate = useNavigate();
  const attribution = import.meta.env.VITE_XPOSEDORNOT_ATTRIBUTION as string | undefined;

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 border-r bg-card/40 md:flex md:flex-col">
        <div className="flex items-center gap-2 border-b px-4 py-4">
          <Shield className="h-6 w-6 text-primary" />
          <div>
            <div className="font-semibold tracking-tight">DigiZafe</div>
            <div className="text-xs text-muted-foreground">Exposure intelligence</div>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="Main">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground",
                  isActive && "bg-accent text-foreground"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t p-3 text-xs text-muted-foreground">
          <div className="mb-2 truncate" title={user?.email}>
            {user?.email}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={() => {
              clear();
              navigate("/login");
            }}
          >
            <LogOut className="mr-2 h-4 w-4" /> Sign out
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b px-4 py-3 md:hidden">
          <Link to="/app" className="flex items-center gap-2 font-semibold">
            <Shield className="h-5 w-5 text-primary" /> DigiZafe
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              clear();
              navigate("/login");
            }}
          >
            Sign out
          </Button>
        </header>
        {/* mobile nav */}
        <div className="flex gap-1 overflow-x-auto border-b p-2 md:hidden">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "whitespace-nowrap rounded-md px-2 py-1 text-xs",
                  isActive ? "bg-accent" : "text-muted-foreground"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>

        <main className="flex-1 overflow-auto p-4 md:p-8">
          <Outlet />
        </main>

        <footer className="border-t px-4 py-3 text-center text-xs text-muted-foreground">
          {attribution || "Free-path breach data: XposedOrNot — personal use; respect ToS."}
          {" · "}Self-only verified identifiers (G1)
        </footer>
      </div>
    </div>
  );
}
```

---

## 18. NEW: `frontend/src/components/charts/PdssGauge.tsx`

```tsx
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from "recharts";
import { cn, severityColor } from "@/lib/utils";

export function PdssGauge({
  score,
  severity,
  className,
}: {
  score: number;
  severity: string;
  className?: string;
}) {
  const data = [{ name: "PDSS", value: Math.min(10, Math.max(0, score)), fill: "hsl(199 89% 48%)" }];
  return (
    <div className={cn("relative mx-auto h-48 w-48", className)}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="70%"
          outerRadius="100%"
          barSize={14}
          data={data}
          startAngle={225}
          endAngle={-45}
        >
          <PolarAngleAxis type="number" domain={[0, 10]} tick={false} />
          <RadialBar background dataKey="value" cornerRadius={8} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-3xl font-bold tabular-nums">{score.toFixed(1)}</div>
        <div className={cn("text-sm font-medium capitalize", severityColor(severity))}>{severity}</div>
      </div>
    </div>
  );
}
```

---

## 19. NEW: `frontend/src/components/charts/PdssBreakdown.tsx`

```tsx
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { Contribution, ScorePublic } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const METRIC_LABELS: Record<string, string> = {
  S: "Sensitivity",
  D: "Discoverability",
  L: "Linkability",
  I: "Impact",
  T: "Temporal",
  E: "Environmental",
  U: "Surprisal",
  R: "Reuse",
};

export function PdssBreakdown({ score }: { score: ScorePublic }) {
  const metrics = score.metrics || {};
  const metricData = Object.entries(METRIC_LABELS).map(([k, label]) => ({
    key: k,
    label,
    value: Number(metrics[k] ?? 0),
  }));

  const contribs = (score.contributions || []) as Contribution[];
  const top = contribs.slice(0, 8).map((c) => ({
    name: c.title.length > 28 ? c.title.slice(0, 28) + "…" : c.title,
    full: c.title,
    value: Number(c.weighted_score || 0),
    source: c.source,
  }));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Vector metrics</CardTitle>
          <CardDescription className="break-all font-mono text-xs">{score.vector}</CardDescription>
        </CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={metricData} layout="vertical" margin={{ left: 16 }}>
              <XAxis type="number" domain={[0, "auto"]} hide />
              <YAxis type="category" dataKey="label" width={110} tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {metricData.map((_, i) => (
                  <Cell key={i} fill="hsl(199 89% 48%)" fillOpacity={0.75} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Top contributions</CardTitle>
          <CardDescription>
            Confirmed {score.score_confirmed.toFixed(1)} · Possible {score.score_possible.toFixed(1)} ·{" "}
            {score.model_version}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {top.length === 0 && <p className="text-sm text-muted-foreground">No contributions yet.</p>}
          {top.map((c, i) => (
            <div key={i} className="flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
              <div className="min-w-0">
                <div className="truncate font-medium" title={c.full}>
                  {c.name}
                </div>
                <Badge variant="outline" className="mt-1">
                  {c.source}
                </Badge>
              </div>
              <div className="tabular-nums text-muted-foreground">{c.value.toFixed(2)}</div>
            </div>
          ))}
          {(score.attributions || []).length > 0 && (
            <p className="pt-2 text-xs text-muted-foreground">
              Attribution: {(score.attributions || []).join(" · ")}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## 20. NEW: `frontend/src/components/graph/IdentityGraphView.tsx`

```tsx
import { useMemo } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import type { IdentityGraphPublic } from "@/lib/types";

export function IdentityGraphView({ graph }: { graph: IdentityGraphPublic }) {
  const elements = useMemo(() => {
    const nodes = graph.nodes.map((n) => ({
      data: {
        id: n.id,
        label: `${n.type}\n${n.value_display}`,
        verified: n.is_verified,
      },
    }));
    const edges = graph.edges
      .filter((e) => e.decision !== "none")
      .map((e) => ({
        data: {
          id: e.id,
          source: e.left_identifier_id,
          target: e.right_identifier_id,
          label: `${(e.match_prob * 100).toFixed(0)}%`,
          decision: e.decision,
        },
      }));
    return [...nodes, ...edges];
  }, [graph]);

  const stylesheet = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "text-wrap": "wrap",
        "text-valign": "center",
        "text-halign": "center",
        "font-size": 9,
        color: "#e2e8f0",
        "background-color": "#0ea5e9",
        width: 56,
        height: 56,
        "text-max-width": 70,
      },
    },
    {
      selector: "node[verified = 0], node[verified = false]",
      style: { "background-color": "#64748b" },
    },
    {
      selector: "edge",
      style: {
        width: 2,
        "line-color": "#475569",
        "target-arrow-color": "#475569",
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        label: "data(label)",
        "font-size": 8,
        color: "#94a3b8",
      },
    },
    {
      selector: 'edge[decision = "auto_link"]',
      style: { "line-color": "#22c55e", "target-arrow-color": "#22c55e" },
    },
    {
      selector: 'edge[decision = "review"]',
      style: { "line-color": "#eab308", "target-arrow-color": "#eab308" },
    },
  ];

  if (!graph.nodes.length) {
    return <p className="text-sm text-muted-foreground">Add and verify identifiers, then rebuild the graph.</p>;
  }

  return (
    <div className="h-[420px] w-full overflow-hidden rounded-xl border bg-card/30">
      <CytoscapeComponent
        elements={elements as never}
        style={{ width: "100%", height: "100%" }}
        stylesheet={stylesheet as never}
        layout={{ name: "cose", animate: false, padding: 30 } as never}
        cy={(cy) => {
          cy.userZoomingEnabled(true);
          cy.userPanningEnabled(true);
        }}
      />
    </div>
  );
}
```

---

## 21. NEW: `frontend/src/hooks/useAuth.ts`

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { TokenPair, UserPublic } from "@/lib/types";

export function useMe(enabled = true) {
  const setUser = useAuthStore((s) => s.setUser);
  const access = useAuthStore((s) => s.accessToken);
  const refresh = useAuthStore((s) => s.refreshToken);

  return useQuery({
    queryKey: ["me"],
    enabled: enabled && !!(access || refresh),
    queryFn: async () => {
      const me = await api.get<UserPublic>("/auth/me");
      setUser(me);
      return me;
    },
    retry: false,
  });
}

export function useLogin() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { email: string; password: string; mfa_code?: string }) => {
      return api.post<TokenPair>("/auth/login/json", body, false);
    },
    onSuccess: async (data) => {
      if (data.mfa_required) return data;
      setTokens(data.access_token, data.refresh_token);
      await qc.invalidateQueries({ queryKey: ["me"] });
      return data;
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      api.post<UserPublic>("/auth/register", body, false),
  });
}
```

---

## 22. Feature API hooks

### `frontend/src/features/identifiers/api.ts`

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IdentifierPublic, IdentifierType, VerificationStartResponse } from "@/lib/types";

export function useIdentifiers() {
  return useQuery({
    queryKey: ["identifiers"],
    queryFn: () => api.get<IdentifierPublic[]>("/identifiers"),
  });
}

export function useCreateIdentifier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { type: IdentifierType; value: string }) =>
      api.post<IdentifierPublic>("/identifiers", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identifiers"] }),
  });
}

export function useDeleteIdentifier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del<{ message: string }>(`/identifiers/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identifiers"] }),
  });
}

export function useStartVerify() {
  return useMutation({
    mutationFn: ({ id, method }: { id: string; method?: string }) => {
      const q = method ? `?method=${encodeURIComponent(method)}` : "";
      return api.post<VerificationStartResponse>(`/identifiers/${id}/verify/start${q}`);
    },
  });
}

export function useConfirmVerify() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      challenge_id,
      code,
    }: {
      id: string;
      challenge_id: string;
      code?: string;
    }) =>
      api.post(
        `/identifiers/${id}/verify/confirm?challenge_id=${encodeURIComponent(challenge_id)}`,
        { code }
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identifiers"] }),
  });
}
```

### `frontend/src/features/scans/api.ts`

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScanPublic } from "@/lib/types";

export function useScans() {
  return useQuery({
    queryKey: ["scans"],
    queryFn: () => api.get<ScanPublic[]>("/scans"),
  });
}

export function useScan(id: string | undefined) {
  return useQuery({
    queryKey: ["scans", id],
    enabled: !!id,
    queryFn: () => api.get<ScanPublic>(`/scans/${id}`),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      if (s && ["completed", "partial", "failed", "cancelled", "timed_out"].includes(s)) return false;
      return 3000;
    },
  });
}

export function useCreateScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { identifier_id: string; connector_ids?: string[] }) =>
      api.post<ScanPublic>("/scans", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scans"] }),
  });
}

export function useCancelScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<ScanPublic>(`/scans/${id}/cancel`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scans"] }),
  });
}
```

### `frontend/src/features/findings/api.ts`

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FindingPublic } from "@/lib/types";

export function useFindings(identifierId?: string) {
  const q = identifierId ? `?identifier_id=${encodeURIComponent(identifierId)}` : "";
  return useQuery({
    queryKey: ["findings", identifierId || "all"],
    queryFn: () => api.get<FindingPublic[]>(`/findings${q}`),
  });
}
```

### `frontend/src/features/scores/api.ts`

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScorePublic } from "@/lib/types";

export function useLatestScore(identifierId?: string) {
  const q = identifierId ? `?identifier_id=${encodeURIComponent(identifierId)}` : "";
  return useQuery({
    queryKey: ["scores", "latest", identifierId || "all"],
    queryFn: () => api.get<ScorePublic>(`/scores/latest${q}`),
    retry: false,
  });
}

export function useComputeScore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { identifier_id?: string; persist?: boolean }) =>
      api.post<ScorePublic>("/scores/compute", { persist: true, trigger: "manual", ...body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scores"] });
    },
  });
}

export function useScoreHistory(identifierId?: string) {
  const q = identifierId ? `?identifier_id=${encodeURIComponent(identifierId)}` : "";
  return useQuery({
    queryKey: ["scores", "history", identifierId || "all"],
    queryFn: () =>
      api.get<{ id: string; score_combined: number; severity: string; created_at: string; trigger: string }[]>(
        `/scores/history${q}`
      ),
  });
}
```

### `frontend/src/features/recommendations/api.ts`

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PlanPublic, RecommendationPublic } from "@/lib/types";

export function useLatestPlan(identifierId?: string) {
  const q = identifierId ? `?identifier_id=${encodeURIComponent(identifierId)}` : "";
  return useQuery({
    queryKey: ["recommendations", "latest", identifierId || "all"],
    queryFn: () => api.get<PlanPublic>(`/recommendations/latest${q}`),
    retry: false,
  });
}

export function useGeneratePlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { identifier_id?: string }) =>
      api.post<PlanPublic>("/recommendations/generate", { persist: true, ...body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recommendations"] }),
  });
}

export function useUpdateRecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch<RecommendationPublic>(`/recommendations/${id}`, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recommendations"] }),
  });
}
```

### `frontend/src/features/identity/api.ts`

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IdentityGraphPublic } from "@/lib/types";

export function useIdentityGraph() {
  return useQuery({
    queryKey: ["identity", "graph"],
    queryFn: () => api.get<IdentityGraphPublic>("/identity/graph"),
  });
}

export function useRebuildGraph() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<IdentityGraphPublic>("/identity/graph/rebuild"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identity"] }),
  });
}
```

---

## 23. Pages

### `frontend/src/features/auth/LoginPage.tsx`

```tsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useLogin, useMe } from "@/hooks/useAuth";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Shield } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { UserPublic } from "@/lib/types";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfa, setMfa] = useState("");
  const [needMfa, setNeedMfa] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const login = useLogin();
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const qc = useQueryClient();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const data = await login.mutateAsync({
        email,
        password,
        mfa_code: needMfa ? mfa : undefined,
      });
      if (data.mfa_required) {
        setNeedMfa(true);
        return;
      }
      const me = await api.get<UserPublic>("/auth/me");
      setUser(me);
      await qc.invalidateQueries({ queryKey: ["me"] });
      navigate("/app");
    } catch (err) {
      setError((err as Error).message || "Login failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-2 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <CardTitle>Sign in to DigiZafe</CardTitle>
          <CardDescription>Self-only digital exposure intelligence</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={12} />
            </div>
            {needMfa && (
              <div className="space-y-2">
                <Label htmlFor="mfa">MFA code</Label>
                <Input id="mfa" inputMode="numeric" value={mfa} onChange={(e) => setMfa(e.target.value)} required />
              </div>
            )}
            {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
            <Button type="submit" className="w-full" disabled={login.isPending}>
              {login.isPending ? "Signing in…" : "Sign in"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            No account?{" "}
            <Link className="text-primary underline-offset-4 hover:underline" to="/register">
              Register
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

### `frontend/src/features/auth/RegisterPage.tsx`

```tsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useRegister } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const reg = useRegister();
  const navigate = useNavigate();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await reg.mutateAsync({ email, password });
      navigate("/login");
    } catch (err) {
      setError((err as Error).message || "Registration failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create account</CardTitle>
          <CardDescription>Password min 12 characters. Self-only scans only.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={12} />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={reg.isPending}>
              Register
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Have an account? <Link className="text-primary hover:underline" to="/login">Sign in</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

### `frontend/src/features/dashboard/DashboardPage.tsx`

```tsx
import { Link } from "react-router-dom";
import { useIdentifiers } from "@/features/identifiers/api";
import { useLatestScore } from "@/features/scores/api";
import { useFindings } from "@/features/findings/api";
import { useLatestPlan } from "@/features/recommendations/api";
import { PdssGauge } from "@/components/charts/PdssGauge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { severityBg } from "@/lib/utils";

export function DashboardPage() {
  const ids = useIdentifiers();
  const score = useLatestScore();
  const findings = useFindings();
  const plan = useLatestPlan();

  const verified = (ids.data || []).filter((i) => i.is_verified).length;
  const openFindings = (findings.data || []).filter((f) => f.status === "open").length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Verified identifiers → free surface discovery → PDSS → plan.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Identifiers</CardTitle>
            <CardDescription>{verified} verified / {(ids.data || []).length} total</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary" size="sm">
              <Link to="/app/identifiers">Manage</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Open findings</CardTitle>
            <CardDescription>{openFindings} open</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary" size="sm">
              <Link to="/app/findings">View</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recommendations</CardTitle>
            <CardDescription>
              {plan.data ? `${plan.data.recommendations.filter((r) => r.status === "open").length} open` : "No plan yet"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary" size="sm">
              <Link to="/app/recommendations">Plan</Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Personal Data Severity Score</CardTitle>
          <CardDescription>
            {score.data?.explanation_summary || "Compute PDSS after a scan with findings."}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
          {score.data ? (
            <>
              <PdssGauge score={score.data.score_combined} severity={score.data.severity} />
              <div className="space-y-2 text-sm">
                <div className={`inline-flex rounded-md border px-2 py-1 capitalize ${severityBg(score.data.severity)}`}>
                  {score.data.severity}
                </div>
                <p className="font-mono text-xs text-muted-foreground break-all">{score.data.vector}</p>
                <Button asChild size="sm">
                  <Link to="/app/scores">Full breakdown</Link>
                </Button>
              </div>
            </>
          ) : (
            <div className="text-sm text-muted-foreground">
              No score yet.{" "}
              <Link className="text-primary hover:underline" to="/app/scans">
                Run a scan
              </Link>{" "}
              then compute PDSS.
            </div>
          )}
        </CardContent>
      </Card>

      {(score.data?.attributions || []).length > 0 && (
        <p className="text-xs text-muted-foreground">
          Data attributions:{" "}
          {(score.data?.attributions || []).map((a) => (
            <Badge key={a} variant="outline" className="mr-1">
              {a}
            </Badge>
          ))}
        </p>
      )}
    </div>
  );
}
```

### `frontend/src/features/identifiers/IdentifiersPage.tsx`

```tsx
import { useState } from "react";
import {
  useIdentifiers,
  useCreateIdentifier,
  useDeleteIdentifier,
  useStartVerify,
  useConfirmVerify,
} from "./api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import type { IdentifierType } from "@/lib/types";

const TYPES: IdentifierType[] = ["email", "domain", "github_username", "username", "phone"];

export function IdentifiersPage() {
  const { data, isLoading } = useIdentifiers();
  const create = useCreateIdentifier();
  const del = useDeleteIdentifier();
  const start = useStartVerify();
  const confirm = useConfirmVerify();

  const [type, setType] = useState<IdentifierType>("email");
  const [value, setValue] = useState("");
  const [challenge, setChallenge] = useState<{
    id: string;
    challenge_id: string;
    method: string;
    instructions: Record<string, unknown>;
    dev_code?: string | null;
  } | null>(null);
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const onAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    try {
      await create.mutateAsync({ type, value });
      setValue("");
      setMsg("Identifier added (unverified).");
    } catch (err) {
      setMsg((err as Error).message);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Identifiers</h1>
        <p className="text-muted-foreground">
          G1: only <strong>verified</strong> identifiers can be scanned. Free path never requires paid APIs.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add identifier</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onAdd} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="space-y-1">
              <Label>Type</Label>
              <select
                className="flex h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={type}
                onChange={(e) => setType(e.target.value as IdentifierType)}
              >
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1 space-y-1">
              <Label>Value</Label>
              <Input value={value} onChange={(e) => setValue(e.target.value)} required placeholder="you@example.com" />
            </div>
            <Button type="submit" disabled={create.isPending}>
              Add
            </Button>
          </form>
          {msg && <p className="mt-2 text-sm text-muted-foreground">{msg}</p>}
        </CardContent>
      </Card>

      <div className="space-y-3">
        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {(data || []).map((id) => (
          <Card key={id.id}>
            <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{id.value_display}</span>
                  <Badge variant="outline">{id.type}</Badge>
                  <Badge variant={id.is_verified ? "default" : "secondary"}>
                    {id.is_verified ? "verified" : "unverified"}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  canonical: {id.value_canonical}
                  {id.verified_at ? ` · verified ${formatDate(id.verified_at)}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {!id.is_verified && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={async () => {
                      const r = await start.mutateAsync({ id: id.id });
                      setChallenge({
                        id: id.id,
                        challenge_id: r.challenge_id,
                        method: r.method,
                        instructions: r.instructions,
                        dev_code: r.dev_code,
                      });
                      if (r.dev_code) setCode(r.dev_code);
                    }}
                  >
                    Verify
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={() => del.mutate(id.id)}>
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {challenge && (
        <Card>
          <CardHeader>
            <CardTitle>Verification — {challenge.method}</CardTitle>
            <CardDescription>
              {typeof challenge.instructions.message === "string"
                ? challenge.instructions.message
                : JSON.stringify(challenge.instructions)}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {challenge.dev_code && (
              <p className="rounded-md border border-yellow-500/30 bg-yellow-500/10 p-2 text-sm">
                Dev code: <code>{challenge.dev_code}</code>
              </p>
            )}
            {challenge.method === "email_code" && (
              <div className="space-y-1">
                <Label>Code</Label>
                <Input value={code} onChange={(e) => setCode(e.target.value)} />
              </div>
            )}
            {(challenge.method === "dns_txt" || challenge.method === "github_proof") && (
              <pre className="overflow-auto rounded-md bg-muted p-3 text-xs">
                {JSON.stringify(challenge.instructions, null, 2)}
              </pre>
            )}
            <Button
              onClick={async () => {
                await confirm.mutateAsync({
                  id: challenge.id,
                  challenge_id: challenge.challenge_id,
                  code: challenge.method === "email_code" ? code : undefined,
                });
                setChallenge(null);
                setCode("");
              }}
              disabled={confirm.isPending}
            >
              Confirm verification
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

### `frontend/src/features/scans/ScansPage.tsx`

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useIdentifiers } from "@/features/identifiers/api";
import { useCreateScan, useScans, useCancelScan } from "./api";
import { openScanSse } from "@/lib/sse";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import type { ScanPublic } from "@/lib/types";

export function ScansPage() {
  const ids = useIdentifiers();
  const scans = useScans();
  const create = useCreateScan();
  const cancel = useCancelScan();
  const verified = (ids.data || []).filter((i) => i.is_verified);
  const [selected, setSelected] = useState("");
  const [live, setLive] = useState<ScanPublic | null>(null);
  const [sseNote, setSseNote] = useState<string | null>(null);

  useEffect(() => {
    if (!live?.id) return;
    if (["completed", "partial", "failed", "cancelled", "timed_out"].includes(live.status)) return;
    const stop = openScanSse(live.id, {
      onEvent: (event, data) => {
        if (event === "scan" || event === "done" || event === "message") {
          const d = data as Partial<ScanPublic> & { scan_id?: string };
          setLive((prev) =>
            prev
              ? {
                  ...prev,
                  status: (d.status as string) || prev.status,
                  progress_pct: d.progress_pct ?? prev.progress_pct,
                  message: d.message ?? prev.message,
                  observation_count: d.observation_count ?? prev.observation_count,
                  finding_count: d.finding_count ?? prev.finding_count,
                  connector_runs: (d.connector_runs as ScanPublic["connector_runs"]) || prev.connector_runs,
                  meta: d.meta ?? prev.meta,
                }
              : prev
          );
        }
        if (event === "done") setSseNote("Scan finished (SSE).");
      },
      onError: (e) => setSseNote(e.message),
    });
    return stop;
  }, [live?.id, live?.status]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Scans</h1>
        <p className="text-muted-foreground">
          Discovery runs only on <strong>verified</strong> identifiers. Work executes in Celery (not the request path).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Start surface scan</CardTitle>
          <CardDescription>XposedOrNot is the primary free breach source for emails.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              <option value="">Select verified identifier…</option>
              {verified.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.type}: {i.value_display}
                </option>
              ))}
            </select>
          </div>
          <Button
            disabled={!selected || create.isPending}
            onClick={async () => {
              const scan = await create.mutateAsync({ identifier_id: selected });
              setLive(scan);
              setSseNote("SSE connected…");
            }}
          >
            Start scan
          </Button>
        </CardContent>
      </Card>

      {live && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Live scan <Badge variant="outline">{live.status}</Badge>
            </CardTitle>
            <CardDescription>{live.message || "—"}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Progress value={live.progress_pct || 0} />
            <div className="text-sm text-muted-foreground">
              {live.progress_pct?.toFixed?.(0) ?? live.progress_pct}% · observations {live.observation_count} ·
              findings {live.finding_count}
            </div>
            <ul className="space-y-1 text-sm">
              {(live.connector_runs || []).map((r) => (
                <li key={r.connector_id} className="flex justify-between rounded border px-2 py-1">
                  <span>{r.connector_id}</span>
                  <span className="text-muted-foreground">
                    {r.status}
                    {r.skip_reason ? ` (${r.skip_reason})` : ""}
                    {r.cache_hit ? " · cache" : ""}
                  </span>
                </li>
              ))}
            </ul>
            {sseNote && <p className="text-xs text-muted-foreground">{sseNote}</p>}
            {!["completed", "partial", "failed", "cancelled", "timed_out"].includes(live.status) && (
              <Button size="sm" variant="outline" onClick={() => cancel.mutate(live.id)}>
                Cancel
              </Button>
            )}
            <Button asChild size="sm" variant="secondary">
              <Link to={`/app/scans/${live.id}`}>Open detail</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="space-y-2">
        <h2 className="text-lg font-medium">History</h2>
        {(scans.data || []).map((s) => (
          <Link
            key={s.id}
            to={`/app/scans/${s.id}`}
            className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm hover:bg-accent/40"
          >
            <span>
              <Badge variant="outline" className="mr-2">
                {s.status}
              </Badge>
              {s.finding_count} findings
            </span>
            <span className="text-muted-foreground">{formatDate(s.created_at)}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

### `frontend/src/features/scans/ScanDetailPage.tsx`

```tsx
import { useParams, Link } from "react-router-dom";
import { useScan } from "./api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";

export function ScanDetailPage() {
  const { scanId } = useParams();
  const { data: scan, isLoading } = useScan(scanId);

  if (isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (!scan) return <p>Scan not found</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Scan detail</h1>
        <Button asChild variant="secondary" size="sm">
          <Link to="/app/findings">Findings</Link>
        </Button>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="flex gap-2">
            <Badge>{scan.status}</Badge>
            <span className="text-base font-normal text-muted-foreground">{scan.id}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Progress value={scan.progress_pct} />
          <p>{scan.message}</p>
          <p className="text-muted-foreground">
            Created {formatDate(scan.created_at)} · Finished {formatDate(scan.finished_at)}
          </p>
          <p>
            Observations {scan.observation_count} · Findings {scan.finding_count}
          </p>
          {(scan.meta as { attributions?: string[] } | null)?.attributions && (
            <p className="text-xs text-muted-foreground">
              Attributions: {(scan.meta as { attributions: string[] }).attributions.join(", ")}
            </p>
          )}
          <div className="space-y-1">
            {(scan.connector_runs || []).map((r) => (
              <div key={r.id} className="rounded border px-2 py-1">
                <div className="font-medium">{r.connector_id}</div>
                <div className="text-muted-foreground">
                  {r.status} · obs {r.observation_count} · findings {r.finding_count}
                  {r.skip_reason ? ` · skip: ${r.skip_reason}` : ""}
                  {r.error ? ` · err: ${r.error}` : ""}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

### `frontend/src/features/findings/FindingsPage.tsx`

```tsx
import { useFindings } from "./api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { severityBg, formatDate } from "@/lib/utils";

export function FindingsPage() {
  const { data, isLoading } = useFindings();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Findings</h1>
        <p className="text-muted-foreground">Normalized durable findings (XposedOrNot breaches, surface signals, …).</p>
      </div>
      {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
      <div className="space-y-2">
        {(data || []).map((f) => (
          <Card key={f.id} className={`border ${severityBg(f.severity_hint)}`}>
            <CardContent className="space-y-1 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{f.title}</span>
                <Badge variant="outline">{f.source}</Badge>
                <Badge variant="secondary">{f.kind}</Badge>
                <Badge>{f.severity_hint}</Badge>
                <Badge variant="outline">{f.track}</Badge>
                <Badge variant="outline">{f.status}</Badge>
              </div>
              <p className="text-sm text-muted-foreground">{f.summary}</p>
              <p className="text-xs text-muted-foreground">
                confidence {(f.confidence * 100).toFixed(0)}% · last seen {formatDate(f.last_seen_at)}
                {f.attribution ? ` · ${f.attribution}` : ""}
              </p>
            </CardContent>
          </Card>
        ))}
        {!isLoading && !(data || []).length && (
          <p className="text-sm text-muted-foreground">No findings yet — run a scan on a verified email.</p>
        )}
      </div>
    </div>
  );
}
```

### `frontend/src/features/scores/ScoresPage.tsx`

```tsx
import { useState } from "react";
import { useIdentifiers } from "@/features/identifiers/api";
import { useComputeScore, useLatestScore, useScoreHistory } from "./api";
import { PdssGauge } from "@/components/charts/PdssGauge";
import { PdssBreakdown } from "@/components/charts/PdssBreakdown";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";

export function ScoresPage() {
  const ids = useIdentifiers();
  const [identifierId, setIdentifierId] = useState<string>("");
  const score = useLatestScore(identifierId || undefined);
  const history = useScoreHistory(identifierId || undefined);
  const compute = useComputeScore();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">PDSS Score</h1>
          <p className="text-muted-foreground">Hybrid Base/Temporal/Environmental + surprisal · two-track · explainable.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={identifierId}
            onChange={(e) => setIdentifierId(e.target.value)}
          >
            <option value="">Whole identity / latest</option>
            {(ids.data || []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.type}: {i.value_display}
              </option>
            ))}
          </select>
          <Button
            onClick={() =>
              compute.mutate({ identifier_id: identifierId || undefined, persist: true })
            }
            disabled={compute.isPending}
          >
            {compute.isPending ? "Computing…" : "Compute PDSS"}
          </Button>
        </div>
      </div>

      {score.data ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Current score</CardTitle>
              <CardDescription>{score.data.explanation_summary}</CardDescription>
            </CardHeader>
            <CardContent className="flex justify-center">
              <PdssGauge score={score.data.score_combined} severity={score.data.severity} />
            </CardContent>
          </Card>
          <PdssBreakdown score={score.data} />
          {(score.data.counterfactuals || []).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Counterfactuals (what-if)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {(score.data.counterfactuals || []).map((c, i) => (
                  <p key={i} className="rounded border px-3 py-2">
                    {c.narrative || JSON.stringify(c)}
                  </p>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <p className="text-sm text-muted-foreground">No score yet. Scan first, then compute.</p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>History</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          {(history.data || []).map((h) => (
            <div key={h.id} className="flex justify-between border-b border-border/50 py-1">
              <span>
                {h.score_combined.toFixed(1)} · {h.severity} · {h.trigger}
              </span>
              <span className="text-muted-foreground">{formatDate(h.created_at)}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
```

### `frontend/src/features/recommendations/RecommendationsPage.tsx`

```tsx
import { useState } from "react";
import { useIdentifiers } from "@/features/identifiers/api";
import { useGeneratePlan, useLatestPlan, useUpdateRecommendation } from "./api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function RecommendationsPage() {
  const ids = useIdentifiers();
  const [identifierId, setIdentifierId] = useState("");
  const plan = useLatestPlan(identifierId || undefined);
  const generate = useGeneratePlan();
  const update = useUpdateRecommendation();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Remediation plan</h1>
          <p className="text-muted-foreground">Two-lane: guided + semi-automated (Green brokers). Ordered by urgency, ROI, DAG.</p>
        </div>
        <div className="flex gap-2">
          <select
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={identifierId}
            onChange={(e) => setIdentifierId(e.target.value)}
          >
            <option value="">Scope…</option>
            {(ids.data || []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.value_display}
              </option>
            ))}
          </select>
          <Button
            onClick={() => generate.mutate({ identifier_id: identifierId || undefined })}
            disabled={generate.isPending}
          >
            Generate plan
          </Button>
        </div>
      </div>

      {plan.data && (
        <Card>
          <CardHeader>
            <CardTitle>{plan.data.summary}</CardTitle>
            <CardDescription>
              Model {plan.data.model_version}
              {plan.data.freeze_recommended ? " · Credit freeze recommended" : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {plan.data.recommendations.map((r, idx) => (
              <div key={r.id} className="rounded-lg border p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-muted-foreground">#{idx + 1}</span>
                  <span className="font-medium">{r.title}</span>
                  <Badge variant="outline">{r.lane}</Badge>
                  <Badge variant="secondary">{r.status}</Badge>
                  <Badge variant="outline">priority {r.priority.toFixed(2)}</Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{r.summary}</p>
                {(r.depends_on || []).length > 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">Depends on: {(r.depends_on || []).join(", ")}</p>
                )}
                {r.steps && (
                  <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
                    {r.steps.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ol>
                )}
                {r.links && r.links.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {r.links.map((l) => (
                      <a
                        key={l.url}
                        href={l.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-primary hover:underline"
                      >
                        {l.label}
                      </a>
                    ))}
                  </div>
                )}
                <div className="mt-3 flex gap-2">
                  {r.status !== "done" && (
                    <Button size="sm" variant="secondary" onClick={() => update.mutate({ id: r.id, status: "done" })}>
                      Mark done
                    </Button>
                  )}
                  {r.status !== "dismissed" && (
                    <Button size="sm" variant="ghost" onClick={() => update.mutate({ id: r.id, status: "dismissed" })}>
                      Dismiss
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
      {!plan.data && !plan.isLoading && (
        <p className="text-sm text-muted-foreground">No plan yet — generate after scoring findings.</p>
      )}
    </div>
  );
}
```

### `frontend/src/features/identity/IdentityPage.tsx`

```tsx
import { useIdentityGraph, useRebuildGraph } from "./api";
import { IdentityGraphView } from "@/components/graph/IdentityGraphView";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function IdentityPage() {
  const graph = useIdentityGraph();
  const rebuild = useRebuildGraph();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Identity graph</h1>
          <p className="text-muted-foreground">
            Deciban / Fellegi–Sunter pairwise links among <em>your</em> verified identifiers.
          </p>
        </div>
        <Button onClick={() => rebuild.mutate()} disabled={rebuild.isPending}>
          {rebuild.isPending ? "Rebuilding…" : "Rebuild graph"}
        </Button>
      </div>

      {graph.data && (
        <>
          <IdentityGraphView graph={graph.data} />
          <Card>
            <CardHeader>
              <CardTitle>Edges</CardTitle>
              <CardDescription>Model {graph.data.model_version}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {graph.data.edges.map((e) => (
                <div key={e.id} className="flex flex-wrap items-center gap-2 rounded border px-2 py-1">
                  <Badge variant="outline">{e.decision}</Badge>
                  <span className="text-muted-foreground">
                    p={e.match_prob.toFixed(3)} · review={e.review_status}
                  </span>
                </div>
              ))}
              {!graph.data.edges.length && <p className="text-muted-foreground">No edges yet.</p>}
            </CardContent>
          </Card>
          {(graph.data.collisions || []).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Collisions / review</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-1">
                {(graph.data.collisions || []).map((c) => (
                  <div key={c.id}>{c.reason}</div>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
```

---

## 24. Router + main

### `frontend/src/app/ProtectedRoute.tsx`

```tsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/lib/auth-store";
import { useMe } from "@/hooks/useAuth";

export function ProtectedRoute() {
  const access = useAuthStore((s) => s.accessToken);
  const refresh = useAuthStore((s) => s.refreshToken);
  const { isLoading, isError } = useMe(!!(access || refresh));

  if (!access && !refresh) return <Navigate to="/login" replace />;
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading session…
      </div>
    );
  }
  if (isError && !access) return <Navigate to="/login" replace />;
  return <Outlet />;
}
```

### `frontend/src/app/router.tsx`

```tsx
import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "./ProtectedRoute";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { IdentifiersPage } from "@/features/identifiers/IdentifiersPage";
import { ScansPage } from "@/features/scans/ScansPage";
import { ScanDetailPage } from "@/features/scans/ScanDetailPage";
import { FindingsPage } from "@/features/findings/FindingsPage";
import { ScoresPage } from "@/features/scores/ScoresPage";
import { RecommendationsPage } from "@/features/recommendations/RecommendationsPage";
import { IdentityPage } from "@/features/identity/IdentityPage";

export const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/app" replace /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: "/app",
        element: <AppShell />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: "identifiers", element: <IdentifiersPage /> },
          { path: "scans", element: <ScansPage /> },
          { path: "scans/:scanId", element: <ScanDetailPage /> },
          { path: "findings", element: <FindingsPage /> },
          { path: "scores", element: <ScoresPage /> },
          { path: "recommendations", element: <RecommendationsPage /> },
          { path: "identity", element: <IdentityPage /> },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/app" replace /> },
]);
```

### `frontend/src/main.tsx`

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { router } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import "@/styles/index.css";

useAuthStore.getState().hydrateFromSession();

const qc = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

### `frontend/src/vite-env.d.ts`

```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_APP_NAME: string;
  readonly VITE_SSE_USE_FETCH: string;
  readonly VITE_XPOSEDORNOT_ATTRIBUTION: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

---

## 25. Docker: `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### `frontend/nginx.conf`

```nginx
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;
  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

---

## 26. UPDATE: root `docker-compose.yml` (add frontend service)

```yaml
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: http://localhost:8000/api/v1
    ports:
      - "5173:80"
    depends_on:
      - api
    networks:
      - digizafe
    profiles:
      - frontend
```

**Dev (hot reload) alternative** — run outside compose:

```bash
cd frontend && npm install && npm run dev
# http://localhost:5173
```

---

## 27. Docs: `docs/runbooks/frontend-core.md`

```markdown
# Frontend Core (Sprint 9)

## Stack
React 18 + TS + Vite + Tailwind + Radix/shadcn-style + TanStack Query + React Router + Recharts + Cytoscape

## Routes
| Path | Purpose |
|------|---------|
| /login, /register | Auth |
| /app | Dashboard + PDSS gauge |
| /app/identifiers | CRUD + verify |
| /app/scans | Start scan + SSE live progress |
| /app/findings | Findings list |
| /app/scores | PDSS breakdown + vector + history |
| /app/recommendations | Two-lane plan |
| /app/identity | Graph |

## Auth
- Access token in memory (Zustand)
- Refresh token in sessionStorage
- Auto-refresh on 401 via `/auth/refresh`

## SSE
Fetch stream with `Authorization` header (not native EventSource).

## Free path UX
Footer attribution for XposedOrNot. Unverified identifiers cannot start scans (API enforces G1).
```

---

# PART C — How to finish Sprint 9

```bash
# 1. Paste all frontend files
cd frontend
npm install

# 2. Ensure backend CORS + running
# 3. Dev
npm run dev
# open http://localhost:5173

# 4. Smoke UX path
# Register → Login → Add email → Verify (dev code) → Start scan → watch SSE
# → Findings → Compute PDSS → Generate plan → Rebuild identity graph

# 5. Production build check
npm run build

# 6. Commit (from monorepo root)
git add frontend docs/runbooks/frontend-core.md docker-compose.yml .env.example
git commit -m "feat(sprint-9): frontend core — auth, identifiers, scan SSE, findings, PDSS, recommendations, identity graph"
```

---

# Sprint 9 Definition of Done Checklist

- [ ] MASTER_ENGINEERING_CONTEXT.md respected  
- [ ] Vite + React 18 + TS + Tailwind app builds (`npm run build`)  
- [ ] Auth: register, login, MFA gate, refresh, logout, protected routes  
- [ ] Identifiers: add/list/delete + verify (email_code / dns / github UX)  
- [ ] Scans: start on **verified only**, list, detail, **SSE live progress**  
- [ ] Findings list with source/severity/attribution  
- [ ] PDSS: compute, gauge, vector string, metric bars, contributions, counterfactuals, history  
- [ ] Recommendations: generate plan, DAG-ordered list, mark done/dismiss  
- [ ] Identity graph: rebuild + Cytoscape visualization  
- [ ] XposedOrNot attribution in footer / score UI  
- [ ] TanStack Query + typed API client; no secrets in localStorage (refresh sessionStorage only)  
- [ ] Dark modern UI, basic mobile nav  
- [ ] Zero paid keys / no paid frontend SaaS required  

→ **Sprint 9 complete.**  
Next: **Sprint 10 — Frontend Creative + Remediation UX** (risk autopsy, what-if, narrative briefing, remediation console, privacy center, a11y, onboarding).

---

## File checklist (create)

| Path |
|------|
| `frontend/package.json` |
| `frontend/vite.config.ts`, `tsconfig*.json`, `tailwind.config.js`, `postcss.config.js` |
| `frontend/index.html`, `public/favicon.svg` |
| `frontend/src/styles/index.css` |
| `frontend/src/lib/{utils,types,api,auth-store,sse}.ts` |
| `frontend/src/components/ui/*` |
| `frontend/src/components/layout/AppShell.tsx` |
| `frontend/src/components/charts/{PdssGauge,PdssBreakdown}.tsx` |
| `frontend/src/components/graph/IdentityGraphView.tsx` |
| `frontend/src/hooks/useAuth.ts` |
| `frontend/src/features/**` pages + api hooks |
| `frontend/src/app/{router,ProtectedRoute}.tsx` |
| `frontend/src/main.tsx` |
| `frontend/Dockerfile`, `nginx.conf` |
| `docs/runbooks/frontend-core.md` |
| UPDATE `docker-compose.yml`, `.env.example` |

---

**You are ready for Sprint 9.**  
1. Save this as `Sprint9.md` next to Sprint0–8.  
2. Paste frontend files under `frontend/`.  
3. `npm install && npm run dev` with backend on `:8000`.  
4. Walk the verified-email → scan SSE → PDSS → plan → graph path.  
5. Commit when DoD is green.

When Sprint 9 is green, ask for **Sprint 10** the same way.