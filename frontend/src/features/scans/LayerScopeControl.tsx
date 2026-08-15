import { AlertTriangle, CheckCircle2, LockKeyhole } from "lucide-react";
import { useLayerCatalog } from "./layers-api";
import type { ExposureLayer } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface LayerScopeControlProps {
  value: ExposureLayer;
  onChange: (value: ExposureLayer) => void;
  hasConsent: (layer: ExposureLayer) => boolean;
}

export function LayerScopeControl({
  value,
  onChange,
  hasConsent,
}: LayerScopeControlProps) {
  const layers = useLayerCatalog();

  return (
    <div className="grid gap-3 md:grid-cols-3">
      {(layers.data || []).map((layer) => {
        const selected = value === layer.layer;
        const consented = hasConsent(layer.layer);

        return (
          <button
            key={layer.layer}
            type="button"
            onClick={() => onChange(layer.layer)}
            className={`text-left transition-colors ${
              selected ? "ring-2 ring-primary" : ""
            }`}
            aria-pressed={selected}
          >
            <Card className={selected ? "border-primary bg-primary/10" : ""}>
              <CardContent className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-medium">{layer.label}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {layer.layer}
                    </div>
                  </div>

                  {selected && (
                    <CheckCircle2
                      className="h-5 w-5 text-primary"
                      aria-label="Selected"
                    />
                  )}
                </div>

                <p className="text-xs text-muted-foreground">
                  {layer.description}
                </p>

                {layer.requires_explicit_consent ? (
                  <Badge
                    variant={consented ? "default" : "secondary"}
                    className="gap-1"
                  >
                    <LockKeyhole className="h-3 w-3" />
                    {consented ? "Consent granted" : "Consent required"}
                  </Badge>
                ) : (
                  <Badge variant="outline">Default layer</Badge>
                )}

                {layer.layer !== "surface" && (
                  <div className="flex gap-2 rounded-md border border-amber-400/20 bg-amber-400/5 p-2 text-xs text-amber-100">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span>{layer.warning}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </button>
        );
      })}
    </div>
  );
}
