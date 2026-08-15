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
