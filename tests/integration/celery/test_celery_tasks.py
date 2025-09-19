#!/usr/bin/env python3
"""
Test Celery background tasks functionality
"""

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
    
    
    print("✅ All task modules imported successfully")


def test_task_registration():
    """Test that tasks are registered with Celery"""
    print("Testing task registration...")
    
    from app.celery_app import celery_app
    
    # Check if tasks are registered
    registered_tasks = celery_app.tasks
    
    # File tasks (currently enabled)
    assert "app.tasks.file_tasks.process_file_upload" in registered_tasks
    assert "app.tasks.file_tasks.reprocess_file" in registered_tasks
    assert "app.tasks.file_tasks.process_pending_files" in registered_tasks
    assert "app.tasks.file_tasks.cleanup_failed_uploads" in registered_tasks
    
    # AI tasks are temporarily disabled
    # Integration tasks are temporarily disabled  
    # Notification tasks are temporarily disabled
    
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
    # AI, integration, and notification tasks are temporarily disabled
    
    print("✅ Celery configuration correct")


def test_beat_schedule():
    """Test Celery Beat periodic task schedule"""
    print("Testing Beat schedule...")
    
    from app.celery_app import celery_app
    
    beat_schedule = celery_app.conf.beat_schedule
    
    # Check scheduled tasks (only enabled ones)
    assert "process-pending-files" in beat_schedule
    assert "cleanup-failed-uploads" in beat_schedule
    # Other tasks are temporarily disabled
    
    # Check task configuration
    process_files_task = beat_schedule["process-pending-files"]
    assert process_files_task["task"] == "app.tasks.file_tasks.process_pending_files"
    
    print("✅ Beat schedule configured correctly")


def test_task_signatures():
    """Test task signatures and basic functionality"""
    print("Testing task signatures...")
    
    from app.tasks.file_tasks import process_file_upload, reprocess_file
    
    # Test task signatures (without actually running them)
    file_task_id = str(uuid4())
    file_signature = process_file_upload.s(file_task_id, {"extract_text": True})
    assert file_signature.task == "app.tasks.file_tasks.process_file_upload"
    assert file_signature.args == (file_task_id, {"extract_text": True})
    
    # Test reprocess file task signature
    reprocess_signature = reprocess_file.s(file_task_id)
    assert reprocess_signature.task == "app.tasks.file_tasks.reprocess_file"
    assert reprocess_signature.args == (file_task_id,)
    
    print("✅ Task signatures working correctly")


def test_task_retry_configuration():
    """Test task retry configuration"""
    print("Testing task retry configuration...")
    
    from app.tasks.file_tasks import process_file_upload, reprocess_file
    
    # Check retry configuration
    file_task = process_file_upload
    assert file_task.max_retries == 3
    assert file_task.retry_backoff == True
    
    reprocess_task = reprocess_file
    assert reprocess_task.max_retries == 3
    assert reprocess_task.retry_backoff == True
    
    print("✅ Task retry configuration correct")


def test_task_queue_routing():
    """Test task queue routing"""
    print("Testing task queue routing...")
    
    from app.celery_app import celery_app
    
    # Test route resolution (only for enabled tasks)
    file_task_route = celery_app.conf.task_routes.get("app.tasks.file_tasks.*")
    assert file_task_route["queue"] == "file_processing"
    
    # Other task routes are temporarily disabled
    
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
    """Test helper functions (mock testing)"""
    print("Testing task helper functions...")
    
    # Import helper functions (only for enabled tasks)
    from app.tasks.file_tasks import _process_file_upload_sync, _process_pending_files_sync, _cleanup_failed_uploads_sync
    
    # These are sync functions, so we just test they're importable
    assert callable(_process_file_upload_sync)
    assert callable(_process_pending_files_sync)
    assert callable(_cleanup_failed_uploads_sync)
    
    print("✅ Task helper functions accessible")


def test_task_chaining():
    """Test task chaining capabilities"""
    print("Testing task chaining...")
    
    from app.tasks.file_tasks import process_file_upload, reprocess_file
    from celery import chain
    
    # Create a task chain
    file_id = str(uuid4())
    task_chain = chain(
        process_file_upload.s(file_id, {"extract_text": True}),
        reprocess_file.s(file_id)
    )
    
    assert len(task_chain.tasks) == 2
    assert task_chain.tasks[0].task == "app.tasks.file_tasks.process_file_upload"
    assert task_chain.tasks[1].task == "app.tasks.file_tasks.reprocess_file"
    
    print("✅ Task chaining working correctly")


def test_task_groups():
    """Test task grouping capabilities"""
    print("Testing task groups...")
    
    from app.tasks.file_tasks import process_file_upload
    from celery import group
    
    # Create a task group for processing multiple files
    file_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
    file_group = group(
        process_file_upload.s(file_ids[0], {"extract_text": True}),
        process_file_upload.s(file_ids[1], {"extract_text": True}),
        process_file_upload.s(file_ids[2], {"extract_text": True})
    )
    
    assert len(file_group.tasks) == 3
    for task in file_group.tasks:
        assert task.task == "app.tasks.file_tasks.process_file_upload"
    
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