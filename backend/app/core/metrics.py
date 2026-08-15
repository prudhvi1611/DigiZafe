import time

from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# --- API Metrics ---
REQUEST_COUNT = Counter(
    "api_request_count_total",
    "Total number of API requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "API request latency in seconds",
    ["method", "endpoint"]
)

# --- Business Metrics ---
SCAN_STATE_TRANSITION = Counter(
    "scan_state_transition_total",
    "Total transitions of scan states",
    ["from_state", "to_state"]
)

CONNECTOR_OUTCOME = Counter(
    "connector_outcome_total",
    "Outcomes of connector execution",
    ["connector_id", "outcome"]
)

REMEDIATION_OUTCOME = Counter(
    "remediation_outcome_total",
    "Outcomes of remediation actions",
    ["broker_id", "outcome"]
)

WORKER_TASK_OUTCOME = Counter(
    "worker_task_outcome_total",
    "Outcomes of celery tasks",
    ["task_name", "outcome"]
)

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        method = request.method
        # We use url.path but for high cardinality endpoints (like /api/v1/scans/{id})
        # it's better to use request.url.path or router matching.
        # To avoid high cardinality, we just use a generic path if it matches an ID,
        # but for simplicity we'll take the first two path components.
        path_parts = request.url.path.split("/")
        endpoint = "/" + "/".join(path_parts[1:4]) if len(path_parts) > 3 else request.url.path
        
        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            latency = time.time() - start_time
            if request.url.path != "/metrics":
                REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
                REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)

        return response

def metrics_response():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
