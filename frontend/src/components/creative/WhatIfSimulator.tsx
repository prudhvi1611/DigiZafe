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
