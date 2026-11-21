from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'generate-invoices': {
        'task': 'app.workers.tasks.generate_invoices',
        'schedule': crontab(hour=0, minute=5),  # Daily 00:05 EAT
    },
    'check-overdue-invoices': {
        'task': 'app.workers.tasks.check_overdue_invoices',
        'schedule': crontab(hour=0, minute=30),  # Daily 00:30 EAT
    },
    'sync-router-status': {
        'task': 'app.workers.tasks.sync_router_status',
        'schedule': 300.0,  # Every 5 minutes
    },
    'sync-active-connections': {
        'task': 'app.workers.tasks.sync_active_connections',
        'schedule': 120.0,  # Every 2 minutes
    },
    'send-expiry-reminders': {
        'task': 'app.workers.tasks.send_expiry_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily 09:00 EAT
    },
}
