# DigiZafe — Sprint 10 Frontend Creative + Remediation UX

**Complete Implementation Guide from Sprint 9 Baseline + All File Contents**

**Document version:** 1.0  
**Based on:** `MASTER_ENGINEERING_CONTEXT.md` v2.1  
**Depends on:** Sprint 0–9 green  
**Goal:** From the completed Sprint 9 frontend core → a polished, accessible, creative DigiZafe experience with:

- Risk autopsy visualization
- What-if remediation simulator
- Grounded narrative briefing UI
- Remediation console
- Green broker opt-out workflow
- CAPTCHA/manual queue handling
- Freeze checklist
- Right-to-know and complaint generators
- Privacy center
- Consent and egress transparency
- Data export and account deletion controls
- Guided onboarding
- Improved accessibility and reduced-motion support
- Memory-only authentication state

**Effort estimate:** ~10 days  
**Critical path next:** Sprint 11 Deep + Constrained-Dark Free Amber

> Load `MASTER_ENGINEERING_CONTEXT.md` before every coding session.  
> Frontend communicates only with `/api/v1` DTOs.  
> Never bypass G1 verified-only enforcement.  
> Do not use `localStorage` or `sessionStorage`. Sprint 10 keeps auth tokens in memory only.  
> Remediation actions must remain user-directed, transparent, and attributable.

---

# PART A — Sprint 10 Scope

## Included

| Area | Sprint 10 outcome |
|---|---|
| Risk autopsy | Explain why the score exists and which findings drive it |
| What-if simulator | Select findings and preview estimated PDSS improvement |
| Narrative briefing | Display grounded narrative from backend facts |
| Remediation console | Start and monitor AIDR-inspired Green broker jobs |
| CAPTCHA queue | Display manual CAPTCHA tasks and resume jobs |
| Freeze checklist | Track credit/security freeze tasks |
| Rights generators | Create and mark DSAR/deletion/complaint drafts |
| Privacy center | Export, consent, audit, egress, deletion |
| Onboarding | Guide users through verify → scan → score → remediate |
| Accessibility | Keyboard navigation, focus styles, live regions, reduced motion |
| Auth security | Remove browser storage dependency from frontend auth state |

## Excluded

- Deep-web or constrained-dark implementation
- New backend discovery connectors
- Paid CAPTCHA services
- Browser extension
- Mobile native application
- Persistent client-side token storage
- Autonomous broker removal without user interaction

---

# PART B — Pre-Sprint 10 Setup

Run these commands from the DigiZafe repository root:

```bash
# Confirm Sprint 9 frontend is available
cd frontend
npm install
npm run build

# Return to repository root
cd ..

# Create Sprint 10 directories
mkdir -p frontend/src/components/creative
mkdir -p frontend/src/features/remediation
mkdir -p frontend/src/features/privacy
mkdir -p frontend/src/features/onboarding

# Verify backend is running
curl -s http://localhost:8000/api/v1/health | jq .

echo "✅ Sprint 10 frontend directories created."
```

No new npm dependencies are required. Sprint 10 uses the existing:

- React
- TypeScript
- TanStack Query
- React Router
- Recharts
- Lucide
- Tailwind
- Radix-style components

---

# PART C — Sprint 10 File Contents

## 1. UPDATE: `.env.example`

Append:

```bash
# === Sprint 10: Creative Frontend + Remediation UX ===
VITE_ONBOARDING_ENABLED=true
VITE_DEFAULT_APP_ROUTE=/app/onboarding
VITE_REDUCED_MOTION_DEFAULT=false
VITE_PRIVACY_CENTER_ENABLED=true
VITE_REMEDIATION_CONSOLE_ENABLED=true
```

Update `frontend/.env`:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_NAME=DigiZafe
VITE_SSE_USE_FETCH=true
VITE_XPOSEDORNOT_ATTRIBUTION=Breach data: XposedOrNot (https://xposedornot.com)

VITE_ONBOARDING_ENABLED=true
VITE_DEFAULT_APP_ROUTE=/app/onboarding
VITE_REDUCED_MOTION_DEFAULT=false
VITE_PRIVACY_CENTER_ENABLED=true
VITE_REMEDIATION_CONSOLE_ENABLED=true
```

---

## 2. UPDATE: `frontend/src/lib/auth-store.ts`

Sprint 10 intentionally removes `sessionStorage`. Tokens remain in memory only.

```typescript
import { create } from "zustand";
import type { UserPublic } from "./types";

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
    set({
      accessToken: access,
      refreshToken: refresh,
    });
  },

  setUser: (user) => set({ user }),

  clear: () =>
    set({
      accessToken: null,
      refreshToken: null,
      user: null,
    }),

  hydrateFromSession: () => {
    // Intentionally empty.
    // Sprint 10 does not persist tokens in localStorage or sessionStorage.
  },
}));

export function getRefreshFromSession(): string | null {
  // Retained for API compatibility with Sprint 9.
  // No browser storage is used.
  return useAuthStore.getState().refreshToken;
}
```

---

## 3. UPDATE: `frontend/src/lib/types.ts`

Append these interfaces to the existing file:

```typescript
export interface BrokerCatalogItem {
  id: string;
  name: string;
  method: string;
  legality: string;
  opt_out_url: string;
  requires_captcha: boolean;
  requires_email_confirm: boolean;
  form_field_map?: Record<string, string>;
  success_hints?: string[];
  enabled?: boolean;
  notes?: string;
}

export interface BrokerStatePublic {
  id: string;
  broker_id: string;
  broker_name: string;
  status: string;
  last_success_at?: string | null;
  last_attempt_at?: string | null;
  last_verified_at?: string | null;
  total_runs: number;
  detail?: string | null;
  meta?: Record<string, unknown> | null;
  updated_at: string;
}

export interface RemediationJobItem {
  id: string;
  broker_id: string;
  broker_name: string;
  status: string;
  skip_reason?: string | null;
  error?: string | null;
  detail?: string | null;
  result_meta?: Record<string, unknown> | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface RemediationJob {
  id: string;
  identifier_id?: string | null;
  job_type: string;
  status: string;
  dry_run: boolean;
  broker_ids?: string[] | null;
  progress_pct: number;
  message?: string | null;
  error?: string | null;
  result_summary?: Record<string, unknown> | null;
  deadline_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  items: RemediationJobItem[];
}

export interface CaptchaQueueItem {
  id: string;
  job_id: string;
  broker_id: string;
  status: string;
  page_url?: string | null;
  captcha_type: string;
  instructions?: string | null;
  expires_at: string;
  created_at: string;
}

export interface FreezeChecklistItem {
  id: string;
  target_id: string;
  label: string;
  url: string;
  status: string;
  notes?: string | null;
  completed_at?: string | null;
}

export interface GeneratedRequest {
  id: string;
  kind: string;
  regime: string;
  recipient_name?: string | null;
  recipient_email?: string | null;
  subject: string;
  body: string;
  status: string;
  deadline_at?: string | null;
  sent_at?: string | null;
  created_at: string;
}

export interface ConsentItem {
  id?: string | null;
  purpose: string;
  scope?: string | null;
  granted: boolean;
  created_at?: string | null;
  revoked_at?: string | null;
  details?: Record<string, unknown> | null;
}

export interface AuditEvent {
  id: string;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  details?: Record<string, unknown> | null;
  created_at: string;
  correlation_id?: string | null;
}

export interface EgressEvent {
  id: string;
  purpose: string;
  destination_host: string;
  method: string;
  status_code?: number | null;
  success: boolean;
  summary?: Record<string, unknown> | null;
  created_at: string;
}

export interface ExportJob {
  id: string;
  status: string;
  include_audit: boolean;
  include_egress: boolean;
  size_bytes: number;
  expires_at: string;
  created_at: string;
  ready_at?: string | null;
  error?: string | null;
}

export interface ExportPackageResponse {
  job: ExportJob;
  package?: Record<string, unknown> | null;
}

export interface NarrativeBriefing {
  id?: string | null;
  score_snapshot_id?: string | null;
  identifier_id?: string | null;
  mode: string;
  model_name?: string | null;
  title: string;
  body_markdown: string;
  grounded: boolean;
  facts_used?: Record<string, unknown> | null;
  created_at?: string | null;
}

export interface CounterfactualResponse {
  score_snapshot_id?: string | null;
  counterfactuals: Counterfactual[];
  explanation_summary: string;
  vector?: string | null;
  score_combined?: number | null;
}

export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  complete: boolean;
  href: string;
}
```

---

## 4. NEW: `frontend/src/hooks/useReducedMotion.ts`

```typescript
import { useEffect, useState } from "react";

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");

    const update = () => setReduced(media.matches);

    update();
    media.addEventListener("change", update);

    return () => media.removeEventListener("change", update);
  }, []);

  return reduced;
}
```

---

## 5. UPDATE: `frontend/src/styles/index.css`

Replace the existing file with:

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

  html {
    scroll-behavior: smooth;
  }

  body {
    @apply bg-background text-foreground;
  }

  :focus-visible {
    @apply outline-none ring-2 ring-ring ring-offset-2 ring-offset-background;
  }

  button,
  a,
  input,
  select,
  textarea {
    min-height: 2.5rem;
  }
}

@layer utilities {
  .text-balance {
    text-wrap: balance;
  }

  .glass-panel {
    @apply border border-white/10 bg-white/[0.03] shadow-2xl shadow-cyan-950/20 backdrop-blur-xl;
  }

  .gradient-border {
    position: relative;
    isolation: isolate;
  }

  .gradient-border::before {
    content: "";
    position: absolute;
    inset: -1px;
    z-index: -1;
    border-radius: inherit;
    background: linear-gradient(
      135deg,
      rgba(34, 211, 238, 0.6),
      rgba(59, 130, 246, 0.15),
      rgba(168, 85, 247, 0.45)
    );
    opacity: 0.75;
  }

  .status-dot {
    @apply h-2 w-2 rounded-full bg-current;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.001ms !important;
  }
}
```

---

# PART D — Creative Components

## 6. NEW: `frontend/src/components/creative/RiskAutopsy.tsx`

```tsx
import { useMemo } from "react";
import { ArrowDown, ArrowRight, CircleAlert, ShieldCheck } from "lucide-react";
import type { ScorePublic } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { severityBg } from "@/lib/utils";

interface RiskAutopsyProps {
  score: ScorePublic;
}

export function RiskAutopsy({ score }: RiskAutopsyProps) {
  const contributions = useMemo(
    () =>
      [...(score.contributions || [])]
        .sort((a, b) => b.weighted_score - a.weighted_score)
        .slice(0, 6),
    [score.contributions]
  );

  return (
    <Card className="glass-panel gradient-border overflow-hidden">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <CircleAlert className="h-5 w-5 text-cyan-300" />
              Risk autopsy
            </CardTitle>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              A transparent explanation of how your exposure signals combine into the current PDSS.
            </p>
          </div>

          <Badge className={severityBg(score.severity)}>
            {score.severity}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-4">
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              Signal
            </div>
            <div className="mt-2 text-lg font-semibold">
              {score.finding_count} findings
            </div>
            <div className="text-xs text-muted-foreground">
              Confirmed {score.score_confirmed.toFixed(1)}
            </div>
          </div>

          <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-4">
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              Amplifiers
            </div>
            <div className="mt-2 text-lg font-semibold">
              {Number(score.metrics?.E || 0).toFixed(2)} E
            </div>
            <div className="text-xs text-muted-foreground">
              Environmental context
            </div>
          </div>

          <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-4">
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              Outcome
            </div>
            <div className="mt-2 text-lg font-semibold">
              {score.score_combined.toFixed(1)} / 10
            </div>
            <div className="text-xs text-muted-foreground">
              Combined PDSS
            </div>
          </div>
        </div>

        <div className="flex flex-col items-center gap-2 md:flex-row md:justify-center">
          <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/5 px-4 py-3 text-center">
            <div className="text-xs text-muted-foreground">Observed signals</div>
            <div className="font-semibold">Findings</div>
          </div>

          <ArrowRight className="hidden h-5 w-5 text-muted-foreground md:block" />
          <ArrowDown className="h-5 w-5 text-muted-foreground md:hidden" />

          <div className="rounded-xl border border-violet-400/20 bg-violet-400/5 px-4 py-3 text-center">
            <div className="text-xs text-muted-foreground">Risk mechanics</div>
            <div className="font-semibold">S · D · L · I · T · E · U</div>
          </div>

          <ArrowRight className="hidden h-5 w-5 text-muted-foreground md:block" />
          <ArrowDown className="h-5 w-5 text-muted-foreground md:hidden" />

          <div className="rounded-xl border border-rose-400/20 bg-rose-400/5 px-4 py-3 text-center">
            <div className="text-xs text-muted-foreground">Decision</div>
            <div className="font-semibold">PDSS {score.score_combined.toFixed(1)}</div>
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-semibold">Top drivers</h3>

          {contributions.length === 0 && (
            <div className="flex items-center gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-4 text-sm text-emerald-200">
              <ShieldCheck className="h-4 w-4" />
              No active finding contributions are currently recorded.
            </div>
          )}

          {contributions.map((contribution, index) => {
            const width = Math.min(100, Math.max(8, contribution.weighted_score * 10));

            return (
              <div key={contribution.finding_id} className="rounded-lg border p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs text-muted-foreground">#{index + 1}</span>
                      <span className="truncate font-medium">{contribution.title}</span>
                      <Badge variant="outline">{contribution.source}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {contribution.vector_fragment}
                    </p>
                  </div>

                  <span className="shrink-0 font-mono text-sm">
                    {contribution.weighted_score.toFixed(2)}
                  </span>
                </div>

                <div className="mt-3 h-2 overflow-hidden rounded-full bg-secondary">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-blue-500 to-violet-500 transition-all"
                    style={{ width: `${width}%` }}
                    aria-label={`${contribution.weighted_score.toFixed(2)} weighted contribution`}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div className="rounded-lg border border-white/10 bg-black/10 p-4 text-sm text-muted-foreground">
          <strong className="text-foreground">Interpretation:</strong>{" "}
          {score.explanation_summary}
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## 7. NEW: `frontend/src/components/creative/WhatIfSimulator.tsx`

```tsx
import { useMemo, useState } from "react";
import { ArrowDownRight, FlaskConical, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import type { Counterfactual, FindingPublic, ScorePublic } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { severityBg } from "@/lib/utils";

interface WhatIfSimulatorProps {
  score: ScorePublic;
  findings: FindingPublic[];
  identifierId?: string;
}

export function WhatIfSimulator({
  score,
  findings,
  identifierId,
}: WhatIfSimulatorProps) {
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<ScorePublic | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openFindings = useMemo(
    () => findings.filter((finding) => finding.status === "open"),
    [findings]
  );

  const toggle = (id: string) => {
    setSelected((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    );
  };

  const runSimulation = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await api.post<ScorePublic>("/scores/whatif", {
        identifier_id: identifierId,
        exclude_finding_ids: selected,
        exclude_sources: [],
        exclude_kinds: [],
      });

      setResult(data);
    } catch (err) {
      setError((err as Error).message || "Unable to run simulation");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setSelected([]);
    setResult(null);
    setError(null);
  };

  const after = result?.score_combined ?? score.score_combined;
  const delta = after - score.score_combined;

  return (
    <Card className="glass-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-violet-300" />
          What-if simulator
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Select findings you intend to remediate and preview the estimated score change.
          This does not modify findings.
        </p>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid gap-2">
          {openFindings.slice(0, 20).map((finding) => {
            const checked = selected.includes(finding.id);

            return (
              <label
                key={finding.id}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                  checked ? "border-primary bg-primary/10" : "hover:bg-accent/40"
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggle(finding.id)}
                  className="mt-1 h-4 w-4 accent-cyan-400"
                />

                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="truncate text-sm font-medium">{finding.title}</span>
                    <Badge variant="outline">{finding.source}</Badge>
                    <Badge className={severityBg(finding.severity_hint)}>
                      {finding.severity_hint}
                    </Badge>
                  </span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    {finding.summary}
                  </span>
                </span>
              </label>
            );
          })}

          {openFindings.length === 0 && (
            <p className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-4 text-sm text-emerald-200">
              There are no open findings available for simulation.
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            onClick={runSimulation}
            disabled={loading || selected.length === 0}
          >
            {loading ? "Simulating…" : `Simulate ${selected.length} change${selected.length === 1 ? "" : "s"}`}
          </Button>

          <Button variant="ghost" onClick={reset}>
            <RotateCcw className="h-4 w-4" />
            Reset
          </Button>
        </div>

        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}

        {result && (
          <div className="rounded-xl border border-violet-400/30 bg-violet-400/5 p-4">
            <div className="flex flex-wrap items-center gap-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Current
                </div>
                <div className="text-2xl font-bold">
                  {score.score_combined.toFixed(1)}
                </div>
              </div>

              <ArrowDownRight className="h-5 w-5 text-emerald-300" />

              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Estimated
                </div>
                <div className="text-2xl font-bold">
                  {result.score_combined.toFixed(1)}
                </div>
              </div>

              <Badge className={delta <= 0 ? "bg-emerald-500/20 text-emerald-200" : "bg-rose-500/20 text-rose-200"}>
                Δ {delta >= 0 ? "+" : ""}
                {delta.toFixed(1)}
              </Badge>
            </div>

            <p className="mt-3 text-sm text-muted-foreground">
              {delta <= 0
                ? "The selected remediation actions are estimated to reduce exposure."
                : "The simulation did not reduce the score. Review the selected findings and current model inputs."}
            </p>
          </div>
        )}

        {(score.counterfactuals || []).length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Model-generated counterfactuals</h3>
            {(score.counterfactuals as Counterfactual[]).slice(0, 3).map((item, index) => (
              <p key={index} className="rounded-lg border p-3 text-sm text-muted-foreground">
                {item.narrative || JSON.stringify(item)}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

---

## 8. NEW: `frontend/src/components/creative/NarrativeBriefing.tsx`

```tsx
import { useState } from "react";
import { BookOpenText, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { NarrativeBriefing } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface NarrativeBriefingProps {
  identifierId?: string;
}

export function NarrativeBriefing({ identifierId }: NarrativeBriefingProps) {
  const [briefing, setBriefing] = useState<NarrativeBriefing | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.post<NarrativeBriefing>("/privacy/narrative", {
        identifier_id: identifierId,
        prefer_ollama: true,
        persist: true,
      });

      setBriefing(result);
    } catch (err) {
      setError((err as Error).message || "Unable to generate briefing");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="glass-panel">
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BookOpenText className="h-5 w-5 text-cyan-300" />
              Grounded narrative briefing
            </CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              A calm, human-readable explanation based only on stored DigiZafe facts.
            </p>
          </div>

          <Button onClick={generate} disabled={loading} variant="secondary">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Writing…" : "Generate briefing"}
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}

        {!briefing && !loading && !error && (
          <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-5 text-sm text-muted-foreground">
            Generate a briefing after computing PDSS. The backend uses a grounded provider when
            available and falls back to a deterministic explanation.
          </div>
        )}

        {briefing && (
          <article className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold">{briefing.title}</h3>
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-1 text-xs text-emerald-200">
                <ShieldCheck className="h-3 w-3" />
                Grounded
              </span>
              <span className="rounded-full border px-2 py-1 text-xs text-muted-foreground">
                {briefing.mode}
              </span>
            </div>

            <div
              className="whitespace-pre-wrap rounded-xl border bg-black/10 p-5 text-sm leading-7 text-slate-200"
              aria-live="polite"
            >
              {briefing.body_markdown}
            </div>

            {briefing.created_at && (
              <p className="text-xs text-muted-foreground">
                Generated {new Date(briefing.created_at).toLocaleString()}
              </p>
            )}
          </article>
        )}
      </CardContent>
    </Card>
  );
}
```

---

# PART E — Remediation API Hooks

## 9. NEW: `frontend/src/features/remediation/api.ts`

```typescript
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  BrokerCatalogItem,
  BrokerStatePublic,
  CaptchaQueueItem,
  FreezeChecklistItem,
  GeneratedRequest,
  RemediationJob,
} from "@/lib/types";

export function useBrokerCatalog() {
  return useQuery({
    queryKey: ["remediation", "brokers"],
    queryFn: () =>
      api.get<{
        brokers: BrokerCatalogItem[];
        attribution: string;
      }>("/remediation/brokers"),
  });
}

export function useBrokerStates() {
  return useQuery({
    queryKey: ["remediation", "state"],
    queryFn: () => api.get<BrokerStatePublic[]>("/remediation/state"),
  });
}

export function useRemediationJobs() {
  return useQuery({
    queryKey: ["remediation", "jobs"],
    queryFn: () => api.get<RemediationJob[]>("/remediation/jobs"),
    refetchInterval: 5000,
  });
}

export function useRemediationJob(jobId?: string) {
  return useQuery({
    queryKey: ["remediation", "jobs", jobId],
    enabled: !!jobId,
    queryFn: () => api.get<RemediationJob>(`/remediation/jobs/${jobId}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (
        status &&
        ["completed", "partial", "failed", "cancelled", "timed_out"].includes(status)
      ) {
        return false;
      }
      return 5000;
    },
  });
}

export function useStartBrokerOptOut() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      identifier_id: string;
      broker_ids?: string[];
      dry_run: boolean;
      profile?: {
        display_name?: string;
        state?: string;
        city?: string;
        zip?: string;
      };
    }) =>
      api.post<RemediationJob>("/remediation/jobs/broker-optout", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation"] });
    },
  });
}

export function useCancelRemediationJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) =>
      api.post<RemediationJob>(`/remediation/jobs/${jobId}/cancel`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation"] });
    },
  });
}

export function useCaptchaQueue() {
  return useQuery({
    queryKey: ["remediation", "captcha"],
    queryFn: () => api.get<CaptchaQueueItem[]>("/remediation/captcha"),
    refetchInterval: 5000,
  });
}

export function useSolveCaptcha() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      action,
      solution_token,
    }: {
      id: string;
      action: "solve" | "skip" | "manual_done";
      solution_token?: string;
    }) =>
      api.post(`/remediation/captcha/${id}`, {
        action,
        solution_token,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation"] });
    },
  });
}

export function useFreezeChecklist() {
  return useQuery({
    queryKey: ["remediation", "freeze"],
    queryFn: () => api.get<FreezeChecklistItem[]>("/remediation/freeze"),
  });
}

export function useUpdateFreezeItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      status,
      notes,
    }: {
      id: string;
      status: string;
      notes?: string;
    }) =>
      api.patch<FreezeChecklistItem>(`/remediation/freeze/${id}`, {
        status,
        notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation", "freeze"] });
    },
  });
}

export function useGeneratedRequests() {
  return useQuery({
    queryKey: ["remediation", "requests"],
    queryFn: () => api.get<GeneratedRequest[]>("/remediation/requests"),
  });
}

export function useCreateKnowRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      regime: "ccpa" | "gdpr" | "other";
      recipient_name: string;
      recipient_email?: string;
      identifier_id?: string;
      include_deletion: boolean;
    }) => api.post<GeneratedRequest>("/remediation/know", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation", "requests"] });
    },
  });
}

export function useCreateComplaint() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      regime: "ccpa" | "gdpr" | "other";
      recipient_name: string;
      regulator: string;
      facts: string;
    }) => api.post<GeneratedRequest>("/remediation/complaints", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation", "requests"] });
    },
  });
}

export function useMarkRequestSent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      api.post<GeneratedRequest>(`/remediation/requests/${id}/mark-sent`, {
        sent: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation", "requests"] });
    },
  });
}

export function useVerifyBrokers() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (broker_ids?: string[]) =>
      api.post("/remediation/verify", { broker_ids }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation"] });
    },
  });
}
```

---

# PART F — Privacy API Hooks

## 10. NEW: `frontend/src/features/privacy/api.ts`

```typescript
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  AuditEvent,
  ConsentItem,
  EgressEvent,
  ExportJob,
  ExportPackageResponse,
} from "@/lib/types";

export function useConsent() {
  return useQuery({
    queryKey: ["privacy", "consent"],
    queryFn: () => api.get<ConsentItem[]>("/privacy/consent"),
  });
}

export function useGrantConsent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      purpose: string;
      scope?: string;
      details?: Record<string, unknown>;
    }) => api.post("/privacy/consent", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["privacy", "consent"] });
    },
  });
}

export function useRevokeConsent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (purpose: string) =>
      api.post("/privacy/consent/revoke", { purpose }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["privacy", "consent"] });
    },
  });
}

export function useAuditEvents() {
  return useQuery({
    queryKey: ["privacy", "audit"],
    queryFn: () => api.get<AuditEvent[]>("/privacy/audit?limit=100"),
  });
}

export function useEgressEvents() {
  return useQuery({
    queryKey: ["privacy", "egress"],
    queryFn: () => api.get<EgressEvent[]>("/privacy/egress?limit=100"),
  });
}

export function useCreateExport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      include_audit: boolean;
      include_egress: boolean;
    }) => api.post<ExportJob>("/privacy/export", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["privacy", "exports"] });
    },
  });
}

export function useExportPackage(exportId?: string) {
  return useQuery({
    queryKey: ["privacy", "exports", exportId],
    enabled: !!exportId,
    queryFn: () =>
      api.get<ExportPackageResponse>(`/privacy/export/${exportId}`),
  });
}

export function useRequestAccountDeletion() {
  return useMutation({
    mutationFn: (body: {
      confirm_phrase: string;
      immediate: boolean;
    }) =>
      api.post("/privacy/account/delete", body),
  });
}
```

---

# PART G — Remediation Console

## 11. NEW: `frontend/src/features/remediation/RemediationPage.tsx`

```tsx
import { useMemo, useState } from "react";
import {
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  FileText,
  KeyRound,
  Loader2,
  ShieldAlert,
  UserRoundCog,
} from "lucide-react";
import { useIdentifiers } from "@/features/identifiers/api";
import {
  useBrokerCatalog,
  useBrokerStates,
  useCaptchaQueue,
  useCancelRemediationJob,
  useCreateComplaint,
  useCreateKnowRequest,
  useFreezeChecklist,
  useGeneratedRequests,
  useMarkRequestSent,
  useRemediationJobs,
  useSolveCaptcha,
  useStartBrokerOptOut,
  useUpdateFreezeItem,
  useVerifyBrokers,
} from "./api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { formatDate } from "@/lib/utils";

export function RemediationPage() {
  const identifiers = useIdentifiers();
  const catalog = useBrokerCatalog();
  const states = useBrokerStates();
  const jobs = useRemediationJobs();
  const captcha = useCaptchaQueue();
  const freeze = useFreezeChecklist();
  const requests = useGeneratedRequests();

  const startJob = useStartBrokerOptOut();
  const cancelJob = useCancelRemediationJob();
  const solveCaptcha = useSolveCaptcha();
  const updateFreeze = useUpdateFreezeItem();
  const verify = useVerifyBrokers();
  const createKnow = useCreateKnowRequest();
  const createComplaint = useCreateComplaint();
  const markSent = useMarkRequestSent();

  const verifiedEmails = useMemo(
    () =>
      (identifiers.data || []).filter(
        (item) => item.is_verified && item.type === "email"
      ),
    [identifiers.data]
  );

  const [identifierId, setIdentifierId] = useState("");
  const [selectedBrokers, setSelectedBrokers] = useState<string[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [state, setState] = useState("");
  const [city, setCity] = useState("");
  const [zip, setZip] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  const [knowRecipient, setKnowRecipient] = useState("");
  const [knowEmail, setKnowEmail] = useState("");
  const [complaintRecipient, setComplaintRecipient] = useState("");
  const [complaintFacts, setComplaintFacts] = useState("");

  const brokers = catalog.data?.brokers || [];

  const toggleBroker = (id: string) => {
    setSelectedBrokers((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    );
  };

  const startOptOut = async () => {
    if (!identifierId) {
      setMessage("Select a verified email before starting remediation.");
      return;
    }

    try {
      await startJob.mutateAsync({
        identifier_id: identifierId,
        broker_ids: selectedBrokers.length ? selectedBrokers : undefined,
        dry_run: dryRun,
        profile: {
          display_name: displayName || undefined,
          state: state || undefined,
          city: city || undefined,
          zip: zip || undefined,
        },
      });

      setMessage(
        dryRun
          ? "Dry-run remediation job queued. No forms will be submitted."
          : "Remediation job queued in the worker."
      );
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <div className="space-y-8">
      <header>
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-cyan-400/10 p-3">
            <UserRoundCog className="h-6 w-6 text-cyan-300" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold">Remediation console</h1>
            <p className="text-muted-foreground">
              Guided and Green-broker remediation with explicit user control.
            </p>
          </div>
        </div>
      </header>

      <Card className="glass-panel gradient-border">
        <CardHeader>
          <CardTitle>Start Green broker opt-out</CardTitle>
          <CardDescription>
            Playwright runs only in the remediation worker. CAPTCHA and manual steps remain user-in-loop.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="remediation-identifier">Verified email</Label>
              <select
                id="remediation-identifier"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={identifierId}
                onChange={(event) => setIdentifierId(event.target.value)}
              >
                <option value="">Select verified email…</option>
                {verifiedEmails.map((identifier) => (
                  <option key={identifier.id} value={identifier.id}>
                    {identifier.value_display}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="display-name">Name for forms</Label>
              <Input
                id="display-name"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder="Optional"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="state">State</Label>
              <Input
                id="state"
                value={state}
                onChange={(event) => setState(event.target.value)}
                placeholder="Optional, e.g. CA"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="city">City</Label>
              <Input
                id="city"
                value={city}
                onChange={(event) => setCity(event.target.value)}
                placeholder="Optional"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="zip">ZIP code</Label>
              <Input
                id="zip"
                value={zip}
                onChange={(event) => setZip(event.target.value)}
                placeholder="Optional"
              />
            </div>
          </div>

          <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-4">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(event) => setDryRun(event.target.checked)}
                className="mt-1 h-4 w-4 accent-amber-400"
              />
              <span>
                <span className="block font-medium">Dry-run preview</span>
                <span className="block text-sm text-muted-foreground">
                  Fill forms without submitting them. Recommended for the first run.
                </span>
              </span>
            </label>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">Green brokers</h3>
              <Button
                size="sm"
                variant="ghost"
                onClick={() =>
                  setSelectedBrokers(
                    selectedBrokers.length
                      ? []
                      : brokers.map((broker) => broker.id)
                  )
                }
              >
                {selectedBrokers.length ? "Clear selection" : "Select all"}
              </Button>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              {brokers.map((broker) => (
                <label
                  key={broker.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 ${
                    selectedBrokers.includes(broker.id)
                      ? "border-primary bg-primary/10"
                      : "hover:bg-accent/40"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedBrokers.includes(broker.id)}
                    onChange={() => toggleBroker(broker.id)}
                    className="mt-1 h-4 w-4 accent-cyan-400"
                  />

                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{broker.name}</span>
                      {broker.requires_captcha && (
                        <Badge variant="secondary">CAPTCHA</Badge>
                      )}
                      {broker.method === "manual" && (
                        <Badge variant="outline">manual</Badge>
                      )}
                    </span>
                    {broker.notes && (
                      <span className="mt-1 block text-xs text-muted-foreground">
                        {broker.notes}
                      </span>
                    )}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={startOptOut} disabled={startJob.isPending}>
              {startJob.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {dryRun ? "Preview opt-out" : "Start opt-out"}
            </Button>

            <Button
              variant="secondary"
              onClick={() => verify.mutate(undefined)}
              disabled={verify.isPending}
            >
              <ShieldAlert className="h-4 w-4" />
              Verify previous removals
            </Button>

            {message && (
              <span className="text-sm text-muted-foreground" role="status">
                {message}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      <section className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Active and previous jobs</CardTitle>
            <CardDescription>
              Worker progress and honest status for each broker.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-3">
            {(jobs.data || []).map((job) => (
              <div key={job.id} className="rounded-lg border p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ClipboardList className="h-4 w-4 text-cyan-300" />
                    <span className="font-medium">{job.job_type}</span>
                    <Badge variant="outline">{job.status}</Badge>
                    {job.dry_run && <Badge variant="secondary">dry-run</Badge>}
                  </div>

                  {!["completed", "partial", "failed", "cancelled", "timed_out"].includes(
                    job.status
                  ) && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => cancelJob.mutate(job.id)}
                    >
                      Cancel
                    </Button>
                  )}
                </div>

                <div className="mt-3 space-y-2">
                  <Progress value={job.progress_pct} />
                  <p className="text-xs text-muted-foreground">
                    {job.progress_pct.toFixed(0)}% · {job.message || "—"}
                  </p>
                </div>

                <div className="mt-3 space-y-1">
                  {job.items?.map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded border px-3 py-2 text-sm"
                    >
                      <span>{item.broker_name}</span>
                      <span className="text-xs text-muted-foreground">
                        {item.status}
                        {item.skip_reason ? ` · ${item.skip_reason}` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {!jobs.isLoading && !(jobs.data || []).length && (
              <p className="text-sm text-muted-foreground">
                No remediation jobs yet.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Broker state</CardTitle>
            <CardDescription>
              AIDR-inspired durable state with fresh-result skipping.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-2">
            {(states.data || []).map((stateRow) => (
              <div
                key={stateRow.id}
                className="flex items-center justify-between gap-3 rounded-lg border p-3"
              >
                <div className="min-w-0">
                  <div className="truncate font-medium">{stateRow.broker_name}</div>
                  <div className="text-xs text-muted-foreground">
                    {stateRow.detail || "No detail recorded"}
                  </div>
                </div>
                <Badge variant="outline">{stateRow.status}</Badge>
              </div>
            ))}

            {!states.isLoading && !(states.data || []).length && (
              <p className="text-sm text-muted-foreground">
                No broker state recorded yet.
              </p>
            )}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-amber-300" />
            CAPTCHA and manual queue
          </CardTitle>
          <CardDescription>
            DigiZafe does not require CapSolver. Complete the step manually and resume the job.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-3">
          {(captcha.data || []).map((item) => (
            <div key={item.id} className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-medium">{item.broker_id}</div>
                  <div className="text-xs text-muted-foreground">
                    {item.captcha_type} · expires {formatDate(item.expires_at)}
                  </div>
                </div>

                {item.page_url && (
                  <a
                    href={item.page_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                  >
                    Open page <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>

              <p className="mt-2 text-sm text-muted-foreground">
                {item.instructions || "Complete the manual step in your browser."}
              </p>

              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() =>
                    solveCaptcha.mutate({
                      id: item.id,
                      action: "manual_done",
                    })
                  }
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Mark complete
                </Button>

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    solveCaptcha.mutate({
                      id: item.id,
                      action: "skip",
                    })
                  }
                >
                  Skip
                </Button>
              </div>
            </div>
          ))}

          {!captcha.isLoading && !(captcha.data || []).length && (
            <p className="text-sm text-muted-foreground">
              No CAPTCHA tasks are waiting.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Credit and security freeze checklist</CardTitle>
          <CardDescription>
            Guided user-in-loop actions inspired by AIDR freeze targets.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-2">
          {(freeze.data || []).map((item) => (
            <div
              key={item.id}
              className="flex flex-col gap-3 rounded-lg border p-3 md:flex-row md:items-center md:justify-between"
            >
              <div>
                <div className="font-medium">{item.label}</div>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  Open official page <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              <select
                className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={item.status}
                onChange={(event) =>
                  updateFreeze.mutate({
                    id: item.id,
                    status: event.target.value,
                  })
                }
              >
                <option value="todo">To do</option>
                <option value="in_progress">In progress</option>
                <option value="done">Done</option>
                <option value="skipped">Skipped</option>
              </select>
            </div>
          ))}
        </CardContent>
      </Card>

      <section className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-cyan-300" />
              Generate right-to-know request
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label>Recipient</Label>
              <Input
                value={knowRecipient}
                onChange={(event) => setKnowRecipient(event.target.value)}
                placeholder="Data broker or company"
              />
            </div>

            <div className="space-y-1">
              <Label>Recipient email</Label>
              <Input
                value={knowEmail}
                onChange={(event) => setKnowEmail(event.target.value)}
                placeholder="Optional"
                type="email"
              />
            </div>

            <Button
              onClick={() =>
                createKnow.mutate({
                  regime: "ccpa",
                  recipient_name: knowRecipient,
                  recipient_email: knowEmail || undefined,
                  identifier_id: identifierId || undefined,
                  include_deletion: true,
                })
              }
              disabled={!knowRecipient || createKnow.isPending}
            >
              Generate draft
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Generate complaint draft</CardTitle>
          </CardHeader>

          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label>Business or broker</Label>
              <Input
                value={complaintRecipient}
                onChange={(event) => setComplaintRecipient(event.target.value)}
                placeholder="Recipient"
              />
            </div>

            <div className="space-y-1">
              <Label>Facts</Label>
              <textarea
                className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={complaintFacts}
                onChange={(event) => setComplaintFacts(event.target.value)}
                placeholder="Describe what happened…"
              />
            </div>

            <Button
              onClick={() =>
                createComplaint.mutate({
                  regime: "ccpa",
                  recipient_name: complaintRecipient,
                  regulator: "ca_ag",
                  facts: complaintFacts,
                })
              }
              disabled={
                !complaintRecipient ||
                complaintFacts.length < 10 ||
                createComplaint.isPending
              }
            >
              Generate complaint
            </Button>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Generated request drafts</CardTitle>
        </CardHeader>

        <CardContent className="space-y-3">
          {(requests.data || []).map((request) => (
            <details key={request.id} className="rounded-lg border p-4">
              <summary className="cursor-pointer font-medium">
                {request.subject}
              </summary>

              <div className="mt-3 space-y-3">
                <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                  {request.body}
                </p>

                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">{request.kind}</Badge>
                  <Badge variant="secondary">{request.status}</Badge>
                  {request.status !== "sent_marked" && (
                    <Button
                      size="sm"
                      onClick={() => markSent.mutate(request.id)}
                    >
                      Mark sent
                    </Button>
                  )}
                </div>
              </div>
            </details>
          ))}

          {!requests.isLoading && !(requests.data || []).length && (
            <p className="text-sm text-muted-foreground">
              No generated requests yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

---

# PART H — Privacy Center

## 12. NEW: `frontend/src/features/privacy/PrivacyPage.tsx`

```tsx
import { useState } from "react";
import {
  Download,
  Eye,
  KeyRound,
  LockKeyhole,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import {
  useAuditEvents,
  useConsent,
  useCreateExport,
  useEgressEvents,
  useExportPackage,
  useGrantConsent,
  useRequestAccountDeletion,
  useRevokeConsent,
} from "./api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatDate } from "@/lib/utils";

export function PrivacyPage() {
  const consent = useConsent();
  const audit = useAuditEvents();
  const egress = useEgressEvents();

  const createExport = useCreateExport();
  const exportPackage = useExportPackage(createExport.data?.id);
  const grant = useGrantConsent();
  const revoke = useRevokeConsent();
  const deletion = useRequestAccountDeletion();

  const [purpose, setPurpose] = useState("discovery.xposedornot");
  const [scope, setScope] = useState("");
  const [confirmPhrase, setConfirmPhrase] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const startExport = async () => {
    try {
      await createExport.mutateAsync({
        include_audit: true,
        include_egress: true,
      });
      setMessage("Export package created.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const downloadExport = () => {
    const packageData = exportPackage.data?.package;
    if (!packageData) return;

    const blob = new Blob([JSON.stringify(packageData, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "digizafe-data-export.json";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const requestDeletion = async () => {
    const confirmed = window.confirm(
      "This will schedule account deletion and crypto-shred. Continue?"
    );

    if (!confirmed) return;

    try {
      await deletion.mutateAsync({
        confirm_phrase: confirmPhrase,
        immediate: false,
      });
      setMessage("Account deletion scheduled.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <div className="space-y-8">
      <header>
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-violet-400/10 p-3">
            <LockKeyhole className="h-6 w-6 text-violet-300" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold">Privacy center</h1>
            <p className="text-muted-foreground">
              Export, inspect, control, and delete your DigiZafe data.
            </p>
          </div>
        </div>
      </header>

      {message && (
        <div
          className="rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-4 text-sm"
          role="status"
        >
          {message}
        </div>
      )}

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="h-5 w-5 text-cyan-300" />
              Data export
            </CardTitle>
            <CardDescription>
              Create a machine-readable export of your DigiZafe records.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <Button onClick={startExport} disabled={createExport.isPending}>
              {createExport.isPending ? "Preparing…" : "Create export"}
            </Button>

            {createExport.data && (
              <div className="rounded-lg border p-4 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">{createExport.data.status}</Badge>
                  <span className="text-muted-foreground">
                    {createExport.data.size_bytes.toLocaleString()} bytes
                  </span>
                </div>

                {exportPackage.data?.package && (
                  <Button className="mt-3" variant="secondary" onClick={downloadExport}>
                    Download JSON
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-rose-300" />
              Account deletion
            </CardTitle>
            <CardDescription>
              Deletion schedules crypto-shred and purge. The grace period allows cancellation.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-3">
            <Label htmlFor="delete-phrase">Confirmation phrase</Label>
            <Input
              id="delete-phrase"
              value={confirmPhrase}
              onChange={(event) => setConfirmPhrase(event.target.value)}
              placeholder="DELETE MY DIGIZAFE ACCOUNT"
            />

            <Button
              variant="destructive"
              onClick={requestDeletion}
              disabled={!confirmPhrase || deletion.isPending}
            >
              Schedule account deletion
            </Button>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-amber-300" />
            Consent center
          </CardTitle>
          <CardDescription>
            Review which external processing purposes have been granted or revoked.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
            <Input
              value={purpose}
              onChange={(event) => setPurpose(event.target.value)}
              placeholder="discovery.xposedornot"
            />
            <Input
              value={scope}
              onChange={(event) => setScope(event.target.value)}
              placeholder="Optional scope"
            />
            <Button
              onClick={() =>
                grant.mutate({
                  purpose,
                  scope: scope || undefined,
                })
              }
              disabled={!purpose || grant.isPending}
            >
              Grant
            </Button>
          </div>

          <div className="space-y-2">
            {(consent.data || []).map((item) => (
              <div
                key={`${item.id || item.purpose}-${item.created_at}`}
                className="flex flex-col gap-3 rounded-lg border p-3 md:flex-row md:items-center md:justify-between"
              >
                <div>
                  <div className="font-medium">{item.purpose}</div>
                  <div className="text-xs text-muted-foreground">
                    Scope: {item.scope || "—"} · Created {formatDate(item.created_at)}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant={item.granted ? "default" : "secondary"}>
                    {item.granted ? "granted" : "revoked"}
                  </Badge>

                  {item.granted && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => revoke.mutate(item.purpose)}
                    >
                      Revoke
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <section className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5 text-cyan-300" />
              Audit transparency
            </CardTitle>
            <CardDescription>Recent actions performed on your account.</CardDescription>
          </CardHeader>

          <CardContent className="max-h-[28rem] space-y-2 overflow-auto">
            {(audit.data || []).map((event) => (
              <div key={event.id} className="rounded-lg border p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{event.action}</span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(event.created_at)}
                  </span>
                </div>
                {event.resource_type && (
                  <div className="mt-1 text-xs text-muted-foreground">
                    {event.resource_type} · {event.resource_id || "—"}
                  </div>
                )}
              </div>
            ))}

            {!audit.isLoading && !(audit.data || []).length && (
              <p className="text-sm text-muted-foreground">No audit events.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-300" />
              Egress ledger
            </CardTitle>
            <CardDescription>
              External destinations used for identifier-related processing.
            </CardDescription>
          </CardHeader>

          <CardContent className="max-h-[28rem] space-y-2 overflow-auto">
            {(egress.data || []).map((event) => (
              <div key={event.id} className="rounded-lg border p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{event.destination_host}</span>
                  <Badge variant={event.success ? "default" : "destructive"}>
                    {event.success ? "success" : "failed"}
                  </Badge>
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {event.purpose} · {event.method} · {formatDate(event.created_at)}
                </div>
              </div>
            ))}

            {!egress.isLoading && !(egress.data || []).length && (
              <p className="text-sm text-muted-foreground">No egress events.</p>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
```

---

# PART I — Onboarding

## 13. NEW: `frontend/src/features/onboarding/OnboardingPage.tsx`

```tsx
import { CheckCircle2, Circle, Rocket, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { useIdentifiers } from "@/features/identifiers/api";
import { useScans } from "@/features/scans/api";
import { useLatestScore } from "@/features/scores/api";
import { useLatestPlan } from "@/features/recommendations/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { OnboardingStep } from "@/lib/types";

export function OnboardingPage() {
  const identifiers = useIdentifiers();
  const scans = useScans();
  const score = useLatestScore();
  const plan = useLatestPlan();

  const totalIdentifiers = identifiers.data?.length || 0;
  const verifiedIdentifiers =
    identifiers.data?.filter((identifier) => identifier.is_verified).length || 0;
  const hasScan = (scans.data || []).length > 0;
  const hasScore = !!score.data;
  const hasPlan = !!plan.data;

  const steps: OnboardingStep[] = [
    {
      id: "identifier",
      title: "Add an identifier",
      description: "Add an email, domain, username, or phone number.",
      complete: totalIdentifiers > 0,
      href: "/app/identifiers",
    },
    {
      id: "verify",
      title: "Verify ownership",
      description: "Only verified identifiers can be scanned.",
      complete: verifiedIdentifiers > 0,
      href: "/app/identifiers",
    },
    {
      id: "scan",
      title: "Run your first scan",
      description: "Discover free surface exposure signals.",
      complete: hasScan,
      href: "/app/scans",
    },
    {
      id: "score",
      title: "Understand your PDSS",
      description: "Review score drivers and counterfactuals.",
      complete: hasScore,
      href: "/app/scores",
    },
    {
      id: "remediate",
      title: "Take action",
      description: "Follow your guided or Green remediation plan.",
      complete: hasPlan,
      href: "/app/remediation",
    },
  ];

  const completed = steps.filter((step) => step.complete).length;
  const percent = Math.round((completed / steps.length) * 100);

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <section className="relative overflow-hidden rounded-2xl border border-cyan-400/20 bg-gradient-to-br from-cyan-400/10 via-blue-500/5 to-violet-500/10 p-6 md:p-10">
        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-cyan-400/10 blur-3xl" />
        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-cyan-400/10 p-3">
              <Rocket className="h-6 w-6 text-cyan-300" />
            </div>
            <div>
              <p className="text-sm font-medium text-cyan-200">DigiZafe onboarding</p>
              <h1 className="text-3xl font-bold tracking-tight">
                Build your exposure picture.
              </h1>
            </div>
          </div>

          <p className="mt-5 max-w-2xl text-balance text-muted-foreground">
            DigiZafe works in a closed loop: verify ownership, discover exposure,
            understand the score, take action, and rescan to measure improvement.
          </p>

          <div className="mt-6 max-w-xl">
            <div className="mb-2 flex justify-between text-xs text-muted-foreground">
              <span>{completed} of {steps.length} steps complete</span>
              <span>{percent}%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-black/20">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-violet-400"
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        {steps.map((step, index) => (
          <Card key={step.id} className={step.complete ? "border-emerald-400/30" : ""}>
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-base">
                {step.complete ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-300" />
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground" />
                )}
                <span>
                  <span className="mr-2 text-xs text-muted-foreground">
                    {index + 1}
                  </span>
                  {step.title}
                </span>
              </CardTitle>
            </CardHeader>

            <CardContent>
              <p className="mb-4 text-sm text-muted-foreground">
                {step.description}
              </p>

              <Button asChild variant={step.complete ? "secondary" : "default"}>
                <Link to={step.href}>
                  {step.complete ? "Review" : "Start"}
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-emerald-400/20 bg-emerald-400/5">
        <CardContent className="flex items-start gap-3 p-5 text-sm">
          <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-300" />
          <p className="text-muted-foreground">
            Your scans are self-only. DigiZafe requires ownership verification before
            discovery or remediation and records external egress transparently.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

# PART J — Update Scores Page

## 14. UPDATE: `frontend/src/features/scores/ScoresPage.tsx`

Replace the existing file:

```tsx
import { useState } from "react";
import { useIdentifiers } from "@/features/identifiers/api";
import { useFindings } from "@/features/findings/api";
import { useComputeScore, useLatestScore, useScoreHistory } from "./api";
import { PdssGauge } from "@/components/charts/PdssGauge";
import { PdssBreakdown } from "@/components/charts/PdssBreakdown";
import { RiskAutopsy } from "@/components/creative/RiskAutopsy";
import { WhatIfSimulator } from "@/components/creative/WhatIfSimulator";
import { NarrativeBriefing } from "@/components/creative/NarrativeBriefing";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";

export function ScoresPage() {
  const ids = useIdentifiers();
  const [identifierId, setIdentifierId] = useState<string>("");

  const score = useLatestScore(identifierId || undefined);
  const findings = useFindings(identifierId || undefined);
  const history = useScoreHistory(identifierId || undefined);
  const compute = useComputeScore();

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">PDSS Score</h1>
          <p className="text-muted-foreground">
            Explore the score, its drivers, and the actions most likely to improve it.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <select
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={identifierId}
            onChange={(event) => setIdentifierId(event.target.value)}
          >
            <option value="">Whole identity / latest</option>
            {(ids.data || []).map((identifier) => (
              <option key={identifier.id} value={identifier.id}>
                {identifier.type}: {identifier.value_display}
              </option>
            ))}
          </select>

          <Button
            onClick={() =>
              compute.mutate({
                identifier_id: identifierId || undefined,
                persist: true,
              })
            }
            disabled={compute.isPending}
          >
            {compute.isPending ? "Computing…" : "Compute PDSS"}
          </Button>
        </div>
      </header>

      {score.data ? (
        <>
          <Card className="glass-panel gradient-border">
            <CardHeader>
              <CardTitle>Current exposure picture</CardTitle>
              <CardDescription>{score.data.explanation_summary}</CardDescription>
            </CardHeader>

            <CardContent className="flex flex-col items-center gap-5 md:flex-row md:items-start">
              <PdssGauge
                score={score.data.score_combined}
                severity={score.data.severity}
              />

              <div className="space-y-3">
                <div className="text-sm text-muted-foreground">
                  Model {score.data.model_version}
                </div>

                <p className="break-all rounded-lg border bg-black/10 p-3 font-mono text-xs text-muted-foreground">
                  {score.data.vector}
                </p>

                {(score.data.attributions || []).length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Attributions: {score.data.attributions.join(" · ")}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          <RiskAutopsy score={score.data} />

          <PdssBreakdown score={score.data} />

          <WhatIfSimulator
            score={score.data}
            findings={findings.data || []}
            identifierId={identifierId || undefined}
          />

          <NarrativeBriefing identifierId={identifierId || undefined} />

          <Card>
            <CardHeader>
              <CardTitle>Score history</CardTitle>
              <CardDescription>
                Compare score changes after rescans and remediation.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-2 text-sm">
              {(history.data || []).map((item) => (
                <div
                  key={item.id}
                  className="flex flex-wrap justify-between gap-2 border-b border-border/50 py-2"
                >
                  <span>
                    {item.score_combined.toFixed(1)} · {item.severity} · {item.trigger}
                  </span>
                  <span className="text-muted-foreground">
                    {formatDate(item.created_at)}
                  </span>
                </div>
              ))}

              {!history.isLoading && !(history.data || []).length && (
                <p className="text-muted-foreground">
                  No score history yet.
                </p>
              )}
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No score yet. Run a scan, then compute PDSS.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

---

# PART K — Update Application Navigation

## 15. UPDATE: `frontend/src/components/layout/AppShell.tsx`

Replace the existing file:

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
  UserRoundCog,
  LockKeyhole,
  Rocket,
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/app/onboarding", label: "Start here", icon: Rocket },
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/identifiers", label: "Identifiers", icon: Fingerprint },
  { to: "/app/scans", label: "Scans", icon: Radar },
  { to: "/app/findings", label: "Findings", icon: AlertTriangle },
  { to: "/app/scores", label: "PDSS Score", icon: Gauge },
  { to: "/app/recommendations", label: "Plan", icon: ListChecks },
  { to: "/app/remediation", label: "Remediation", icon: UserRoundCog },
  { to: "/app/identity", label: "Identity graph", icon: Network },
  { to: "/app/privacy", label: "Privacy center", icon: LockKeyhole },
];

export function AppShell() {
  const user = useAuthStore((state) => state.user);
  const clear = useAuthStore((state) => state.clear);
  const navigate = useNavigate();
  const attribution = import.meta.env.VITE_XPOSEDORNOT_ATTRIBUTION as string | undefined;

  return (
    <div className="flex min-h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-2"
      >
        Skip to main content
      </a>

      <aside className="hidden w-64 shrink-0 border-r bg-card/40 md:flex md:flex-col">
        <div className="flex items-center gap-2 border-b px-4 py-4">
          <Shield className="h-6 w-6 text-primary" />
          <div>
            <div className="font-semibold tracking-tight">DigiZafe</div>
            <div className="text-xs text-muted-foreground">Exposure intelligence</div>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3" aria-label="Main navigation">
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
              <item.icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t p-3 text-xs text-muted-foreground">
          <div className="mb-2 truncate" title={user?.email || undefined}>
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
            <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
            Sign out
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b px-4 py-3 md:hidden">
          <Link to="/app" className="flex items-center gap-2 font-semibold">
            <Shield className="h-5 w-5 text-primary" aria-hidden="true" />
            DigiZafe
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

        <div className="flex gap-1 overflow-x-auto border-b p-2 md:hidden" aria-label="Mobile navigation">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "whitespace-nowrap rounded-md px-2 py-2 text-xs",
                  isActive ? "bg-accent text-foreground" : "text-muted-foreground"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>

        <main id="main-content" className="flex-1 overflow-auto p-4 md:p-8">
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

# PART L — Update Router

## 16. UPDATE: `frontend/src/app/router.tsx`

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
import { RemediationPage } from "@/features/remediation/RemediationPage";
import { PrivacyPage } from "@/features/privacy/PrivacyPage";
import { OnboardingPage } from "@/features/onboarding/OnboardingPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/app/onboarding" replace />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: "/app",
        element: <AppShell />,
        children: [
          {
            index: true,
            element: <DashboardPage />,
          },
          {
            path: "onboarding",
            element: <OnboardingPage />,
          },
          {
            path: "identifiers",
            element: <IdentifiersPage />,
          },
          {
            path: "scans",
            element: <ScansPage />,
          },
          {
            path: "scans/:scanId",
            element: <ScanDetailPage />,
          },
          {
            path: "findings",
            element: <FindingsPage />,
          },
          {
            path: "scores",
            element: <ScoresPage />,
          },
          {
            path: "recommendations",
            element: <RecommendationsPage />,
          },
          {
            path: "remediation",
            element: <RemediationPage />,
          },
          {
            path: "identity",
            element: <IdentityPage />,
          },
          {
            path: "privacy",
            element: <PrivacyPage />,
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/app/onboarding" replace />,
  },
]);
```

---

# PART M — Sprint 8 Narrative Compatibility Fix

Sprint 8 contains a backend naming mismatch between `prefer_ollama` and `prefer_llm`, plus undefined variables in `NarrativeService.generate`.

Apply the following replacement.

## 17. UPDATE: `backend/app/services/privacy/narrative_service.py`

```python
from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.narrative import (
    FactsPack,
    SYSTEM_PROMPT,
    build_deterministic_narrative,
    user_prompt_from_facts,
)
from app.repositories.privacy_repository import PrivacyRepository
from app.repositories.score_repository import ScoreRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.remediation_repository import RemediationRepository
from app.repositories.identifier_repository import IdentifierRepository
from app.services.privacy.groq_client import groq_available, groq_chat, GroqError
from app.services.audit_service import AuditService


class NarrativeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PrivacyRepository(session)
        self.scores = ScoreRepository(session)
        self.settings = get_settings()
        self.audit = AuditService(session)

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def _facts(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None,
        score_snapshot_id: uuid.UUID | None,
    ) -> tuple[FactsPack, uuid.UUID]:
        if score_snapshot_id:
            snapshot = await self.scores.get(score_snapshot_id, user_id)
        else:
            snapshot = await self.scores.latest(user_id, identifier_id)

        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail="No score snapshot — compute PDSS first",
            )

        contributions = list(snapshot.contributions or [])[
            : self.settings.narrative_max_findings
        ]
        counterfactuals = list(snapshot.counterfactuals or [])[:5]

        recommendation_titles: list[str] = []
        try:
            recommendations = await RecommendationRepository(self.session).list_open(
                user_id,
                identifier_id,
            )
            recommendation_titles = [
                recommendation.title for recommendation in recommendations[:8]
            ]
        except Exception:
            recommendation_titles = []

        broker_statuses: list[dict[str, str]] = []
        try:
            states = await RemediationRepository(self.session).list_states(user_id)
            broker_statuses = [
                {
                    "broker_id": state.broker_id,
                    "status": state.status,
                }
                for state in states[:10]
            ]
        except Exception:
            broker_statuses = []

        identifier_types: list[str] = []
        try:
            identifiers = await IdentifierRepository(self.session).list_for_user(user_id)
            identifier_types = sorted(
                {
                    identifier.type
                    for identifier in identifiers
                    if identifier.is_verified
                }
            )
        except Exception:
            identifier_types = []

        facts = FactsPack(
            score_combined=float(snapshot.score_combined),
            severity=snapshot.severity,
            score_confirmed=float(snapshot.score_confirmed),
            score_possible=float(snapshot.score_possible),
            vector=snapshot.vector,
            explanation_summary=snapshot.explanation_summary or "",
            model_version=snapshot.model_version,
            contributions=contributions,
            counterfactuals=counterfactuals,
            attributions=list(snapshot.attributions or []),
            open_recommendation_titles=recommendation_titles,
            broker_statuses=broker_statuses,
            identifier_types=identifier_types,
        )

        return facts, snapshot.id

    async def generate(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        score_snapshot_id: uuid.UUID | None = None,
        prefer_llm: bool = True,
        persist: bool = True,
    ) -> dict[str, Any]:
        if not self.settings.feature_grounded_narrative:
            raise HTTPException(
                status_code=503,
                detail="Narrative feature disabled",
            )

        await self._set_rls(user_id)

        facts, snapshot_id = await self._facts(
            user_id,
            identifier_id=identifier_id,
            score_snapshot_id=score_snapshot_id,
        )

        mode = "deterministic"
        model_name: str | None = None
        body = build_deterministic_narrative(facts)

        if prefer_llm and await groq_available():
            try:
                body = await groq_chat(
                    system=SYSTEM_PROMPT,
                    user=user_prompt_from_facts(facts),
                )
                mode = "groq"
                model_name = self.settings.groq_model
            except GroqError:
                body = build_deterministic_narrative(facts)

        title = (
            f"Exposure briefing — PDSS "
            f"{facts.score_combined:.1f} ({facts.severity})"
        )

        row = None

        if persist:
            row = await self.repo.save_narrative(
                user_id=user_id,
                score_snapshot_id=snapshot_id,
                identifier_id=identifier_id,
                mode=mode,
                model_name=model_name,
                title=title,
                body_markdown=body,
                facts_used=facts.to_dict(),
            )

            await self.audit.log(
                "privacy.narrative_generated",
                user_id=user_id,
                resource_type="narrative_briefing",
                resource_id=str(row.id),
                details={
                    "mode": mode,
                    "model": model_name,
                    "grounded": True,
                },
            )

            await self.session.commit()

        return {
            "id": row.id if row else None,
            "score_snapshot_id": snapshot_id,
            "identifier_id": identifier_id,
            "mode": mode,
            "model_name": model_name,
            "title": title,
            "body_markdown": body,
            "grounded": True,
            "facts_used": facts.to_dict(),
            "created_at": row.created_at if row else None,
        }

    async def get_counterfactuals(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        snapshot_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        await self._set_rls(user_id)

        snapshot = (
            await self.scores.get(snapshot_id, user_id)
            if snapshot_id
            else await self.scores.latest(user_id, identifier_id)
        )

        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail="No score snapshot",
            )

        return {
            "score_snapshot_id": snapshot.id,
            "counterfactuals": snapshot.counterfactuals or [],
            "explanation_summary": snapshot.explanation_summary or "",
            "vector": snapshot.vector,
            "score_combined": snapshot.score_combined,
        }
```

## 18. UPDATE: `backend/app/api/v1/privacy.py`

In the narrative endpoint, replace the service call with:

```python
data = await svc.generate(
    current_user.id,
    identifier_id=body.identifier_id,
    score_snapshot_id=body.score_snapshot_id,
    prefer_llm=body.prefer_ollama,
    persist=body.persist,
)
```

Ensure this import exists:

```python
from fastapi import APIRouter, Depends, Query, HTTPException
```

---

# PART N — Accessibility Requirements

Sprint 10 must satisfy these requirements:

- All major pages have one `<h1>`.
- Navigation has `aria-label`.
- Important asynchronous status messages use `role="status"` or `aria-live`.
- Errors use `role="alert"`.
- Buttons have visible focus styles.
- Checkbox controls have visible labels.
- Color is not the only method of communicating severity.
- Reduced-motion users receive minimal transitions.
- External links use `target="_blank"` and `rel="noreferrer"`.
- Forms provide labels and meaningful placeholders.
- The main content has a skip link.
- The remediation console must not submit forms without clear user action.
- CAPTCHA and manual tasks must explain what the user must do next.
- “Dry-run” must be visibly different from real remediation.
- Attribution must remain visible when XposedOrNot data is displayed.

---

# PART O — Optional Dashboard Enhancement

Add the following section to the existing `DashboardPage.tsx` after the score card:

```tsx
<div className="grid gap-4 md:grid-cols-2">
  <Card className="border-cyan-400/20 bg-cyan-400/5">
    <CardHeader>
      <CardTitle className="text-base">Next best action</CardTitle>
      <CardDescription>
        Use your remediation plan to reduce the highest-impact exposure first.
      </CardDescription>
    </CardHeader>
    <CardContent>
      <Button asChild>
        <Link to="/app/remediation">Open remediation console</Link>
      </Button>
    </CardContent>
  </Card>

  <Card className="border-violet-400/20 bg-violet-400/5">
    <CardHeader>
      <CardTitle className="text-base">Privacy controls</CardTitle>
      <CardDescription>
        Review consent, external egress, exports, and account deletion.
      </CardDescription>
    </CardHeader>
    <CardContent>
      <Button asChild variant="secondary">
        <Link to="/app/privacy">Open privacy center</Link>
      </Button>
    </CardContent>
  </Card>
</div>
```

---

# PART P — Sprint 10 Validation

## 1. Frontend build

```bash
cd frontend
npm run build
```

## 2. Start development server

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

## 3. Authentication test

```text
Register → Login → refresh remains memory-only
```

Expected behavior:

- Access token works during the active page session.
- Refresh token remains only in Zustand memory.
- Reloading the page requires login again.
- No `localStorage` or `sessionStorage` keys are created.

## 4. Onboarding test

```text
/app/onboarding
```

Verify:

- Steps update based on identifiers, scans, score, and recommendations.
- Links route to the correct page.
- Completion percentage updates.

## 5. Risk autopsy test

```text
Run scan → compute PDSS → open /app/scores
```

Verify:

- Top drivers display.
- Vector fragments display.
- Source attribution appears.
- XposedOrNot findings are visibly attributed.

## 6. What-if simulator test

```text
Open /app/scores
Select one or more findings
Click Simulate
```

Verify:

- `/scores/whatif` is called.
- Current score and simulated score are shown.
- No finding is actually dismissed or modified.

## 7. Narrative test

```text
Open /app/scores
Click Generate briefing
```

Verify:

- `/privacy/narrative` is called.
- Narrative displays as grounded.
- Deterministic fallback works if the optional model provider is unavailable.

## 8. Remediation test

```text
Open /app/remediation
Select verified email
Enable dry-run
Select one or more brokers
Click Preview opt-out
```

Verify:

- Job is created.
- Job status updates.
- Dry-run is visibly labeled.
- Broker states appear after processing.
- CAPTCHA queue displays manual tasks when applicable.

## 9. Privacy center test

```text
Open /app/privacy
```

Verify:

- Export can be created and downloaded.
- Consent can be granted and revoked.
- Audit events display.
- Egress ledger displays.
- Account deletion requires the exact confirmation phrase.

## 10. Accessibility test

Use keyboard only:

```text
Tab → Enter → Arrow keys → Escape
```

Check:

- Skip link works.
- Navigation is reachable.
- Buttons have visible focus.
- Forms have labels.
- Status and error messages are announced.

---

# Sprint 10 Definition of Done

- [ ] Creative onboarding flow implemented
- [ ] Risk autopsy explains score drivers
- [ ] What-if simulator calls `/scores/whatif`
- [ ] Narrative briefing calls `/privacy/narrative`
- [ ] Narrative backend compatibility bug fixed
- [ ] Remediation console implemented
- [ ] Green broker catalog displayed
- [ ] Dry-run opt-out supported
- [ ] Remediation job progress displayed
- [ ] CAPTCHA/manual queue displayed
- [ ] Freeze checklist displayed and editable
- [ ] Right-to-know request generation implemented
- [ ] Complaint generation implemented
- [ ] Generated requests can be marked sent
- [ ] Broker verification action available
- [ ] Privacy center implemented
- [ ] Data export can be downloaded
- [ ] Consent grant/revoke works
- [ ] Audit transparency works
- [ ] Egress ledger works
- [ ] Account deletion workflow works
- [ ] No `localStorage` or `sessionStorage` usage remains
- [ ] Reduced-motion styles implemented
- [ ] Keyboard navigation and focus styles implemented
- [ ] ARIA labels/live regions added
- [ ] XposedOrNot attribution remains visible
- [ ] Frontend production build passes
- [ ] No paid API keys required
- [ ] No new backend architecture introduced

---

# Endpoint Quick Reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/remediation/brokers` | Green broker catalog |
| GET | `/api/v1/remediation/state` | Broker opt-out state |
| POST | `/api/v1/remediation/jobs/broker-optout` | Start dry-run or real remediation |
| GET | `/api/v1/remediation/jobs` | List remediation jobs |
| GET | `/api/v1/remediation/jobs/{id}` | Job details |
| POST | `/api/v1/remediation/jobs/{id}/cancel` | Cancel job |
| GET | `/api/v1/remediation/captcha` | CAPTCHA/manual queue |
| POST | `/api/v1/remediation/captcha/{id}` | Resume or skip CAPTCHA item |
| GET | `/api/v1/remediation/freeze` | Freeze checklist |
| PATCH | `/api/v1/remediation/freeze/{id}` | Update freeze task |
| POST | `/api/v1/remediation/know` | Generate right-to-know request |
| POST | `/api/v1/remediation/complaints` | Generate complaint |
| GET | `/api/v1/remediation/requests` | List generated requests |
| POST | `/api/v1/remediation/requests/{id}/mark-sent` | Mark request sent |
| POST | `/api/v1/remediation/verify` | Re-check broker removals |
| POST | `/api/v1/privacy/export` | Create data export |
| GET | `/api/v1/privacy/export/{id}` | Retrieve export package |
| GET | `/api/v1/privacy/consent` | List consent records |
| POST | `/api/v1/privacy/consent` | Grant consent |
| POST | `/api/v1/privacy/consent/revoke` | Revoke consent |
| GET | `/api/v1/privacy/audit` | Audit transparency |
| GET | `/api/v1/privacy/egress` | Egress transparency |
| POST | `/api/v1/privacy/account/delete` | Schedule account deletion |
| POST | `/api/v1/privacy/narrative` | Generate grounded briefing |
| GET | `/api/v1/privacy/counterfactuals` | Retrieve score counterfactuals |
| POST | `/api/v1/scores/whatif` | Run what-if simulation |

---

# File Checklist

## New files

```text
frontend/src/hooks/useReducedMotion.ts

frontend/src/components/creative/RiskAutopsy.tsx
frontend/src/components/creative/WhatIfSimulator.tsx
frontend/src/components/creative/NarrativeBriefing.tsx

frontend/src/features/remediation/api.ts
frontend/src/features/remediation/RemediationPage.tsx

frontend/src/features/privacy/api.ts
frontend/src/features/privacy/PrivacyPage.tsx

frontend/src/features/onboarding/OnboardingPage.tsx
```

## Updated files

```text
.env.example
frontend/.env
frontend/src/lib/auth-store.ts
frontend/src/lib/types.ts
frontend/src/styles/index.css
frontend/src/components/layout/AppShell.tsx
frontend/src/features/scores/ScoresPage.tsx
frontend/src/app/router.tsx

backend/app/services/privacy/narrative_service.py
backend/app/api/v1/privacy.py
```

## Optional update

```text
frontend/src/features/dashboard/DashboardPage.tsx
```

---

# Commit

From the repository root:

```bash
git add .
git commit -m "feat(sprint-10): creative frontend, risk autopsy, what-if, narrative, remediation console, privacy center, onboarding, accessibility"
```

---

# Sprint 10 Completion Statement

Sprint 10 is complete when a user can:

```text
Register
→ Add and verify an identifier
→ Run a scan
→ Understand PDSS through risk autopsy
→ Simulate remediation impact
→ Read a grounded narrative briefing
→ Open a remediation console
→ Run a dry-run or Green broker job
→ Handle CAPTCHA/manual tasks
→ Track freeze and rights requests
→ Review consent and egress
→ Export data
→ Schedule account deletion
```

DigiZafe then has a complete user-facing loop:

```text
Verify → Discover → Explain → Prioritize → Remediate → Re-verify → Re-score
```

Next sprint:

```text
Sprint 11 — Deep + Constrained-Dark Free Amber
```