#!/usr/bin/env python3
"""
Task Cancellation Service - Cancel file processing tasks without storing task IDs
Uses Celery's built-in inspection and control features
"""

import logging
from typing import List, Dict, Any, Optional
from celery import current_app
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


class TaskCancellationService:
    """Service for cancelling file processing tasks using Celery inspection"""
    
    def __init__(self):
        self.celery = celery_app
    
    def cancel_file_processing_tasks(self, file_id: str) -> Dict[str, Any]:
        """
        Cancel all active processing tasks for a specific file ID
        
        Args:
            file_id: The file ID to cancel tasks for
            
        Returns:
            Dictionary with cancellation results
        """
        results = {
            "file_id": file_id,
            "cancelled_tasks": [],
            "failed_cancellations": [],
            "active_tasks_found": 0,
            "success": False
        }
        
        try:
            # Get Celery inspector
            inspector = self.celery.control.inspect()
            
            # Get active tasks from all workers
            active_tasks = inspector.active()
            
            if not active_tasks:
                logger.info(f"No active tasks found for file {file_id}")
                results["success"] = True
                return results
            
            # Find tasks processing this file
            tasks_to_cancel = []
            
            for worker, tasks in active_tasks.items():
                for task_info in tasks:
                    # Check if this task is processing our file
                    task_args = task_info.get('args', [])
                    task_name = task_info.get('name', '')
                    task_id = task_info.get('id', '')
                    
                    # Check for file processing tasks
                    if (task_name in ['app.tasks.file_tasks.process_file_upload', 
                                     'app.tasks.file_tasks.reprocess_file'] and 
                        task_args and str(task_args[0]) == str(file_id)):
                        
                        tasks_to_cancel.append({
                            'task_id': task_id,
                            'worker': worker,
                            'task_name': task_name
                        })
                        results["active_tasks_found"] += 1
            
            # Cancel the found tasks
            for task_info in tasks_to_cancel:
                try:
                    # Revoke the task
                    self.celery.control.revoke(
                        task_info['task_id'], 
                        terminate=True,  # Kill the task if it's already running
                        signal='SIGKILL'  # Force kill
                    )
                    
                    results["cancelled_tasks"].append({
                        'task_id': task_info['task_id'],
                        'worker': task_info['worker'],
                        'task_name': task_info['task_name']
                    })
                    
                    logger.info(f"Cancelled task {task_info['task_id']} for file {file_id}")
                    
                except Exception as e:
                    error_info = {
                        'task_id': task_info['task_id'],
                        'error': str(e)
                    }
                    results["failed_cancellations"].append(error_info)
                    logger.error(f"Failed to cancel task {task_info['task_id']}: {str(e)}")
            
            results["success"] = len(results["cancelled_tasks"]) > 0 or len(tasks_to_cancel) == 0
            
        except Exception as e:
            logger.error(f"Error during task cancellation for file {file_id}: {str(e)}")
            results["error"] = str(e)
        
        return results
    
    def cancel_all_file_tasks_by_pattern(self, file_ids: List[str]) -> Dict[str, Any]:
        """
        Cancel processing tasks for multiple files
        
        Args:
            file_ids: List of file IDs to cancel tasks for
            
        Returns:
            Dictionary with batch cancellation results
        """
        batch_results = {
            "total_files": len(file_ids),
            "files_processed": 0,
            "total_cancelled": 0,
            "file_results": {}
        }
        
        for file_id in file_ids:
            result = self.cancel_file_processing_tasks(file_id)
            batch_results["file_results"][file_id] = result
            batch_results["files_processed"] += 1
            batch_results["total_cancelled"] += len(result["cancelled_tasks"])
        
        return batch_results
    
    def get_active_file_processing_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all currently active file processing tasks
        
        Returns:
            Dictionary mapping file IDs to their active tasks
        """
        file_tasks = {}
        
        try:
            inspector = self.celery.control.inspect()
            active_tasks = inspector.active()
            
            if not active_tasks:
                return file_tasks
            
            for worker, tasks in active_tasks.items():
                for task_info in tasks:
                    task_args = task_info.get('args', [])
                    task_name = task_info.get('name', '')
                    
                    # Check for file processing tasks
                    if (task_name in ['app.tasks.file_tasks.process_file_upload', 
                                     'app.tasks.file_tasks.reprocess_file'] and 
                        task_args):
                        
                        file_id = str(task_args[0])
                        
                        if file_id not in file_tasks:
                            file_tasks[file_id] = []
                        
                        file_tasks[file_id].append({
                            'task_id': task_info.get('id'),
                            'worker': worker,
                            'task_name': task_name,
                            'started': task_info.get('time_start'),
                            'args': task_args
                        })
        
        except Exception as e:
            logger.error(f"Error getting active file processing tasks: {str(e)}")
        
        return file_tasks