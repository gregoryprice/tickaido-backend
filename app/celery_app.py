#!/usr/bin/env python3
"""
Celery application configuration for background task processing
"""

from celery import Celery
from celery.schedules import crontab

from app.config.settings import get_settings

# Get settings
settings = get_settings()

# Create Celery instance
celery_app = Celery(
    "ai-ticket-creator-backend",
    broker=settings.effective_celery_broker_url,
    backend=settings.effective_celery_result_backend,
    include=[
        "app.tasks.file_tasks",
        "app.tasks.ai_tasks", 
        "app.tasks.integration_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.agent_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task routing
    task_routes={
        "app.tasks.file_tasks.*": {"queue": "file_processing"},
        "app.tasks.ai_tasks.*": {"queue": "ai_processing"},
        "app.tasks.integration_tasks.*": {"queue": "integrations"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.agent_tasks.*": {"queue": "agent_processing"},
    },
    
    # Task execution settings
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_log_color=False,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "retry_policy": {
            "timeout": 5.0
        }
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Periodic task schedule
    beat_schedule={
        # Process pending file uploads every 5 minutes
        "process-pending-files": {
            "task": "app.tasks.file_tasks.process_pending_files",
            "schedule": crontab(minute="*/5"),
        },
        
        # Sync integrations every 30 minutes
        "sync-integrations": {
            "task": "app.tasks.integration_tasks.sync_all_active_integrations",
            "schedule": crontab(minute="*/30"),
        },
        
        # Clean up old completed tasks every hour
        "cleanup-completed-tasks": {
            "task": "app.tasks.maintenance_tasks.cleanup_completed_tasks",
            "schedule": crontab(minute=0),
        },
        
        # Generate daily analytics report
        "daily-analytics": {
            "task": "app.tasks.analytics_tasks.generate_daily_report",
            "schedule": crontab(hour=1, minute=0),
        },
        
        # Check integration health every 15 minutes
        "health-check-integrations": {
            "task": "app.tasks.integration_tasks.health_check_integrations",
            "schedule": crontab(minute="*/15"),
        }
    }
)

# Import task modules to ensure registration
try:
    from app.tasks import file_tasks, ai_tasks, integration_tasks, notification_tasks, agent_tasks
    print("✅ All task modules imported successfully for Celery registration")
except ImportError as e:
    print(f"⚠️ Failed to import some task modules: {e}")

# Task autodiscovery
celery_app.autodiscover_tasks()

# Health check task
@celery_app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
    return {"status": "healthy", "worker": self.request.hostname}

if __name__ == "__main__":
    celery_app.start()