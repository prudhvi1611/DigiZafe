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
