from celery import Celery
from celery.signals import task_failure, task_retry, task_success

from app.core.config import get_settings
from app.core.metrics import WORKER_TASK_OUTCOME

settings = get_settings()

celery_app = Celery(
    "digizafe",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks",
        "app.tasks.discovery_tasks",
        "app.tasks.alert_tasks",
        "app.tasks.remediation_tasks",
        "app.tasks.enrichment_tasks",
        "app.tasks.osint_tasks",
    ],
)

celery_app.conf.task_routes = {
    'app.tasks.enrichment_tasks.*': {'queue': 'identity_enrichment'},
    'app.tasks.osint_tasks.*': {'queue': 'osint_connectors'},
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="app.tasks.health_ping")
def health_ping() -> str:
    return "pong"

celery_app.conf.beat_schedule = {
    "reconcile-scans": {
        "task": "app.tasks.discovery_tasks.reconcile_scans_task",
        "schedule": 300.0,
    },
    "reconcile-alerts-rescans": {
        "task": "app.tasks.alert_tasks.reconcile_alerts_rescans_task",
        "schedule": float(settings.alert_reconcile_interval_seconds),
    },
    "update-brokers": {
        "task": "app.tasks.remediation_tasks.update_brokers_task",
        "schedule": float(settings.update_brokers_interval_hours * 3600),
    }
}

@task_success.connect
def on_task_success(sender=None, **kwargs):
    if sender:
        WORKER_TASK_OUTCOME.labels(task_name=sender.name, outcome="success").inc()

@task_failure.connect
def on_task_failure(sender=None, **kwargs):
    if sender:
        WORKER_TASK_OUTCOME.labels(task_name=sender.name, outcome="failure").inc()

@task_retry.connect
def on_task_retry(sender=None, **kwargs):
    if sender:
        WORKER_TASK_OUTCOME.labels(task_name=sender.name, outcome="retry").inc()
