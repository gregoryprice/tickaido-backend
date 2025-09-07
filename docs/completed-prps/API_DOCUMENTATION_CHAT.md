# Chat Assistant API Documentation

This document provides comprehensive documentation for the Chat Assistant API, including REST endpoints and WebSocket streaming functionality.

## Overview

The Chat Assistant API provides real-time AI chat capabilities with full conversation management. It features:

- **6 REST API endpoints** for full CRUD operations
- **WebSocket streaming** for real-time AI responses
- **JWT authentication** with user ownership validation
- **Conversation management** with soft delete functionality
- **Message persistence** with role-based storage

## Base URL

```
Local Development: http://localhost:8000
WebSocket: ws://localhost:8000
```

## Authentication

All endpoints require JWT authentication via the `Authorization` header:

```
Authorization: Bearer {your_jwt_token}
```

For WebSocket connections, pass the token as a query parameter:

```
ws://localhost:8000/api/v1/ws/chat/stream/{conversation_id}?token={your_jwt_token}
```

## REST API Endpoints

### 1. List Conversations

**GET** `/api/v1/chat/conversations`

Retrieve paginated list of conversations for the authenticated user (excluding deleted ones).

**Headers:**
- `Authorization: Bearer {token}` (required)

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Customer Support Chat",
    "total_messages": 5,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:00:00Z",
    "is_deleted": false
  }
]
```

### 2. Create Conversation

**POST** `/api/v1/chat/conversations`

Create a new conversation for the authenticated user.

**Headers:**
- `Authorization: Bearer {token}` (required)
- `Content-Type: application/json`

**Request Body:**
```json
{
  "title": "New Support Chat"  // optional
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "New Support Chat",
  "total_messages": 0,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "is_deleted": false
}
```

### 3. Get Conversation Messages

**GET** `/api/v1/chat/conversations/{conversation_id}/messages`

Retrieve all messages for a conversation with ownership validation.

**Headers:**
- `Authorization: Bearer {token}` (required)

**Path Parameters:**
- `conversation_id` (UUID, required) - Conversation ID

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "role": "user",
    "content": "Hello, I need help with my account",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "is_deleted": false
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "role": "assistant",
    "content": "I'd be happy to help you with your account. What specific issue are you experiencing?",
    "created_at": "2024-01-15T10:30:05Z",
    "updated_at": "2024-01-15T10:30:05Z",
    "is_deleted": false
  }
]
```

### 4. Send Message

**POST** `/api/v1/chat/conversations/{conversation_id}/messages`

Send a user message to a conversation with ownership validation.

**Headers:**
- `Authorization: Bearer {token}` (required)
- `Content-Type: application/json`

**Path Parameters:**
- `conversation_id` (UUID, required) - Conversation ID

**Request Body:**
```json
{
  "message": "I have a question about billing"
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "role": "user",
  "content": "I have a question about billing",
  "created_at": "2024-01-15T10:35:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "is_deleted": false
}
```

### 5. Update Conversation Title

**PATCH** `/api/v1/chat/conversations/{conversation_id}/title`

Update the title of a conversation with ownership validation.

**Headers:**
- `Authorization: Bearer {token}` (required)
- `Content-Type: application/json`

**Path Parameters:**
- `conversation_id` (UUID, required) - Conversation ID

**Request Body:**
```json
{
  "title": "Updated Chat Title"
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Updated Chat Title",
  "total_messages": 3,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:40:00Z",
  "is_deleted": false
}
```

### 6. Delete Conversation

**DELETE** `/api/v1/chat/conversations/{conversation_id}`

Delete a conversation (soft delete) with ownership validation.

**Headers:**
- `Authorization: Bearer {token}` (required)

**Path Parameters:**
- `conversation_id` (UUID, required) - Conversation ID

**Response:** `200 OK`
```json
{
  "detail": "Conversation deleted successfully"
}
```

## WebSocket API

### Connection

**URL:** `ws://localhost:8000/api/v1/ws/chat/stream/{conversation_id}?token={jwt_token}`

**Authentication:** JWT token passed as query parameter

**Connection Flow:**
1. Client connects with valid JWT token
2. Server validates user ownership of conversation
3. Server sends `connection_established` message
4. Client can send/receive real-time messages

### Message Types

#### Client → Server Messages

##### Send Message
```json
{
  "type": "send_message",
  "data": {
    "message": "Hello, how can I help you?"
  }
}
```

##### Ping (Health Check)
```json
{
  "type": "ping",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Server → Client Messages

##### Connection Established
```json
{
  "type": "connection_established",
  "data": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user-123",
    "supported_features": ["real_time_messaging", "ai_streaming"]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

##### User Message Sent
```json
{
  "type": "user_message_sent",
  "data": {
    "message_id": "550e8400-e29b-41d4-a716-446655440001",
    "content": "Hello, how can I help you?",
    "role": "user",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

##### AI Response Start
```json
{
  "type": "ai_response_start",
  "data": {
    "message": "AI is generating response..."
  }
}
```

##### AI Response Chunk (Streaming)
```json
{
  "type": "ai_response_chunk",
  "data": {
    "content": "I understand your message.",
    "is_complete": false,
    "word_count": 4
  }
}
```

##### AI Response Complete
```json
{
  "type": "ai_response_complete",
  "data": {
    "message_id": "550e8400-e29b-41d4-a716-446655440002",
    "content": "I understand your message. Let me help you with that.",
    "role": "assistant",
    "created_at": "2024-01-15T10:30:05Z",
    "total_words": 10
  }
}
```

##### Pong Response
```json
{
  "type": "pong",
  "timestamp": "2024-01-15T10:30:01Z"
}
```

##### Error Messages
```json
{
  "type": "error",
  "data": {
    "error_code": "INVALID_JSON",
    "error_message": "Invalid JSON format"
  }
}
```

## Error Responses

### HTTP Error Codes

- **403 Forbidden**: Authentication required or invalid token
- **404 Not Found**: Conversation not found or not accessible
- **422 Unprocessable Entity**: Invalid request data

### WebSocket Error Codes

- **INVALID_JSON**: Malformed JSON message
- **UNKNOWN_MESSAGE_TYPE**: Unsupported message type
- **MISSING_MESSAGE**: Required message content missing
- **MESSAGE_SEND_FAILED**: Failed to send message
- **AI_RESPONSE_FAILED**: Failed to generate AI response
- **SERVER_ERROR**: Internal server error

## Usage Examples

### Complete Chat Flow (REST + WebSocket)

1. **Authenticate and create conversation:**
   ```bash
   # Login to get JWT token
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com","password":"password"}'
   
   # Create conversation
   curl -X POST http://localhost:8000/api/v1/chat/conversations \
     -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title":"Support Chat"}'
   ```

2. **Connect via WebSocket:**
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/api/v1/ws/chat/stream/CONVERSATION_ID?token=JWT_TOKEN');
   
   ws.onmessage = (event) => {
     const message = JSON.parse(event.data);
     console.log('Received:', message);
   };
   
   // Send message
   ws.send(JSON.stringify({
     type: 'send_message',
     data: { message: 'Hello!' }
   }));
   ```

3. **Retrieve conversation history:**
   ```bash
   curl -X GET http://localhost:8000/api/v1/chat/conversations/CONVERSATION_ID/messages \
     -H "Authorization: Bearer $JWT_TOKEN"
   ```

## Security Features

- **User Ownership Validation**: All operations validate that the user owns the conversation
- **JWT Authentication**: All endpoints require valid JWT tokens
- **Soft Delete**: Deleted conversations are not permanently removed
- **Input Validation**: All requests are validated using Pydantic schemas
- **Rate Limiting**: WebSocket connections include rate limiting protection

## Testing with Postman

1. Import the collection from `docs/postman/AI_Ticket_Creator_API.postman_collection.json`
2. Set environment variables:
   - `BASE_URL`: `http://localhost:8000`
   - `USER_EMAIL`: Your test email
   - `USER_PASSWORD`: Your test password
3. Run the Login request to populate `ACCESS_TOKEN`
4. Run Create Conversation to populate `CONVERSATION_ID`
5. Test all Chat Assistant endpoints

For WebSocket testing, use a WebSocket client like:
- Postman's WebSocket support
- Browser developer tools
- `wscat` command line tool

## Integration Notes

- The Chat Assistant integrates with the existing user authentication system
- All conversations are isolated by user ID
- Messages are persisted to the database for conversation history
- WebSocket connections are stateless and can be reconnected
- AI responses are generated using the same AI service used for ticket creation

## Rate Limits

- WebSocket connections: 100 messages per minute per user
- REST API: Standard rate limits apply (defined in middleware)
- Connection limits: 10 concurrent WebSocket connections per user