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
