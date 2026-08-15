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
