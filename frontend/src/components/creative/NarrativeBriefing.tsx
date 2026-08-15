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
