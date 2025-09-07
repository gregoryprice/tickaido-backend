I want to completely redo the chat endpoints and the ai_chat_service and complete a PRP to do the following. The ai chat service will now use an organizations Agent or a specific agent to chat with. this agent will be the responsible for interfacing with the chat service. We will call conversations -> threads now as well for terminology change.  

1. I want to create a chat service that will be more extensible for many agents and to be more reliable for external chat api clients. 

2. I want to refactor POST /api/v1/chat/conversations to /api/v1/chat/{agent_id}/threads where you create a thread with an agent_id now because you will be chatting with an agent. The request body will be: 

request: 
"agent_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "title": "string",
  "metadata": {}, 
  
response will be:
{
  "id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "agent_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "user_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "organization_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "title": "<string>",
  "metadata": {},
  "created_at": "2023-11-07T05:31:56Z",
  "updated_at": "2023-11-07T05:31:56Z",
  "archived": "false",
  "messages": [
    {
      "id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
      "thread_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
      "content": "<string>",
      "content_html": "<string>",
      "role": "<string>",
      "tool_calls": [
        {
          "tool_name": "<string>",
          "arguments": {},
          "result": {},
          "error": "<string>",
          "start_time": "2023-11-07T05:31:56Z",
          "end_time": "2023-11-07T05:31:56Z"
        }
      ],
      "attachments": [
        {}
      ],
      "metadata": {},
      "created_at": "2023-11-07T05:31:56Z",
    }
  ]
}

3. I want to refactor GET /api/v1/chat/conversations, to /api/v1/chat/{agent_id}/threads. This gets all threads for a specific organization, and agent_id.  Has limit and offset query params limit
integerdefault:10
Number of threads to return

Required range: 1 <= x <= 50
​
offset
integerdefault:0
Number of threads to skip

archived: boolean (returns all threads (archived/unarchived) if nothing selected, returns only archived threads if true, returns only unarchived threads if false)

Required range: x >= 0, 

The response will be a list of threads: 
[ {
  "id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "agent_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "user_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "organization_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "title": "<string>",
  "metadata": {},
  "created_at": "2023-11-07T05:31:56Z",
  "updated_at": "2023-11-07T05:31:56Z",
  "archived": "false",
  "messages": [
    {
      "id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
      "thread_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
      "content": "<string>",
      "content_html": "<string>",
      "role": "<string>",
      "tool_calls": [
        {
          "tool_name": "<string>",
          "arguments": {},
          "result": {},
          "error": "<string>",
          "start_time": "2023-11-07T05:31:56Z",
          "end_time": "2023-11-07T05:31:56Z"
        }
      ],
      "attachments": [
        {}
      ],
      "metadata": {},
      "created_at": "2023-11-07T05:31:56Z",
    }
  ]
}]

4. Refactor DELETE /api/v1/chat/conversations/{conversation_id} to DELETE /api/v1/chat/{agent_id}/threads/{thread_id}

5. Refactor GET /api/v1/chat/conversations/{conversation_id}/messages to api/v1/chat/{agent_id}/threads/{thread_id}
 query parameters (optional) message_limit
integerdefault:50
Number of messages to return (returns the message_limit latest messages by created_at date), Required range: 1 <= x <= 100

returns the thread with the same response body as the GET thread

6. Refactor POST /api/v1/chat/conversations/{conversation_id}/messages to POST /api/v1/chat/{agent_id}/threads/{thread_id}/messages

request body is: 
{
  "content": "<string>",
  "content_html": "<string>",
  "role": "<string>",
  "metadata": {}
}

response is: 

{
  "id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "thread_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
  "content": "<string>",
  "content_html": "<string>",
  "role": "<string>",
  "tool_calls": [
    {
      "tool_name": "<string>",
      "arguments": {},
      "result": {},
      "error": "<string>",
      "start_time": "2023-11-07T05:31:56Z",
      "end_time": "2023-11-07T05:31:56Z"
    }
  ],
  "attachments": [
    {}
  ],
  "metadata": {},
  "created_at": "2023-11-07T05:31:56Z"
}


7. Refactor PATCH /api/v1/chat/conversations/{conversation_id} to PATCH /api/v1/chat/{agent_id}/threads/{thread_id}

request body:

{
  "title": "string",
  "archived": true
}

You can update a thread title and if it is archived or not

response body: 

same as the GET /api/v1/chat/{agent_id}/threads/{thread_id} response body

8. Refactor POST /api/v1/chat/conversations/{conversation_id}/generate_title to POST /api/v1/chat/{agent_id}/threads/{thread_id}/generate_title

this will generate a title from the thread messages and automatically update the thread title


Functionality requirements

1. An agent must get created in order to create a thread (e.g. if an agent doesn't exist then you can call the endpoint)
2. When a thread is created, the agent_id will be the agent to respond on the thread. It will also have access to the mcp_client which will be able to call the mcp_server. The tools the mcp_client calls will be recorded in to the message / tools and in the "tool_calls": [
        {
          "tool_name": "<string>",
          "arguments": {},
          "result": {},
          "error": "<string>",
          "start_time": "2023-11-07T05:31:56Z",
          "end_time": "2023-11-07T05:31:56Z"
        } part of the message in the thread

3. attachments need to use the file system and the appropriate storage. When a user uploads an attachment, they need to call the the file sysetm processing which extracts the context, and then can use that information in the context window of the agent

4. Outline the rest of the steps needed to make the changes to the ai_chat_service.py

