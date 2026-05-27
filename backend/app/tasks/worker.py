from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    'ops_platform',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.tasks.scan_tasks',
        'app.tasks.iperf_tasks',
        'app.tasks.broadband_tasks',
        'app.tasks.topology_tasks',
    ],
)

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Asia/Shanghai',
    enable_utc=True,
    broker_connection_timeout=3,
    broker_connection_retry=False,
    broker_connection_max_retries=1,
    task_soft_time_limit=1800,
    task_time_limit=1900,
    result_expires=86400,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_routes={
        'app.tasks.scan_tasks.*': {'queue': 'scan'},
        'app.tasks.iperf_tasks.*': {'queue': 'iperf'},
        'app.tasks.broadband_tasks.*': {'queue': 'default'},
        'app.tasks.topology_tasks.*': {'queue': 'topology'},
    },
    task_default_queue='default',
    beat_schedule={
        'check-broadband-renewals-daily': {
            'task': 'app.tasks.broadband_tasks.check_broadband_renewals',
            'schedule': crontab(hour=9, minute=0),
        },
    },
)

worker = celery_app
