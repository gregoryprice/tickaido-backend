# Bulk Operations PRD

## Overview

This document outlines the implementation of bulk ticket operations functionality, allowing users to perform actions on multiple tickets simultaneously with real-time status tracking and cancellation capabilities.

## User Requirements

1. **Bulk Actions**: Users can select multiple tickets and perform batch operations:
   - Update ticket status
   - Add comments to multiple tickets
   - Change assigned party
   - Update priority or category
   - Delete multiple tickets

2. **Operation Tracking**: Users can monitor the progress of bulk operations in real-time

3. **Cancellation**: Users can cancel in-progress bulk operations

## Proposed API Endpoints

### 1. Create Bulk Operation
```http
POST /api/v1/tickets/bulk-operations
Authorization: Bearer <token>
Content-Type: application/json

{
  "ticket_ids": [1, 2, 3, 4, 5],
  "operation_type": "update_status",
  "operation_data": {
    "status": "resolved"
  },
  "metadata": {
    "description": "Marking resolved tickets as closed"
  }
}
```

**Response:**
```json
{
  "operation_id": "bulk_op_12345",
  "status": "pending",
  "ticket_count": 5,
  "created_at": "2025-09-26T10:00:00Z",
  "estimated_completion": "2025-09-26T10:02:00Z"
}
```

### 2. Get Bulk Operation Status
```http
GET /api/v1/tickets/bulk-operations/{operation_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "operation_id": "bulk_op_12345",
  "status": "in_progress",
  "operation_type": "update_status",
  "total_tickets": 5,
  "processed_tickets": 3,
  "successful_tickets": 2,
  "failed_tickets": 1,
  "progress_percentage": 60,
  "created_at": "2025-09-26T10:00:00Z",
  "started_at": "2025-09-26T10:00:15Z",
  "estimated_completion": "2025-09-26T10:01:30Z",
  "errors": [
    {
      "ticket_id": 3,
      "error_message": "Insufficient permissions to update ticket"
    }
  ]
}
```

### 3. Cancel Bulk Operation
```http
POST /api/v1/tickets/bulk-operations/{operation_id}/cancel
Authorization: Bearer <token>
```

**Response:**
```json
{
  "operation_id": "bulk_op_12345",
  "status": "cancelled",
  "processed_tickets": 3,
  "cancelled_at": "2025-09-26T10:01:00Z"
}
```

### 4. List User's Bulk Operations
```http
GET /api/v1/tickets/bulk-operations?status=in_progress&limit=10&offset=0
Authorization: Bearer <token>
```

**Response:**
```json
{
  "operations": [
    {
      "operation_id": "bulk_op_12345",
      "status": "completed",
      "operation_type": "update_status",
      "total_tickets": 5,
      "successful_tickets": 4,
      "failed_tickets": 1,
      "created_at": "2025-09-26T10:00:00Z",
      "completed_at": "2025-09-26T10:02:15Z"
    }
  ],
  "total": 1,
  "has_more": false
}
```

### 5. WebSocket Updates
```
WS /ws/bulk-operations/{operation_id}
Authorization: Bearer <token>
```

**Real-time messages:**
```json
{
  "type": "progress_update",
  "operation_id": "bulk_op_12345",
  "processed_tickets": 4,
  "progress_percentage": 80,
  "current_ticket_id": 5,
  "timestamp": "2025-09-26T10:01:45Z"
}

{
  "type": "operation_completed",
  "operation_id": "bulk_op_12345",
  "final_status": "completed",
  "successful_tickets": 4,
  "failed_tickets": 1,
  "completed_at": "2025-09-26T10:02:15Z"
}
```

## User Experience Flow

### 1. Initiate Bulk Operation
1. User selects multiple tickets in the UI (checkbox selection)
2. User chooses bulk action from dropdown menu
3. User fills in operation-specific form (e.g., new status, comment text)
4. User confirms the operation
5. System displays operation ID and initial status

### 2. Monitor Progress
1. User navigates to bulk operations page or receives real-time updates
2. Progress bar shows completion percentage
3. Real-time list shows processed vs remaining tickets
4. Error messages displayed for failed operations
5. User can view detailed logs

### 3. Cancel Operation (if needed)
1. User clicks "Cancel Operation" button
2. System confirms cancellation intent
3. Operation stops processing remaining tickets
4. System shows final status with partial results

## Architecture Implementation

### Database Schema

#### BulkOperation Model
```python
class BulkOperation(Base):
    __tablename__ = "bulk_operations"
    
    id = Column(String, primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operation_type = Column(String, nullable=False)  # update_status, add_comment, etc.
    operation_data = Column(JSON, nullable=False)
    status = Column(String, default="pending")  # pending, in_progress, completed, cancelled, failed
    total_tickets = Column(Integer, nullable=False)
    processed_tickets = Column(Integer, default=0)
    successful_tickets = Column(Integer, default=0)
    failed_tickets = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    metadata = Column(JSON, nullable=True)
```

#### BulkOperationTicket Model
```python
class BulkOperationTicket(Base):
    __tablename__ = "bulk_operation_tickets"
    
    id = Column(Integer, primary_key=True)
    bulk_operation_id = Column(String, ForeignKey("bulk_operations.id"), nullable=False)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    bulk_operation = relationship("BulkOperation", back_populates="operation_tickets")
    ticket = relationship("Ticket")
```

### Service Layer

#### BulkOperationService
```python
class BulkOperationService:
    async def create_bulk_operation(
        self, 
        user_id: int, 
        ticket_ids: List[int], 
        operation_type: str, 
        operation_data: dict,
        metadata: dict = None
    ) -> BulkOperation
    
    async def get_bulk_operation(self, operation_id: str, user_id: int) -> BulkOperation
    
    async def cancel_bulk_operation(self, operation_id: str, user_id: int) -> BulkOperation
    
    async def list_bulk_operations(
        self, 
        user_id: int, 
        status: str = None, 
        limit: int = 10, 
        offset: int = 0
    ) -> List[BulkOperation]
```

### Celery Task Implementation

#### Background Task Processor
```python
@celery_app.task(bind=True)
async def process_bulk_operation(self, operation_id: str):
    """
    Process bulk operation asynchronously with progress tracking
    """
    operation = await bulk_operation_service.get_bulk_operation(operation_id)
    
    # Update status to in_progress
    await bulk_operation_service.update_status(operation_id, "in_progress")
    
    # Process each ticket
    for ticket_entry in operation.operation_tickets:
        if operation.status == "cancelled":
            break
            
        try:
            # Process individual ticket based on operation_type
            await process_ticket_operation(
                ticket_entry.ticket_id, 
                operation.operation_type, 
                operation.operation_data
            )
            
            # Update progress
            await bulk_operation_service.update_ticket_status(
                operation_id, 
                ticket_entry.ticket_id, 
                "completed"
            )
            
            # Send WebSocket update
            await websocket_manager.send_progress_update(operation_id, {
                "processed_tickets": operation.processed_tickets + 1,
                "progress_percentage": calculate_progress(operation)
            })
            
        except Exception as e:
            await bulk_operation_service.update_ticket_status(
                operation_id, 
                ticket_entry.ticket_id, 
                "failed", 
                str(e)
            )
    
    # Mark operation as completed
    await bulk_operation_service.update_status(operation_id, "completed")
```

### WebSocket Manager

#### Real-time Updates
```python
class BulkOperationWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, operation_id: str):
        await websocket.accept()
        if operation_id not in self.active_connections:
            self.active_connections[operation_id] = []
        self.active_connections[operation_id].append(websocket)
    
    async def disconnect(self, websocket: WebSocket, operation_id: str):
        if operation_id in self.active_connections:
            self.active_connections[operation_id].remove(websocket)
    
    async def send_progress_update(self, operation_id: str, data: dict):
        if operation_id in self.active_connections:
            message = {
                "type": "progress_update",
                "operation_id": operation_id,
                **data
            }
            
            for connection in self.active_connections[operation_id]:
                try:
                    await connection.send_json(message)
                except:
                    # Remove disconnected clients
                    self.active_connections[operation_id].remove(connection)
```

## Testing Strategy

### Unit Tests

#### Service Tests
```python
class TestBulkOperationService:
    async def test_create_bulk_operation(self):
        # Test operation creation with valid data
        
    async def test_create_bulk_operation_invalid_tickets(self):
        # Test with non-existent ticket IDs
        
    async def test_cancel_bulk_operation(self):
        # Test cancellation functionality
        
    async def test_get_operation_unauthorized(self):
        # Test access control
```

#### Task Tests
```python
class TestBulkOperationTasks:
    async def test_process_bulk_operation_success(self):
        # Test successful bulk processing
        
    async def test_process_bulk_operation_partial_failure(self):
        # Test handling of some failed tickets
        
    async def test_process_bulk_operation_cancellation(self):
        # Test mid-operation cancellation
```

### Integration Tests

#### API Endpoint Tests
```python
class TestBulkOperationAPI:
    async def test_create_bulk_operation_endpoint(self):
        # Test POST /api/v1/tickets/bulk-operations
        
    async def test_get_bulk_operation_status(self):
        # Test GET /api/v1/tickets/bulk-operations/{id}
        
    async def test_cancel_bulk_operation_endpoint(self):
        # Test POST /api/v1/tickets/bulk-operations/{id}/cancel
        
    async def test_websocket_progress_updates(self):
        # Test real-time WebSocket updates
```

### End-to-End Tests

#### Full Flow Tests
```python
class TestBulkOperationE2E:
    async def test_complete_bulk_update_flow(self):
        # Test: Create operation -> Monitor progress -> Verify completion
        
    async def test_bulk_operation_with_cancellation(self):
        # Test: Create operation -> Cancel -> Verify partial completion
        
    async def test_bulk_operation_error_handling(self):
        # Test: Create operation with some invalid tickets -> Verify error handling
```

## Performance Considerations

### Scalability
- **Chunked Processing**: Process tickets in batches to avoid memory issues
- **Rate Limiting**: Prevent users from creating too many concurrent operations
- **Database Indexing**: Index on user_id, status, and created_at for efficient queries
- **WebSocket Optimization**: Batch progress updates to reduce message frequency

### Error Handling
- **Retry Logic**: Retry failed ticket operations with exponential backoff
- **Partial Success**: Continue processing even if some tickets fail
- **Timeout Handling**: Set reasonable timeouts for individual ticket operations
- **Resource Cleanup**: Clean up resources if operation is cancelled

## Security Considerations

### Authorization
- Users can only perform bulk operations on tickets they have access to
- Validate ticket permissions before starting bulk operation
- Rate limit bulk operation creation per user

### Data Validation
- Validate all operation data before processing
- Sanitize input to prevent injection attacks
- Verify ticket ownership and permissions for each operation

## Monitoring and Logging

### Metrics
- Track bulk operation success/failure rates
- Monitor processing times and performance
- Alert on high failure rates or long processing times

### Logging
- Log all bulk operation lifecycle events
- Track individual ticket processing results
- Maintain audit trail for compliance

## Future Enhancements

1. **Scheduled Bulk Operations**: Allow users to schedule bulk operations for later
2. **Operation Templates**: Save common bulk operation configurations
3. **Advanced Filtering**: Allow bulk operations on filtered ticket sets
4. **Bulk Operation History**: Detailed history and rollback capabilities
5. **Import/Export**: Bulk operations via CSV import/export