#!/usr/bin/env python3
"""
Test Celery background tasks functionality
"""

import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4


def test_celery_app_import():
    """Test that Celery app can be imported"""
    print("Testing Celery app import...")
    
    from app.celery_app import celery_app
    assert celery_app is not None
    assert celery_app.main == "ai-ticket-creator-backend"
    print("✅ Celery app imported successfully")


def test_task_imports():
    """Test that all task modules can be imported"""
    print("Testing task imports...")
    
    from app.tasks.file_tasks import process_file_upload, analyze_file_content
    from app.tasks.ai_tasks import create_ticket_with_ai, categorize_ticket
    from app.tasks.integration_tasks import sync_integration, test_integration_connection
    from app.tasks.notification_tasks import send_email_notification, notify_ticket_created
    
    print("✅ All task modules imported successfully")


def test_task_registration():
    """Test that tasks are registered with Celery"""
    print("Testing task registration...")
    
    from app.celery_app import celery_app
    
    # Check if tasks are registered
    registered_tasks = celery_app.tasks
    
    # File tasks
    assert "app.tasks.file_tasks.process_file_upload" in registered_tasks
    assert "app.tasks.file_tasks.analyze_file_content" in registered_tasks
    
    # AI tasks
    assert "app.tasks.ai_tasks.create_ticket_with_ai" in registered_tasks
    assert "app.tasks.ai_tasks.categorize_ticket" in registered_tasks
    
    # Integration tasks
    assert "app.tasks.integration_tasks.sync_integration" in registered_tasks
    assert "app.tasks.integration_tasks.test_integration_connection" in registered_tasks
    
    # Notification tasks
    assert "app.tasks.notification_tasks.send_email_notification" in registered_tasks
    assert "app.tasks.notification_tasks.notify_ticket_created" in registered_tasks
    
    print("✅ All tasks registered with Celery")


def test_celery_configuration():
    """Test Celery app configuration"""
    print("Testing Celery configuration...")
    
    from app.celery_app import celery_app
    
    # Check configuration
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc == True
    
    # Check task routing
    task_routes = celery_app.conf.task_routes
    assert "app.tasks.file_tasks.*" in task_routes
    assert "app.tasks.ai_tasks.*" in task_routes
    assert "app.tasks.integration_tasks.*" in task_routes
    assert "app.tasks.notification_tasks.*" in task_routes
    
    print("✅ Celery configuration correct")


def test_beat_schedule():
    """Test Celery Beat periodic task schedule"""
    print("Testing Beat schedule...")
    
    from app.celery_app import celery_app
    
    beat_schedule = celery_app.conf.beat_schedule
    
    # Check scheduled tasks
    assert "process-pending-files" in beat_schedule
    assert "sync-integrations" in beat_schedule
    assert "cleanup-completed-tasks" in beat_schedule
    assert "daily-analytics" in beat_schedule
    assert "health-check-integrations" in beat_schedule
    
    # Check task configuration
    process_files_task = beat_schedule["process-pending-files"]
    assert process_files_task["task"] == "app.tasks.file_tasks.process_pending_files"
    
    print("✅ Beat schedule configured correctly")


def test_task_signatures():
    """Test task signatures and basic functionality"""
    print("Testing task signatures...")
    
    from app.tasks.file_tasks import process_file_upload
    from app.tasks.ai_tasks import create_ticket_with_ai
    from app.tasks.notification_tasks import send_email_notification
    
    # Test task signatures (without actually running them)
    file_task_id = str(uuid4())
    file_signature = process_file_upload.s(file_task_id, {"extract_text": True})
    assert file_signature.task == "app.tasks.file_tasks.process_file_upload"
    assert file_signature.args == (file_task_id, {"extract_text": True})
    
    # Test AI task signature
    ai_signature = create_ticket_with_ai.s(
        "Test user input", 
        str(uuid4()), 
        {"context": "test"}
    )
    assert ai_signature.task == "app.tasks.ai_tasks.create_ticket_with_ai"
    
    # Test notification task signature
    email_signature = send_email_notification.s(
        "test@example.com",
        "Test Subject",
        "Test Body"
    )
    assert email_signature.task == "app.tasks.notification_tasks.send_email_notification"
    
    print("✅ Task signatures working correctly")


def test_task_retry_configuration():
    """Test task retry configuration"""
    print("Testing task retry configuration...")
    
    from app.tasks.file_tasks import process_file_upload
    from app.tasks.ai_tasks import create_ticket_with_ai
    
    # Check retry configuration
    file_task = process_file_upload
    assert file_task.max_retries == 3
    assert file_task.retry_backoff == True
    
    ai_task = create_ticket_with_ai
    assert ai_task.max_retries == 3
    assert ai_task.retry_backoff == True
    
    print("✅ Task retry configuration correct")


def test_task_queue_routing():
    """Test task queue routing"""
    print("Testing task queue routing...")
    
    from app.celery_app import celery_app
    
    # Test route resolution
    file_task_route = celery_app.conf.task_routes.get("app.tasks.file_tasks.*")
    assert file_task_route["queue"] == "file_processing"
    
    ai_task_route = celery_app.conf.task_routes.get("app.tasks.ai_tasks.*")
    assert ai_task_route["queue"] == "ai_processing"
    
    integration_task_route = celery_app.conf.task_routes.get("app.tasks.integration_tasks.*")
    assert integration_task_route["queue"] == "integrations"
    
    notification_task_route = celery_app.conf.task_routes.get("app.tasks.notification_tasks.*")
    assert notification_task_route["queue"] == "notifications"
    
    print("✅ Task queue routing configured correctly")


def test_debug_task():
    """Test debug/health check task"""
    print("Testing debug task...")
    
    from app.celery_app import debug_task
    
    # Test debug task signature
    debug_signature = debug_task.s()
    assert debug_signature.task == "app.celery_app.debug_task"
    
    print("✅ Debug task configured correctly")


def test_task_helper_functions():
    """Test async helper functions (mock testing)"""
    print("Testing task helper functions...")
    
    # Import helper functions
    from app.tasks.file_tasks import _process_file_async
    from app.tasks.ai_tasks import _create_ticket_with_ai_async
    from app.tasks.notification_tasks import _send_email_async
    
    # These are async functions, so we just test they're importable
    assert callable(_process_file_async)
    assert callable(_create_ticket_with_ai_async)
    assert callable(_send_email_async)
    
    print("✅ Task helper functions accessible")


def test_task_chaining():
    """Test task chaining capabilities"""
    print("Testing task chaining...")
    
    from app.tasks.file_tasks import process_file_upload, analyze_file_content
    from celery import chain
    
    # Create a task chain
    file_id = str(uuid4())
    task_chain = chain(
        process_file_upload.s(file_id, {"extract_text": True}),
        analyze_file_content.s({"categorize_content": True})
    )
    
    assert len(task_chain.tasks) == 2
    assert task_chain.tasks[0].task == "app.tasks.file_tasks.process_file_upload"
    assert task_chain.tasks[1].task == "app.tasks.file_tasks.analyze_file_content"
    
    print("✅ Task chaining working correctly")


def test_task_groups():
    """Test task grouping capabilities"""
    print("Testing task groups...")
    
    from app.tasks.notification_tasks import send_email_notification
    from celery import group
    
    # Create a task group
    email_group = group(
        send_email_notification.s("user1@example.com", "Subject", "Body"),
        send_email_notification.s("user2@example.com", "Subject", "Body"),
        send_email_notification.s("user3@example.com", "Subject", "Body")
    )
    
    assert len(email_group.tasks) == 3
    for task in email_group.tasks:
        assert task.task == "app.tasks.notification_tasks.send_email_notification"
    
    print("✅ Task grouping working correctly")


if __name__ == "__main__":
    print("🚀 Starting Celery tasks validation tests...")
    
    # Run all tests
    test_celery_app_import()
    test_task_imports()
    test_task_registration()
    test_celery_configuration()
    test_beat_schedule()
    test_task_signatures()
    test_task_retry_configuration()
    test_task_queue_routing()
    test_debug_task()
    test_task_helper_functions()
    test_task_chaining()
    test_task_groups()
    
    print("✅ All Celery tasks validation tests completed!")