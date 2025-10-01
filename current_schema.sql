--
-- PostgreSQL database dump
--

\restrict 4gMemcXX4vbG40HCGI2yygik3kbgnYbcJJiUK3L8gqeEYhompQ1h4kzvz2BPBbQ

-- Dumped from database version 15.14 (Debian 15.14-1.pgdg13+1)
-- Dumped by pg_dump version 15.14 (Debian 15.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: aiagenttype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.aiagenttype AS ENUM (
    'CUSTOMER_SUPPORT',
    'CATEGORIZATION',
    'FILE_ANALYSIS',
    'TITLE_GENERATION',
    'SENTIMENT_ANALYSIS',
    'ROUTING',
    'ESCALATION',
    'SUMMARY',
    'TRANSLATION'
);


--
-- Name: filestatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.filestatus AS ENUM (
    'UPLOADED',
    'PROCESSING',
    'PROCESSED',
    'FAILED',
    'QUARANTINED',
    'DELETED'
);


--
-- Name: filetype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.filetype AS ENUM (
    'DOCUMENT',
    'IMAGE',
    'AUDIO',
    'VIDEO',
    'SPREADSHEET',
    'PRESENTATION',
    'ARCHIVE',
    'TEXT',
    'CODE',
    'OTHER'
);


--
-- Name: integrationcategory; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.integrationcategory AS ENUM (
    'ticketing',
    'crm',
    'messaging',
    'communication',
    'project_management',
    'code_repository',
    'webhook'
);


--
-- Name: integrationstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.integrationstatus AS ENUM (
    'active',
    'inactive',
    'pending',
    'error',
    'expired',
    'suspended'
);


--
-- Name: invitationstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.invitationstatus AS ENUM (
    'PENDING',
    'ACCEPTED',
    'DECLINED',
    'EXPIRED',
    'CANCELLED'
);


--
-- Name: organizationrole; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.organizationrole AS ENUM (
    'ADMIN',
    'MEMBER'
);


--
-- Name: ticketcategory; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.ticketcategory AS ENUM (
    'technical',
    'billing',
    'feature_request',
    'bug',
    'user_access',
    'general',
    'integration',
    'performance',
    'security'
);


--
-- Name: ticketpriority; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.ticketpriority AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);


--
-- Name: ticketstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.ticketstatus AS ENUM (
    'new',
    'open',
    'in_progress',
    'pending',
    'resolved',
    'closed',
    'cancelled'
);


--
-- Name: userrole; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.userrole AS ENUM (
    'ADMIN',
    'MEMBER'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_actions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_actions (
    agent_id uuid NOT NULL,
    action_type character varying(50) NOT NULL,
    action_subtype character varying(50),
    action_data json NOT NULL,
    action_context json,
    result_data json,
    success boolean NOT NULL,
    error_message text,
    execution_time_ms integer NOT NULL,
    tokens_used integer,
    cost_cents numeric(10,4),
    confidence_score numeric(5,4),
    quality_score numeric(5,4),
    user_feedback_score integer,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone NOT NULL,
    user_id uuid,
    session_id character varying(255),
    conversation_id character varying(255),
    source_channel character varying(50),
    source_reference character varying(255),
    ip_address character varying(45),
    user_agent text,
    tools_used json,
    integration_calls json,
    input_length integer,
    output_length integer,
    media_processed json,
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT ck_agent_action_confidence_score CHECK (((confidence_score IS NULL) OR ((confidence_score >= 0.0) AND (confidence_score <= 1.0)))),
    CONSTRAINT ck_agent_action_quality_score CHECK (((quality_score IS NULL) OR ((quality_score >= 0.0) AND (quality_score <= 1.0)))),
    CONSTRAINT ck_agent_action_user_feedback CHECK (((user_feedback_score IS NULL) OR ((user_feedback_score >= 1) AND (user_feedback_score <= 5))))
);


--
-- Name: TABLE agent_actions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.agent_actions IS 'Agent action tracking with performance metrics and analytics';


--
-- Name: COLUMN agent_actions.agent_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.agent_id IS 'Agent that performed the action';


--
-- Name: COLUMN agent_actions.action_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.action_type IS 'Type of action (chat_response, ticket_creation, tool_call, etc.)';


--
-- Name: COLUMN agent_actions.action_subtype; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.action_subtype IS 'Subtype for more specific action categorization';


--
-- Name: COLUMN agent_actions.action_data; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.action_data IS 'Input data and parameters for the action';


--
-- Name: COLUMN agent_actions.action_context; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.action_context IS 'Context information (conversation ID, user info, etc.)';


--
-- Name: COLUMN agent_actions.result_data; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.result_data IS 'Action results and outputs';


--
-- Name: COLUMN agent_actions.success; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.success IS 'Whether the action completed successfully';


--
-- Name: COLUMN agent_actions.error_message; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.error_message IS 'Error message if action failed';


--
-- Name: COLUMN agent_actions.execution_time_ms; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.execution_time_ms IS 'Execution time in milliseconds';


--
-- Name: COLUMN agent_actions.tokens_used; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.tokens_used IS 'Number of AI model tokens consumed';


--
-- Name: COLUMN agent_actions.cost_cents; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.cost_cents IS 'Estimated cost in cents for the action';


--
-- Name: COLUMN agent_actions.confidence_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.confidence_score IS 'Agent confidence in the action result (0.0 to 1.0)';


--
-- Name: COLUMN agent_actions.quality_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.quality_score IS 'Quality assessment score (0.0 to 1.0)';


--
-- Name: COLUMN agent_actions.user_feedback_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.user_feedback_score IS 'User feedback score (1-5 stars) if available';


--
-- Name: COLUMN agent_actions.started_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.started_at IS 'When the action started';


--
-- Name: COLUMN agent_actions.completed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.completed_at IS 'When the action completed';


--
-- Name: COLUMN agent_actions.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.user_id IS 'User who triggered the action (if applicable)';


--
-- Name: COLUMN agent_actions.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.session_id IS 'Session ID for grouping related actions';


--
-- Name: COLUMN agent_actions.conversation_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.conversation_id IS 'Conversation ID for chat-related actions';


--
-- Name: COLUMN agent_actions.source_channel; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.source_channel IS 'Channel that triggered the action (api, slack, email, etc.)';


--
-- Name: COLUMN agent_actions.source_reference; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.source_reference IS 'External reference ID';


--
-- Name: COLUMN agent_actions.ip_address; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.ip_address IS 'IP address of the request (if applicable)';


--
-- Name: COLUMN agent_actions.user_agent; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.user_agent IS 'User agent string (if from web request)';


--
-- Name: COLUMN agent_actions.tools_used; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.tools_used IS 'List of tools/integrations used in the action';


--
-- Name: COLUMN agent_actions.integration_calls; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.integration_calls IS 'External API calls made during action';


--
-- Name: COLUMN agent_actions.input_length; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.input_length IS 'Length of input content in characters';


--
-- Name: COLUMN agent_actions.output_length; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.output_length IS 'Length of output content in characters';


--
-- Name: COLUMN agent_actions.media_processed; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.media_processed IS 'Information about processed media files';


--
-- Name: COLUMN agent_actions.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.notes IS 'Internal notes';


--
-- Name: COLUMN agent_actions.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_actions.extra_metadata IS 'JSON metadata storage';


--
-- Name: agent_files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_files (
    agent_id uuid NOT NULL,
    file_id uuid NOT NULL,
    processing_status character varying(20) NOT NULL,
    extracted_content text,
    content_hash character varying(64),
    content_length integer,
    order_index integer NOT NULL,
    priority character varying(10) NOT NULL,
    processing_started_at timestamp with time zone,
    processing_completed_at timestamp with time zone,
    processing_error text,
    attached_at timestamp with time zone NOT NULL,
    attached_by_user_id uuid,
    last_used_in_context timestamp with time zone,
    usage_count integer NOT NULL,
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT ck_agent_file_priority CHECK (((priority)::text = ANY ((ARRAY['high'::character varying, 'normal'::character varying, 'low'::character varying])::text[]))),
    CONSTRAINT ck_agent_file_processing_status CHECK (((processing_status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: TABLE agent_files; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.agent_files IS 'Agent file relationships with processing status and context metadata';


--
-- Name: COLUMN agent_files.agent_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.agent_id IS 'Agent this file belongs to';


--
-- Name: COLUMN agent_files.file_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.file_id IS 'File attached to agent';


--
-- Name: COLUMN agent_files.processing_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.processing_status IS 'Processing status (pending, processing, completed, failed)';


--
-- Name: COLUMN agent_files.extracted_content; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.extracted_content IS 'Text content extracted from file for agent context';


--
-- Name: COLUMN agent_files.content_hash; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.content_hash IS 'SHA-256 hash of extracted content for deduplication';


--
-- Name: COLUMN agent_files.content_length; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.content_length IS 'Length of extracted content in characters';


--
-- Name: COLUMN agent_files.order_index; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.order_index IS 'Order of file in agent context (0 = first)';


--
-- Name: COLUMN agent_files.priority; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.priority IS 'File priority for context inclusion (high, normal, low)';


--
-- Name: COLUMN agent_files.processing_started_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.processing_started_at IS 'When processing started';


--
-- Name: COLUMN agent_files.processing_completed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.processing_completed_at IS 'When processing completed';


--
-- Name: COLUMN agent_files.processing_error; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.processing_error IS 'Error message if processing failed';


--
-- Name: COLUMN agent_files.attached_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.attached_at IS 'When file was attached to agent';


--
-- Name: COLUMN agent_files.attached_by_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.attached_by_user_id IS 'User who attached the file';


--
-- Name: COLUMN agent_files.last_used_in_context; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.last_used_in_context IS 'When this file was last used in agent context';


--
-- Name: COLUMN agent_files.usage_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.usage_count IS 'Number of times file content was used in context';


--
-- Name: COLUMN agent_files.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.notes IS 'Internal notes';


--
-- Name: COLUMN agent_files.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.extra_metadata IS 'JSON metadata storage';


--
-- Name: agent_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_history (
    agent_id uuid NOT NULL,
    changed_by_user_id uuid NOT NULL,
    change_type character varying(50) NOT NULL,
    field_changed character varying(100) NOT NULL,
    old_value text,
    new_value text,
    change_timestamp timestamp with time zone NOT NULL,
    change_reason text,
    ip_address character varying(45),
    request_metadata text,
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: COLUMN agent_history.agent_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.agent_id IS 'Agent this history entry belongs to';


--
-- Name: COLUMN agent_history.changed_by_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.changed_by_user_id IS 'User who made the change';


--
-- Name: COLUMN agent_history.change_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.change_type IS 'Type of change (configuration_update, status_change, activation, etc.)';


--
-- Name: COLUMN agent_history.field_changed; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.field_changed IS 'Field that was changed (prompt, role, is_active, etc.)';


--
-- Name: COLUMN agent_history.old_value; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.old_value IS 'Previous value (JSON for complex fields)';


--
-- Name: COLUMN agent_history.new_value; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.new_value IS 'New value (JSON for complex fields)';


--
-- Name: COLUMN agent_history.change_timestamp; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.change_timestamp IS 'When the change occurred';


--
-- Name: COLUMN agent_history.change_reason; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.change_reason IS 'Optional reason for the change';


--
-- Name: COLUMN agent_history.ip_address; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.ip_address IS 'IP address of the request that made the change';


--
-- Name: COLUMN agent_history.request_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.request_metadata IS 'Additional request metadata (user agent, etc.)';


--
-- Name: COLUMN agent_history.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.notes IS 'Internal notes';


--
-- Name: COLUMN agent_history.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.extra_metadata IS 'JSON metadata storage';


--
-- Name: agent_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_tasks (
    agent_id uuid NOT NULL,
    task_type character varying(50) NOT NULL,
    task_subtype character varying(50),
    task_data json NOT NULL,
    task_metadata json,
    status character varying(20) NOT NULL,
    priority integer NOT NULL,
    scheduled_at timestamp with time zone NOT NULL,
    assigned_at timestamp with time zone,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    celery_task_id character varying(255),
    retry_count integer NOT NULL,
    max_retries integer NOT NULL,
    last_error text,
    error_history json,
    result_data json,
    result_metadata json,
    parent_task_id uuid,
    correlation_id character varying(255),
    estimated_duration_seconds integer,
    actual_duration_seconds integer,
    created_by_user_id uuid,
    source_channel character varying(50),
    source_reference character varying(255),
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT ck_agent_task_priority CHECK (((priority >= 1) AND (priority <= 10))),
    CONSTRAINT ck_agent_task_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'assigned'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: TABLE agent_tasks; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.agent_tasks IS 'Agent task queue with autonomous processing and retry logic';


--
-- Name: COLUMN agent_tasks.agent_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.agent_id IS 'Agent assigned to process this task';


--
-- Name: COLUMN agent_tasks.task_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.task_type IS 'Type of task (slack_message, email, api_request, health_check, etc.)';


--
-- Name: COLUMN agent_tasks.task_subtype; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.task_subtype IS 'Subtype for more granular task categorization';


--
-- Name: COLUMN agent_tasks.task_data; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.task_data IS 'Task input data and parameters';


--
-- Name: COLUMN agent_tasks.task_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.task_metadata IS 'Additional metadata about the task source and context';


--
-- Name: COLUMN agent_tasks.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.status IS 'Task status (pending, assigned, processing, completed, failed, cancelled)';


--
-- Name: COLUMN agent_tasks.priority; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.priority IS 'Task priority (1=highest, 10=lowest)';


--
-- Name: COLUMN agent_tasks.scheduled_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.scheduled_at IS 'When the task should be processed';


--
-- Name: COLUMN agent_tasks.assigned_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.assigned_at IS 'When task was assigned to an agent';


--
-- Name: COLUMN agent_tasks.started_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.started_at IS 'When task processing started';


--
-- Name: COLUMN agent_tasks.completed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.completed_at IS 'When task was completed';


--
-- Name: COLUMN agent_tasks.celery_task_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.celery_task_id IS 'Celery task ID for tracking background processing';


--
-- Name: COLUMN agent_tasks.retry_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.retry_count IS 'Number of retry attempts made';


--
-- Name: COLUMN agent_tasks.max_retries; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.max_retries IS 'Maximum number of retry attempts allowed';


--
-- Name: COLUMN agent_tasks.last_error; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.last_error IS 'Last error message if task failed';


--
-- Name: COLUMN agent_tasks.error_history; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.error_history IS 'History of all error attempts';


--
-- Name: COLUMN agent_tasks.result_data; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.result_data IS 'Task processing results and output';


--
-- Name: COLUMN agent_tasks.result_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.result_metadata IS 'Metadata about task processing (duration, resources used, etc.)';


--
-- Name: COLUMN agent_tasks.parent_task_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.parent_task_id IS 'Parent task if this is a subtask';


--
-- Name: COLUMN agent_tasks.correlation_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.correlation_id IS 'Correlation ID for grouping related tasks';


--
-- Name: COLUMN agent_tasks.estimated_duration_seconds; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.estimated_duration_seconds IS 'Estimated processing duration in seconds';


--
-- Name: COLUMN agent_tasks.actual_duration_seconds; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.actual_duration_seconds IS 'Actual processing duration in seconds';


--
-- Name: COLUMN agent_tasks.created_by_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.created_by_user_id IS 'User who created the task (if applicable)';


--
-- Name: COLUMN agent_tasks.source_channel; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.source_channel IS 'Channel that generated the task (slack, email, api, etc.)';


--
-- Name: COLUMN agent_tasks.source_reference; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.source_reference IS 'External reference ID (slack message ID, email ID, etc.)';


--
-- Name: COLUMN agent_tasks.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.notes IS 'Internal notes';


--
-- Name: COLUMN agent_tasks.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_tasks.extra_metadata IS 'JSON metadata storage';


--
-- Name: agent_usage_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_usage_stats (
    agent_id uuid NOT NULL,
    total_messages integer NOT NULL,
    successful_responses integer NOT NULL,
    failed_responses integer NOT NULL,
    tools_called integer NOT NULL,
    avg_response_time_ms numeric(10,2),
    period_start timestamp with time zone NOT NULL,
    period_end timestamp with time zone NOT NULL,
    unique_users integer,
    confidence_scores json,
    tool_usage json,
    error_types json,
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: COLUMN agent_usage_stats.agent_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.agent_id IS 'Agent these stats belong to';


--
-- Name: COLUMN agent_usage_stats.total_messages; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.total_messages IS 'Total messages processed by agent';


--
-- Name: COLUMN agent_usage_stats.successful_responses; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.successful_responses IS 'Number of successful responses';


--
-- Name: COLUMN agent_usage_stats.failed_responses; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.failed_responses IS 'Number of failed responses';


--
-- Name: COLUMN agent_usage_stats.tools_called; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.tools_called IS 'Total number of MCP tool calls made';


--
-- Name: COLUMN agent_usage_stats.avg_response_time_ms; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.avg_response_time_ms IS 'Average response time in milliseconds';


--
-- Name: COLUMN agent_usage_stats.period_start; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.period_start IS 'Start of statistics period';


--
-- Name: COLUMN agent_usage_stats.period_end; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.period_end IS 'End of statistics period';


--
-- Name: COLUMN agent_usage_stats.unique_users; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.unique_users IS 'Number of unique users who interacted with agent';


--
-- Name: COLUMN agent_usage_stats.confidence_scores; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.confidence_scores IS 'Array of confidence scores for responses';


--
-- Name: COLUMN agent_usage_stats.tool_usage; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.tool_usage IS 'Breakdown of tool usage by tool name';


--
-- Name: COLUMN agent_usage_stats.error_types; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.error_types IS 'Breakdown of error types encountered';


--
-- Name: COLUMN agent_usage_stats.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.notes IS 'Internal notes';


--
-- Name: COLUMN agent_usage_stats.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_usage_stats.extra_metadata IS 'JSON metadata storage';


--
-- Name: agents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents (
    organization_id uuid,
    agent_type character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    avatar_url character varying(500),
    is_active boolean NOT NULL,
    status character varying(20) NOT NULL,
    role character varying(255),
    prompt text,
    initial_context text,
    initial_ai_msg text,
    tone character varying(100),
    communication_style character varying(100) NOT NULL,
    use_streaming boolean NOT NULL,
    response_length character varying(20) NOT NULL,
    memory_retention integer NOT NULL,
    show_suggestions_after_each_message boolean NOT NULL,
    suggestions_prompt text,
    max_context_size integer NOT NULL,
    use_memory_context boolean NOT NULL,
    max_iterations integer NOT NULL,
    timeout_seconds integer,
    tools json NOT NULL,
    last_used_at timestamp with time zone,
    extra_metadata json,
    id uuid NOT NULL,
    notes text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    has_custom_avatar boolean NOT NULL
);


--
-- Name: TABLE agents; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.agents IS 'Multi-agent system for organization-scoped automation and support';


--
-- Name: COLUMN agents.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.organization_id IS 'Organization this agent belongs to (NULL for system agents)';


--
-- Name: COLUMN agents.agent_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.agent_type IS 'Type of agent (customer_support, categorization, etc.)';


--
-- Name: COLUMN agents.name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.name IS 'Human-readable name for the agent';


--
-- Name: COLUMN agents.avatar_url; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.avatar_url IS 'URL for agent avatar image';


--
-- Name: COLUMN agents.is_active; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.is_active IS 'Whether agent is active and ready to handle requests';


--
-- Name: COLUMN agents.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.status IS 'Current agent status (active, inactive, error, maintenance)';


--
-- Name: COLUMN agents.role; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.role IS 'Agent role and responsibility description';


--
-- Name: COLUMN agents.prompt; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.prompt IS 'System prompt for Pydantic AI agent initialization';


--
-- Name: COLUMN agents.initial_context; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.initial_context IS 'Initial context provided to agent conversations';


--
-- Name: COLUMN agents.initial_ai_msg; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.initial_ai_msg IS 'Initial AI message for conversation start';


--
-- Name: COLUMN agents.tone; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.tone IS 'Communication tone (formal, casual, professional, etc.)';


--
-- Name: COLUMN agents.communication_style; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.communication_style IS 'Communication style preference';


--
-- Name: COLUMN agents.use_streaming; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.use_streaming IS 'Whether to use streaming responses';


--
-- Name: COLUMN agents.response_length; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.response_length IS 'Preferred response length (brief, moderate, detailed)';


--
-- Name: COLUMN agents.memory_retention; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.memory_retention IS 'Number of previous messages to retain in memory';


--
-- Name: COLUMN agents.show_suggestions_after_each_message; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.show_suggestions_after_each_message IS 'Whether to show suggested responses';


--
-- Name: COLUMN agents.suggestions_prompt; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.suggestions_prompt IS 'Custom prompt for generating suggestions';


--
-- Name: COLUMN agents.max_context_size; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.max_context_size IS 'Maximum context window size in tokens';


--
-- Name: COLUMN agents.use_memory_context; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.use_memory_context IS 'Whether to use conversation memory in context';


--
-- Name: COLUMN agents.max_iterations; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.max_iterations IS 'Maximum number of tool call iterations';


--
-- Name: COLUMN agents.timeout_seconds; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.timeout_seconds IS 'Timeout for agent responses in seconds';


--
-- Name: COLUMN agents.tools; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.tools IS 'List of enabled tool names';


--
-- Name: COLUMN agents.last_used_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.last_used_at IS 'When agent was last used to process a message';


--
-- Name: COLUMN agents.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.extra_metadata IS 'Additional metadata and custom fields';


--
-- Name: COLUMN agents.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.notes IS 'Internal notes';


--
-- Name: COLUMN agents.has_custom_avatar; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.has_custom_avatar IS 'Whether agent has a custom uploaded avatar';


--
-- Name: ai_agent_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_agent_configs (
    agent_type public.aiagenttype NOT NULL,
    name character varying(255) NOT NULL,
    version character varying(20) NOT NULL,
    description text,
    is_active boolean NOT NULL,
    is_default boolean NOT NULL,
    environment character varying(50) NOT NULL,
    model_provider character varying(50) NOT NULL,
    model_name character varying(100) NOT NULL,
    model_parameters json,
    system_prompt text,
    prompt_template text,
    prompt_variables json,
    few_shot_examples json,
    output_schema json,
    validation_rules json,
    post_processing_rules json,
    temperature character varying(10) NOT NULL,
    max_tokens integer,
    timeout_seconds integer NOT NULL,
    retry_attempts integer NOT NULL,
    confidence_threshold character varying(10) NOT NULL,
    content_filters json,
    safety_settings json,
    cost_per_request_usd character varying(20),
    daily_budget_usd character varying(20),
    monthly_budget_usd character varying(20),
    total_requests integer NOT NULL,
    successful_requests integer NOT NULL,
    failed_requests integer NOT NULL,
    average_response_time_ms integer,
    last_used_at timestamp with time zone,
    ab_test_group character varying(50),
    ab_test_percentage integer,
    ab_test_start_date timestamp with time zone,
    ab_test_end_date timestamp with time zone,
    parent_config_id uuid,
    inheritance_rules json,
    monitoring_enabled boolean NOT NULL,
    alert_thresholds json,
    performance_metrics json,
    created_by_id uuid,
    approved_by_id uuid,
    approved_at timestamp with time zone,
    deprecated_at timestamp with time zone,
    deprecation_reason text,
    change_log json,
    tags json,
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: COLUMN ai_agent_configs.agent_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.agent_type IS 'Type of AI agent this configuration applies to';


--
-- Name: COLUMN ai_agent_configs.name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.name IS 'Human-readable name for this configuration';


--
-- Name: COLUMN ai_agent_configs.version; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.version IS 'Configuration version (semantic versioning)';


--
-- Name: COLUMN ai_agent_configs.description; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.description IS 'Description of configuration purpose and changes';


--
-- Name: COLUMN ai_agent_configs.is_active; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.is_active IS 'Whether this configuration is currently active';


--
-- Name: COLUMN ai_agent_configs.is_default; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.is_default IS 'Whether this is the default configuration';


--
-- Name: COLUMN ai_agent_configs.environment; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.environment IS 'Environment this configuration applies to';


--
-- Name: COLUMN ai_agent_configs.model_provider; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.model_provider IS 'AI provider (openai, anthropic, google, azure)';


--
-- Name: COLUMN ai_agent_configs.model_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.model_name IS 'Specific model name/version';


--
-- Name: COLUMN ai_agent_configs.model_parameters; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.model_parameters IS 'Model-specific parameters (temperature, max_tokens, etc.)';


--
-- Name: COLUMN ai_agent_configs.system_prompt; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.system_prompt IS 'System prompt template for the agent';


--
-- Name: COLUMN ai_agent_configs.prompt_template; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.prompt_template IS 'User message prompt template';


--
-- Name: COLUMN ai_agent_configs.prompt_variables; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.prompt_variables IS 'Variables used in prompt templates';


--
-- Name: COLUMN ai_agent_configs.few_shot_examples; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.few_shot_examples IS 'Few-shot learning examples for the agent';


--
-- Name: COLUMN ai_agent_configs.output_schema; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.output_schema IS 'Expected output schema/format';


--
-- Name: COLUMN ai_agent_configs.validation_rules; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.validation_rules IS 'Rules for validating agent output';


--
-- Name: COLUMN ai_agent_configs.post_processing_rules; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.post_processing_rules IS 'Rules for post-processing agent responses';


--
-- Name: COLUMN ai_agent_configs.temperature; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.temperature IS 'Model temperature for response variability';


--
-- Name: COLUMN ai_agent_configs.max_tokens; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.max_tokens IS 'Maximum tokens in response';


--
-- Name: COLUMN ai_agent_configs.timeout_seconds; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.timeout_seconds IS 'Request timeout in seconds';


--
-- Name: COLUMN ai_agent_configs.retry_attempts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.retry_attempts IS 'Number of retry attempts on failure';


--
-- Name: COLUMN ai_agent_configs.confidence_threshold; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.confidence_threshold IS 'Minimum confidence threshold for responses';


--
-- Name: COLUMN ai_agent_configs.content_filters; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.content_filters IS 'Content filtering rules and thresholds';


--
-- Name: COLUMN ai_agent_configs.safety_settings; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.safety_settings IS 'Safety configuration for the agent';


--
-- Name: COLUMN ai_agent_configs.cost_per_request_usd; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.cost_per_request_usd IS 'Estimated cost per request in USD';


--
-- Name: COLUMN ai_agent_configs.daily_budget_usd; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.daily_budget_usd IS 'Daily budget limit in USD';


--
-- Name: COLUMN ai_agent_configs.monthly_budget_usd; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.monthly_budget_usd IS 'Monthly budget limit in USD';


--
-- Name: COLUMN ai_agent_configs.total_requests; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.total_requests IS 'Total requests made with this configuration';


--
-- Name: COLUMN ai_agent_configs.successful_requests; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.successful_requests IS 'Number of successful requests';


--
-- Name: COLUMN ai_agent_configs.failed_requests; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.failed_requests IS 'Number of failed requests';


--
-- Name: COLUMN ai_agent_configs.average_response_time_ms; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.average_response_time_ms IS 'Average response time in milliseconds';


--
-- Name: COLUMN ai_agent_configs.last_used_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.last_used_at IS 'Last time this configuration was used';


--
-- Name: COLUMN ai_agent_configs.ab_test_group; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.ab_test_group IS 'A/B test group identifier';


--
-- Name: COLUMN ai_agent_configs.ab_test_percentage; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.ab_test_percentage IS 'Percentage of traffic for A/B testing';


--
-- Name: COLUMN ai_agent_configs.ab_test_start_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.ab_test_start_date IS 'A/B test start date';


--
-- Name: COLUMN ai_agent_configs.ab_test_end_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.ab_test_end_date IS 'A/B test end date';


--
-- Name: COLUMN ai_agent_configs.parent_config_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.parent_config_id IS 'Parent configuration for inheritance';


--
-- Name: COLUMN ai_agent_configs.inheritance_rules; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.inheritance_rules IS 'Rules for inheriting from parent configuration';


--
-- Name: COLUMN ai_agent_configs.monitoring_enabled; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.monitoring_enabled IS 'Whether to monitor this configuration';


--
-- Name: COLUMN ai_agent_configs.alert_thresholds; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.alert_thresholds IS 'Thresholds for triggering alerts';


--
-- Name: COLUMN ai_agent_configs.performance_metrics; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.performance_metrics IS 'Performance metrics and benchmarks';


--
-- Name: COLUMN ai_agent_configs.created_by_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.created_by_id IS 'User who created this configuration';


--
-- Name: COLUMN ai_agent_configs.approved_by_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.approved_by_id IS 'User who approved this configuration';


--
-- Name: COLUMN ai_agent_configs.approved_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.approved_at IS 'When configuration was approved';


--
-- Name: COLUMN ai_agent_configs.deprecated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.deprecated_at IS 'When configuration was deprecated';


--
-- Name: COLUMN ai_agent_configs.deprecation_reason; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.deprecation_reason IS 'Reason for deprecating this configuration';


--
-- Name: COLUMN ai_agent_configs.change_log; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.change_log IS 'Log of changes made to this configuration';


--
-- Name: COLUMN ai_agent_configs.tags; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.tags IS 'Tags for organizing and searching configurations';


--
-- Name: COLUMN ai_agent_configs.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.notes IS 'Internal notes';


--
-- Name: COLUMN ai_agent_configs.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_agent_configs.extra_metadata IS 'JSON metadata storage';


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: api_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_tokens (
    name character varying(255) NOT NULL,
    token_hash character varying(255) NOT NULL,
    user_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    permissions json,
    expires_at timestamp with time zone NOT NULL,
    last_used_at timestamp with time zone,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: COLUMN api_tokens.name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.api_tokens.name IS 'User-friendly name for the token';


--
-- Name: COLUMN api_tokens.token_hash; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.api_tokens.token_hash IS 'Hashed token value (raw token never stored)';


--
-- Name: COLUMN api_tokens.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.api_tokens.user_id IS 'User who owns this token';


--
-- Name: COLUMN api_tokens.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.api_tokens.organization_id IS 'Organization this token is scoped to';


--
-- Name: COLUMN api_tokens.permissions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.api_tokens.permissions IS 'JSON array of permissions for this token';


--
-- Name: COLUMN api_tokens.expires_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.api_tokens.expires_at IS 'Token expiration timestamp';


--
-- Name: COLUMN api_tokens.last_used_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.api_tokens.last_used_at IS 'Last time this token was used';


--
-- Name: COLUMN api_tokens.is_active; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.api_tokens.is_active IS 'Whether token is active and can be used';


--
-- Name: COLUMN api_tokens.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.api_tokens.notes IS 'Internal notes';


--
-- Name: COLUMN api_tokens.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.api_tokens.extra_metadata IS 'JSON metadata storage';


--
-- Name: avatar_variants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.avatar_variants (
    id uuid NOT NULL,
    base_file_id uuid NOT NULL,
    entity_type character varying(20) NOT NULL,
    entity_id uuid NOT NULL,
    size_variant character varying(20) NOT NULL,
    storage_key character varying(500) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    notes text,
    extra_metadata text
);


--
-- Name: TABLE avatar_variants; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.avatar_variants IS 'Avatar size variants for different entity types';


--
-- Name: COLUMN avatar_variants.base_file_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.avatar_variants.base_file_id IS 'References file_storage_metadata for the original file';


--
-- Name: COLUMN avatar_variants.entity_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.avatar_variants.entity_type IS 'Type of entity (user, agent)';


--
-- Name: COLUMN avatar_variants.entity_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.avatar_variants.entity_id IS 'ID of the entity (user_id or agent_id)';


--
-- Name: COLUMN avatar_variants.size_variant; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.avatar_variants.size_variant IS 'Size variant (original, small, medium, large)';


--
-- Name: COLUMN avatar_variants.storage_key; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.avatar_variants.storage_key IS 'Storage key for this specific size variant';


--
-- Name: COLUMN avatar_variants.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.avatar_variants.notes IS 'Internal notes';


--
-- Name: COLUMN avatar_variants.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.avatar_variants.extra_metadata IS 'JSON metadata storage';


--
-- Name: file_storage_metadata; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.file_storage_metadata (
    id uuid NOT NULL,
    storage_key character varying(500) NOT NULL,
    original_filename character varying(255) NOT NULL,
    content_type character varying(100) NOT NULL,
    storage_backend character varying(20) NOT NULL,
    file_size bigint NOT NULL,
    file_metadata jsonb,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    notes text,
    extra_metadata text
);


--
-- Name: TABLE file_storage_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.file_storage_metadata IS 'Generic file storage metadata for all file types across storage backends';


--
-- Name: COLUMN file_storage_metadata.storage_key; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.file_storage_metadata.storage_key IS 'Unique storage key/path for the file across all backends';


--
-- Name: COLUMN file_storage_metadata.original_filename; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.file_storage_metadata.original_filename IS 'Original filename when uploaded';


--
-- Name: COLUMN file_storage_metadata.content_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.file_storage_metadata.content_type IS 'MIME type of the file';


--
-- Name: COLUMN file_storage_metadata.storage_backend; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.file_storage_metadata.storage_backend IS 'Storage backend used (local, s3, etc.)';


--
-- Name: COLUMN file_storage_metadata.file_size; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.file_storage_metadata.file_size IS 'File size in bytes';


--
-- Name: COLUMN file_storage_metadata.file_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.file_storage_metadata.file_metadata IS 'Additional file metadata and custom fields';


--
-- Name: COLUMN file_storage_metadata.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.file_storage_metadata.notes IS 'Internal notes';


--
-- Name: COLUMN file_storage_metadata.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.file_storage_metadata.extra_metadata IS 'JSON metadata storage';


--
-- Name: files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.files (
    filename character varying(255) NOT NULL,
    file_path character varying(500) NOT NULL,
    mime_type character varying(100) NOT NULL,
    file_size bigint NOT NULL,
    file_hash character varying(64) NOT NULL,
    file_type public.filetype NOT NULL,
    status public.filestatus NOT NULL,
    uploaded_by_id uuid NOT NULL,
    processing_started_at timestamp with time zone,
    processing_completed_at timestamp with time zone,
    processing_error text,
    processing_attempts integer NOT NULL,
    ai_analysis_version character varying(20),
    ai_confidence_score character varying(10),
    content_summary text,
    key_topics json,
    sentiment_analysis json,
    language_detection character varying(10),
    virus_scan_result character varying(20),
    virus_scan_at timestamp with time zone,
    virus_details text,
    is_public boolean NOT NULL,
    access_permissions json,
    download_count integer NOT NULL,
    last_accessed_at timestamp with time zone,
    retention_policy character varying(50),
    expires_at timestamp with time zone,
    archived_at timestamp with time zone,
    external_references json,
    tags json,
    processing_time_seconds integer,
    file_quality_score character varying(10),
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    organization_id uuid NOT NULL,
    extracted_context json,
    extraction_method character varying(50)
);


--
-- Name: COLUMN files.filename; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.filename IS 'Original filename';


--
-- Name: COLUMN files.file_path; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.file_path IS 'Server file path';


--
-- Name: COLUMN files.mime_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.mime_type IS 'MIME type of the file';


--
-- Name: COLUMN files.file_size; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.file_size IS 'File size in bytes';


--
-- Name: COLUMN files.file_hash; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.file_hash IS 'SHA-256 hash of file content';


--
-- Name: COLUMN files.file_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.file_type IS 'Detected file type category';


--
-- Name: COLUMN files.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.status IS 'Current processing status';


--
-- Name: COLUMN files.uploaded_by_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.uploaded_by_id IS 'User who uploaded the file';


--
-- Name: COLUMN files.processing_started_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.processing_started_at IS 'When processing started';


--
-- Name: COLUMN files.processing_completed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.processing_completed_at IS 'When processing completed';


--
-- Name: COLUMN files.processing_error; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.processing_error IS 'Error message if processing failed';


--
-- Name: COLUMN files.processing_attempts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.processing_attempts IS 'Number of processing attempts';


--
-- Name: COLUMN files.ai_analysis_version; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.ai_analysis_version IS 'Version of AI analysis used';


--
-- Name: COLUMN files.ai_confidence_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.ai_confidence_score IS 'AI confidence in analysis (0-1)';


--
-- Name: COLUMN files.content_summary; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.content_summary IS 'AI-generated summary of file content';


--
-- Name: COLUMN files.key_topics; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.key_topics IS 'Key topics identified in content';


--
-- Name: COLUMN files.sentiment_analysis; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.sentiment_analysis IS 'Sentiment analysis results';


--
-- Name: COLUMN files.language_detection; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.language_detection IS 'Detected primary language';


--
-- Name: COLUMN files.virus_scan_result; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.virus_scan_result IS 'Virus scan result (clean, infected, unknown)';


--
-- Name: COLUMN files.virus_scan_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.virus_scan_at IS 'When virus scan was performed';


--
-- Name: COLUMN files.virus_details; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.virus_details IS 'Details if virus/malware detected';


--
-- Name: COLUMN files.is_public; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.is_public IS 'Whether file is publicly accessible';


--
-- Name: COLUMN files.access_permissions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.access_permissions IS 'Specific access permissions for users/roles';


--
-- Name: COLUMN files.download_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.download_count IS 'Number of times file has been downloaded';


--
-- Name: COLUMN files.last_accessed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.last_accessed_at IS 'Last access timestamp';


--
-- Name: COLUMN files.retention_policy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.retention_policy IS 'Retention policy name';


--
-- Name: COLUMN files.expires_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.expires_at IS 'When file should be automatically deleted';


--
-- Name: COLUMN files.archived_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.archived_at IS 'When file was archived';


--
-- Name: COLUMN files.external_references; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.external_references IS 'References to file in external systems';


--
-- Name: COLUMN files.tags; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.tags IS 'User and AI-generated tags';


--
-- Name: COLUMN files.processing_time_seconds; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.processing_time_seconds IS 'Total processing time in seconds';


--
-- Name: COLUMN files.file_quality_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.file_quality_score IS 'Quality assessment score (0-1)';


--
-- Name: COLUMN files.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.notes IS 'Internal notes';


--
-- Name: COLUMN files.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.extra_metadata IS 'JSON metadata storage';


--
-- Name: COLUMN files.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.organization_id IS 'Organization that owns this file';


--
-- Name: COLUMN files.extracted_context; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.extracted_context IS 'Unified JSON structure for all content types (document, image, audio)';


--
-- Name: COLUMN files.extraction_method; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.files.extraction_method IS 'Method used for extraction (document_parser, vision_ocr, speech_transcription)';


--
-- Name: integrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.integrations (
    name character varying(255) NOT NULL,
    integration_category public.integrationcategory NOT NULL,
    platform_name character varying(50) NOT NULL,
    status public.integrationstatus NOT NULL,
    enabled boolean NOT NULL,
    description text,
    base_url character varying(500),
    api_version character varying(20),
    auth_type character varying(50) NOT NULL,
    credentials_encrypted text,
    oauth_scopes json,
    last_health_check_at timestamp with time zone,
    health_check_status character varying(20),
    health_check_error text,
    connection_test_count integer NOT NULL,
    total_requests integer NOT NULL,
    successful_requests integer NOT NULL,
    failed_requests integer NOT NULL,
    last_request_at timestamp with time zone,
    last_success_at timestamp with time zone,
    last_error_at timestamp with time zone,
    last_error_message text,
    rate_limit_per_hour integer,
    current_hour_requests integer NOT NULL,
    rate_limit_reset_at timestamp with time zone,
    routing_rules json,
    default_priority integer NOT NULL,
    supports_categories json,
    supports_priorities json,
    department_mapping json,
    custom_fields_mapping json,
    webhook_url character varying(500),
    webhook_secret_encrypted text,
    sync_enabled boolean NOT NULL,
    sync_frequency_minutes integer NOT NULL,
    last_sync_at timestamp with time zone,
    notification_events json,
    notification_channels json,
    environment character varying(50) NOT NULL,
    region character varying(50),
    monitoring_enabled boolean NOT NULL,
    alert_on_failure boolean NOT NULL,
    failure_threshold integer NOT NULL,
    consecutive_failures integer NOT NULL,
    maintenance_window_start character varying(10),
    maintenance_window_end character varying(10),
    auto_disable_on_error boolean NOT NULL,
    expires_at timestamp with time zone,
    last_activation_at timestamp with time zone,
    activation_method character varying(20),
    organization_id uuid,
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: COLUMN integrations.name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.name IS 'Display name for the integration';


--
-- Name: COLUMN integrations.integration_category; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.integration_category IS 'Functional category of the integration';


--
-- Name: COLUMN integrations.platform_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.platform_name IS 'Name of the integration platform (jira, slack, etc.)';


--
-- Name: COLUMN integrations.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.status IS 'Current integration status';


--
-- Name: COLUMN integrations.enabled; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.enabled IS 'Whether the integration is enabled for use';


--
-- Name: COLUMN integrations.description; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.description IS 'Description of integration purpose';


--
-- Name: COLUMN integrations.base_url; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.base_url IS 'Base URL for API endpoints';


--
-- Name: COLUMN integrations.api_version; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.api_version IS 'API version being used';


--
-- Name: COLUMN integrations.auth_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.auth_type IS 'Authentication type (api_key, oauth2, basic, bearer)';


--
-- Name: COLUMN integrations.credentials_encrypted; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.credentials_encrypted IS 'Encrypted authentication credentials (base64 encoded)';


--
-- Name: COLUMN integrations.oauth_scopes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.oauth_scopes IS 'OAuth scopes if using OAuth authentication';


--
-- Name: COLUMN integrations.last_health_check_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.last_health_check_at IS 'Last health check timestamp';


--
-- Name: COLUMN integrations.health_check_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.health_check_status IS 'Last health check result (healthy, unhealthy, unknown)';


--
-- Name: COLUMN integrations.health_check_error; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.health_check_error IS 'Error message from last health check';


--
-- Name: COLUMN integrations.connection_test_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.connection_test_count IS 'Number of connection tests performed';


--
-- Name: COLUMN integrations.total_requests; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.total_requests IS 'Total API requests made';


--
-- Name: COLUMN integrations.successful_requests; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.successful_requests IS 'Number of successful requests';


--
-- Name: COLUMN integrations.failed_requests; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.failed_requests IS 'Number of failed requests';


--
-- Name: COLUMN integrations.last_request_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.last_request_at IS 'Timestamp of last API request';


--
-- Name: COLUMN integrations.last_success_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.last_success_at IS 'Timestamp of last successful request';


--
-- Name: COLUMN integrations.last_error_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.last_error_at IS 'Timestamp of last error';


--
-- Name: COLUMN integrations.last_error_message; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.last_error_message IS 'Last error message';


--
-- Name: COLUMN integrations.rate_limit_per_hour; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.rate_limit_per_hour IS 'Rate limit requests per hour';


--
-- Name: COLUMN integrations.current_hour_requests; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.current_hour_requests IS 'Requests made in current hour';


--
-- Name: COLUMN integrations.rate_limit_reset_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.rate_limit_reset_at IS 'When rate limit counter resets';


--
-- Name: COLUMN integrations.routing_rules; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.routing_rules IS 'Rules for when to use this integration';


--
-- Name: COLUMN integrations.default_priority; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.default_priority IS 'Priority for routing (lower = higher priority)';


--
-- Name: COLUMN integrations.supports_categories; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.supports_categories IS 'List of ticket categories this integration supports';


--
-- Name: COLUMN integrations.supports_priorities; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.supports_priorities IS 'List of ticket priorities this integration supports';


--
-- Name: COLUMN integrations.department_mapping; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.department_mapping IS 'Mapping of internal departments to integration teams/queues';


--
-- Name: COLUMN integrations.custom_fields_mapping; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.custom_fields_mapping IS 'Mapping of internal fields to integration fields';


--
-- Name: COLUMN integrations.webhook_url; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.webhook_url IS 'Webhook URL for receiving events';


--
-- Name: COLUMN integrations.webhook_secret_encrypted; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.webhook_secret_encrypted IS 'Encrypted webhook authentication secret';


--
-- Name: COLUMN integrations.sync_enabled; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.sync_enabled IS 'Whether to sync data bidirectionally';


--
-- Name: COLUMN integrations.sync_frequency_minutes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.sync_frequency_minutes IS 'Sync frequency in minutes';


--
-- Name: COLUMN integrations.last_sync_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.last_sync_at IS 'Last successful sync timestamp';


--
-- Name: COLUMN integrations.notification_events; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.notification_events IS 'Events that should trigger notifications';


--
-- Name: COLUMN integrations.notification_channels; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.notification_channels IS 'Channels for sending notifications';


--
-- Name: COLUMN integrations.environment; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.environment IS 'Environment (production, staging, development)';


--
-- Name: COLUMN integrations.region; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.region IS 'Service region if applicable';


--
-- Name: COLUMN integrations.monitoring_enabled; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.monitoring_enabled IS 'Whether to monitor this integration';


--
-- Name: COLUMN integrations.alert_on_failure; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.alert_on_failure IS 'Whether to send alerts on failures';


--
-- Name: COLUMN integrations.failure_threshold; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.failure_threshold IS 'Number of failures before alerting';


--
-- Name: COLUMN integrations.consecutive_failures; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.consecutive_failures IS 'Current consecutive failure count';


--
-- Name: COLUMN integrations.maintenance_window_start; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.maintenance_window_start IS 'Maintenance window start time (HH:MM UTC)';


--
-- Name: COLUMN integrations.maintenance_window_end; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.maintenance_window_end IS 'Maintenance window end time (HH:MM UTC)';


--
-- Name: COLUMN integrations.auto_disable_on_error; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.auto_disable_on_error IS 'Whether to auto-disable on repeated errors';


--
-- Name: COLUMN integrations.expires_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.expires_at IS 'When integration credentials expire';


--
-- Name: COLUMN integrations.last_activation_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.last_activation_at IS 'When integration was last activated';


--
-- Name: COLUMN integrations.activation_method; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.activation_method IS 'How integration was activated (manual, automatic)';


--
-- Name: COLUMN integrations.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.organization_id IS 'Organization/company this integration belongs to';


--
-- Name: COLUMN integrations.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.notes IS 'Internal notes';


--
-- Name: COLUMN integrations.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.integrations.extra_metadata IS 'JSON metadata storage';


--
-- Name: messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.messages (
    id uuid NOT NULL,
    thread_id uuid NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    content_html text,
    created_at timestamp with time zone,
    tool_calls json,
    message_metadata json,
    response_time_ms integer,
    confidence_score double precision,
    notes text,
    extra_metadata text,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    attachments json
);


--
-- Name: COLUMN messages.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.messages.notes IS 'Internal notes';


--
-- Name: COLUMN messages.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.messages.extra_metadata IS 'JSON metadata storage';


--
-- Name: COLUMN messages.attachments; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.messages.attachments IS 'Array of file references: [{''file_id'':''uuid''}]';


--
-- Name: organization_invitations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_invitations (
    organization_id uuid NOT NULL,
    email character varying(255) NOT NULL,
    role public.organizationrole NOT NULL,
    invited_by_id uuid NOT NULL,
    invitation_token character varying(255) NOT NULL,
    status public.invitationstatus NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    accepted_at timestamp with time zone,
    declined_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    message character varying(1000),
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: COLUMN organization_invitations.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.organization_id IS 'Organization extending the invitation';


--
-- Name: COLUMN organization_invitations.email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.email IS 'Email address of invited user';


--
-- Name: COLUMN organization_invitations.role; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.role IS 'Role to assign upon acceptance';


--
-- Name: COLUMN organization_invitations.invited_by_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.invited_by_id IS 'User who sent the invitation';


--
-- Name: COLUMN organization_invitations.invitation_token; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.invitation_token IS 'Secure token for invitation acceptance';


--
-- Name: COLUMN organization_invitations.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.status IS 'Current invitation status';


--
-- Name: COLUMN organization_invitations.expires_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.expires_at IS 'When invitation expires (default 7 days)';


--
-- Name: COLUMN organization_invitations.accepted_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.accepted_at IS 'When invitation was accepted';


--
-- Name: COLUMN organization_invitations.declined_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.declined_at IS 'When invitation was declined';


--
-- Name: COLUMN organization_invitations.cancelled_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.cancelled_at IS 'When invitation was cancelled';


--
-- Name: COLUMN organization_invitations.message; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.message IS 'Custom invitation message from inviter';


--
-- Name: COLUMN organization_invitations.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.notes IS 'Internal notes';


--
-- Name: COLUMN organization_invitations.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_invitations.extra_metadata IS 'JSON metadata storage';


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizations (
    name character varying(255) NOT NULL,
    domain character varying(255),
    display_name character varying(255),
    is_enabled boolean NOT NULL,
    settings json,
    contact_email character varying(255),
    contact_phone character varying(50),
    address text,
    city character varying(100),
    state_province character varying(100),
    postal_code character varying(20),
    country character varying(100),
    industry character varying(100),
    size character varying(50),
    timezone character varying(50) NOT NULL,
    plan character varying(50) NOT NULL,
    billing_email character varying(255),
    feature_flags json,
    limits json,
    logo_url character varying(500),
    brand_colors json,
    custom_domain character varying(255),
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    clerk_organization_id character varying(255),
    clerk_metadata json
);


--
-- Name: COLUMN organizations.name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.name IS 'Company/organization name';


--
-- Name: COLUMN organizations.domain; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.domain IS 'Primary domain for the organization (e.g., company.com) - multiple orgs can share domains';


--
-- Name: COLUMN organizations.display_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.display_name IS 'Display name for UI (defaults to name if not set)';


--
-- Name: COLUMN organizations.is_enabled; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.is_enabled IS 'Whether organization is enabled for use';


--
-- Name: COLUMN organizations.settings; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.settings IS 'Organization-specific settings and preferences';


--
-- Name: COLUMN organizations.contact_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.contact_email IS 'Primary contact email for the organization';


--
-- Name: COLUMN organizations.contact_phone; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.contact_phone IS 'Primary contact phone number';


--
-- Name: COLUMN organizations.address; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.address IS 'Organization address';


--
-- Name: COLUMN organizations.city; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.city IS 'City';


--
-- Name: COLUMN organizations.state_province; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.state_province IS 'State or province';


--
-- Name: COLUMN organizations.postal_code; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.postal_code IS 'Postal/ZIP code';


--
-- Name: COLUMN organizations.country; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.country IS 'Country';


--
-- Name: COLUMN organizations.industry; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.industry IS 'Industry or business sector';


--
-- Name: COLUMN organizations.size; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.size IS 'Organization size (small, medium, large, enterprise)';


--
-- Name: COLUMN organizations.timezone; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.timezone IS 'Default timezone for the organization';


--
-- Name: COLUMN organizations.plan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.plan IS 'Subscription plan (basic, professional, enterprise)';


--
-- Name: COLUMN organizations.billing_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.billing_email IS 'Billing contact email';


--
-- Name: COLUMN organizations.feature_flags; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.feature_flags IS 'Enabled features for this organization';


--
-- Name: COLUMN organizations.limits; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.limits IS 'Usage limits and quotas';


--
-- Name: COLUMN organizations.logo_url; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.logo_url IS 'Organization logo URL';


--
-- Name: COLUMN organizations.brand_colors; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.brand_colors IS 'Brand colors for UI customization';


--
-- Name: COLUMN organizations.custom_domain; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.custom_domain IS 'Custom domain for white-labeling';


--
-- Name: COLUMN organizations.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.notes IS 'Internal notes';


--
-- Name: COLUMN organizations.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.extra_metadata IS 'JSON metadata storage';


--
-- Name: COLUMN organizations.clerk_organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.clerk_organization_id IS 'Clerk organization ID for authentication service integration';


--
-- Name: COLUMN organizations.clerk_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.clerk_metadata IS 'Synced Clerk organization data and metadata';


--
-- Name: threads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.threads (
    id uuid NOT NULL,
    agent_id uuid NOT NULL,
    user_id character varying(255) NOT NULL,
    organization_id uuid NOT NULL,
    title character varying(500),
    total_messages integer NOT NULL,
    last_message_at timestamp with time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    archived boolean,
    notes text,
    extra_metadata text,
    deleted_at timestamp with time zone
);


--
-- Name: COLUMN threads.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.threads.notes IS 'Internal notes';


--
-- Name: COLUMN threads.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.threads.extra_metadata IS 'JSON metadata storage';


--
-- Name: ticket_comments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ticket_comments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    ticket_id uuid NOT NULL,
    external_comment_id text,
    integration_id uuid,
    author_email text NOT NULL,
    author_display_name text,
    body text NOT NULL,
    body_html text,
    external_format_data json,
    is_internal boolean DEFAULT false NOT NULL,
    notes text,
    extra_metadata text,
    deleted_at timestamp with time zone
);


--
-- Name: TABLE ticket_comments; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.ticket_comments IS 'Comments on support tickets with generic integration platform support';


--
-- Name: COLUMN ticket_comments.id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.id IS 'Primary key for comment';


--
-- Name: COLUMN ticket_comments.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.created_at IS 'Timestamp when comment was created';


--
-- Name: COLUMN ticket_comments.updated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.updated_at IS 'Timestamp when comment was last updated';


--
-- Name: COLUMN ticket_comments.ticket_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.ticket_id IS 'Reference to parent ticket';


--
-- Name: COLUMN ticket_comments.external_comment_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.external_comment_id IS 'External platform comment ID for synchronization (JIRA, ServiceNow, etc.)';


--
-- Name: COLUMN ticket_comments.integration_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.integration_id IS 'Integration platform this comment was synchronized with';


--
-- Name: COLUMN ticket_comments.author_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.author_email IS 'Email address of comment author';


--
-- Name: COLUMN ticket_comments.author_display_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.author_display_name IS 'Display name of comment author';


--
-- Name: COLUMN ticket_comments.body; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.body IS 'Comment content (supports text and markdown)';


--
-- Name: COLUMN ticket_comments.body_html; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.body_html IS 'Rendered HTML version of content';


--
-- Name: COLUMN ticket_comments.external_format_data; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.external_format_data IS 'Platform-specific formatted content (e.g., ADF for JIRA, rich text for ServiceNow)';


--
-- Name: COLUMN ticket_comments.is_internal; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.is_internal IS 'Whether comment is internal-only or visible to customers';


--
-- Name: COLUMN ticket_comments.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.notes IS 'Internal notes';


--
-- Name: COLUMN ticket_comments.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.extra_metadata IS 'JSON metadata storage';


--
-- Name: COLUMN ticket_comments.deleted_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ticket_comments.deleted_at IS 'Soft delete timestamp - NULL means not deleted';


--
-- Name: tickets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tickets (
    title character varying(500) NOT NULL,
    description text NOT NULL,
    status public.ticketstatus NOT NULL,
    priority public.ticketpriority NOT NULL,
    category public.ticketcategory NOT NULL,
    subcategory character varying(100),
    created_by_id uuid NOT NULL,
    assigned_to_id uuid,
    organization_id uuid NOT NULL,
    integration_id uuid,
    department character varying(100),
    external_ticket_id character varying(255),
    external_ticket_url character varying(500),
    ai_confidence_score character varying(10),
    ai_reasoning text,
    ai_tags json,
    ai_keywords json,
    ai_similar_patterns json,
    urgency public.ticketpriority NOT NULL,
    business_impact character varying(50) NOT NULL,
    customer_segment character varying(100),
    estimated_effort character varying(50),
    estimated_resolution_time character varying(100),
    resolution_summary text,
    resolution_time_minutes integer,
    first_response_at timestamp with time zone,
    resolved_at timestamp with time zone,
    closed_at timestamp with time zone,
    last_activity_at timestamp with time zone NOT NULL,
    communication_count integer NOT NULL,
    satisfaction_rating integer,
    satisfaction_feedback text,
    escalation_level integer NOT NULL,
    escalated_at timestamp with time zone,
    escalated_by_id uuid,
    escalation_reason text,
    source_channel character varying(50) NOT NULL,
    source_details json,
    custom_fields json,
    internal_notes text,
    sla_due_date timestamp with time zone,
    sla_breached boolean NOT NULL,
    related_kb_articles json,
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    attachments json,
    integration_result json,
    description_adf jsonb,
    description_html text
);


--
-- Name: COLUMN tickets.title; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.title IS 'Ticket title/subject';


--
-- Name: COLUMN tickets.description; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.description IS 'Detailed ticket description';


--
-- Name: COLUMN tickets.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.status IS 'Current ticket status';


--
-- Name: COLUMN tickets.priority; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.priority IS 'Ticket priority level';


--
-- Name: COLUMN tickets.category; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.category IS 'Issue category';


--
-- Name: COLUMN tickets.subcategory; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.subcategory IS 'Specific subcategory within main category';


--
-- Name: COLUMN tickets.created_by_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.created_by_id IS 'User who created the ticket';


--
-- Name: COLUMN tickets.assigned_to_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.assigned_to_id IS 'User assigned to handle the ticket';


--
-- Name: COLUMN tickets.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.organization_id IS 'Organization to which the ticket belongs';


--
-- Name: COLUMN tickets.integration_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.integration_id IS 'Integration platform for routing (jira, servicenow, etc.)';


--
-- Name: COLUMN tickets.department; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.department IS 'Department responsible for ticket';


--
-- Name: COLUMN tickets.external_ticket_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.external_ticket_id IS 'External ticket ID in integration system';


--
-- Name: COLUMN tickets.external_ticket_url; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.external_ticket_url IS 'URL to external ticket';


--
-- Name: COLUMN tickets.ai_confidence_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.ai_confidence_score IS 'AI confidence score for categorization (0-1)';


--
-- Name: COLUMN tickets.ai_reasoning; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.ai_reasoning IS 'AI explanation for categorization decisions';


--
-- Name: COLUMN tickets.ai_tags; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.ai_tags IS 'AI-generated tags for the ticket';


--
-- Name: COLUMN tickets.ai_keywords; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.ai_keywords IS 'Key terms detected by AI';


--
-- Name: COLUMN tickets.ai_similar_patterns; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.ai_similar_patterns IS 'Similar issue patterns identified by AI';


--
-- Name: COLUMN tickets.urgency; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.urgency IS 'Urgency level for resolution';


--
-- Name: COLUMN tickets.business_impact; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.business_impact IS 'Assessed business impact level';


--
-- Name: COLUMN tickets.customer_segment; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.customer_segment IS 'Affected customer segment';


--
-- Name: COLUMN tickets.estimated_effort; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.estimated_effort IS 'Estimated effort level (minimal, moderate, significant, major)';


--
-- Name: COLUMN tickets.estimated_resolution_time; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.estimated_resolution_time IS 'Estimated time to resolve';


--
-- Name: COLUMN tickets.resolution_summary; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.resolution_summary IS 'Summary of how the ticket was resolved';


--
-- Name: COLUMN tickets.resolution_time_minutes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.resolution_time_minutes IS 'Actual resolution time in minutes';


--
-- Name: COLUMN tickets.first_response_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.first_response_at IS 'Timestamp of first response';


--
-- Name: COLUMN tickets.resolved_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.resolved_at IS 'Timestamp when ticket was resolved';


--
-- Name: COLUMN tickets.closed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.closed_at IS 'Timestamp when ticket was closed';


--
-- Name: COLUMN tickets.last_activity_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.last_activity_at IS 'Last activity timestamp';


--
-- Name: COLUMN tickets.communication_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.communication_count IS 'Number of communications on this ticket';


--
-- Name: COLUMN tickets.satisfaction_rating; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.satisfaction_rating IS 'Customer satisfaction rating (1-5)';


--
-- Name: COLUMN tickets.satisfaction_feedback; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.satisfaction_feedback IS 'Customer feedback on resolution';


--
-- Name: COLUMN tickets.escalation_level; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.escalation_level IS 'Current escalation level';


--
-- Name: COLUMN tickets.escalated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.escalated_at IS 'Timestamp when ticket was escalated';


--
-- Name: COLUMN tickets.escalated_by_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.escalated_by_id IS 'User who escalated the ticket';


--
-- Name: COLUMN tickets.escalation_reason; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.escalation_reason IS 'Reason for escalation';


--
-- Name: COLUMN tickets.source_channel; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.source_channel IS 'Channel where ticket was created (web, email, phone, chat)';


--
-- Name: COLUMN tickets.source_details; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.source_details IS 'Additional source-specific details';


--
-- Name: COLUMN tickets.custom_fields; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.custom_fields IS 'Custom fields for organization-specific data';


--
-- Name: COLUMN tickets.internal_notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.internal_notes IS 'Internal notes not visible to customer';


--
-- Name: COLUMN tickets.sla_due_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.sla_due_date IS 'SLA due date for resolution';


--
-- Name: COLUMN tickets.sla_breached; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.sla_breached IS 'Whether SLA has been breached';


--
-- Name: COLUMN tickets.related_kb_articles; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.related_kb_articles IS 'Related knowledge base articles';


--
-- Name: COLUMN tickets.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.notes IS 'Internal notes';


--
-- Name: COLUMN tickets.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.extra_metadata IS 'JSON metadata storage';


--
-- Name: COLUMN tickets.attachments; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.attachments IS 'Array of file references: [{''file_id'':''uuid''}]';


--
-- Name: COLUMN tickets.integration_result; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.integration_result IS 'Complete integration creation result with status, IDs, and response details';


--
-- Name: COLUMN tickets.description_adf; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.description_adf IS 'Rich text description in ADF format';


--
-- Name: COLUMN tickets.description_html; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tickets.description_html IS 'Rendered HTML description for display';


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    email character varying(255) NOT NULL,
    full_name character varying(255),
    password_hash character varying(255),
    is_active boolean NOT NULL,
    is_verified boolean NOT NULL,
    is_admin boolean NOT NULL,
    role public.userrole NOT NULL,
    permissions json,
    last_login_at timestamp with time zone,
    login_count character varying(50) NOT NULL,
    failed_login_attempts character varying(50) NOT NULL,
    locked_until timestamp with time zone,
    external_auth_provider character varying(50),
    external_auth_id character varying(255),
    preferences json,
    timezone character varying(50) NOT NULL,
    language character varying(10) NOT NULL,
    api_key_hash character varying(255),
    api_key_created_at timestamp with time zone,
    api_key_last_used_at timestamp with time zone,
    rate_limit_override character varying(50),
    avatar_url character varying(500),
    department character varying(100),
    organization_id uuid,
    id uuid NOT NULL,
    notes text,
    extra_metadata text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    organization_role public.organizationrole,
    invited_by_id uuid,
    invited_at timestamp with time zone,
    joined_organization_at timestamp with time zone,
    clerk_id character varying(255)
);


--
-- Name: COLUMN users.email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.email IS 'User email address';


--
-- Name: COLUMN users.full_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.full_name IS 'User''s full name';


--
-- Name: COLUMN users.password_hash; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.password_hash IS 'Hashed password (null for external auth)';


--
-- Name: COLUMN users.is_active; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.is_active IS 'Whether user account is active';


--
-- Name: COLUMN users.is_verified; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.is_verified IS 'Whether email is verified';


--
-- Name: COLUMN users.is_admin; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.is_admin IS 'Admin privileges';


--
-- Name: COLUMN users.role; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.role IS 'User role';


--
-- Name: COLUMN users.permissions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.permissions IS 'JSON array of specific permissions';


--
-- Name: COLUMN users.last_login_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.last_login_at IS 'Last login timestamp';


--
-- Name: COLUMN users.login_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.login_count IS 'Total number of logins';


--
-- Name: COLUMN users.failed_login_attempts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.failed_login_attempts IS 'Failed login attempts counter';


--
-- Name: COLUMN users.locked_until; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.locked_until IS 'Account locked until timestamp';


--
-- Name: COLUMN users.external_auth_provider; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.external_auth_provider IS 'External auth provider (google, microsoft, etc.)';


--
-- Name: COLUMN users.external_auth_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.external_auth_id IS 'External authentication ID';


--
-- Name: COLUMN users.preferences; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.preferences IS 'User preferences as JSON';


--
-- Name: COLUMN users.timezone; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.timezone IS 'User''s timezone';


--
-- Name: COLUMN users.language; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.language IS 'Preferred language code';


--
-- Name: COLUMN users.api_key_hash; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.api_key_hash IS 'Hashed API key for programmatic access';


--
-- Name: COLUMN users.api_key_created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.api_key_created_at IS 'API key creation timestamp';


--
-- Name: COLUMN users.api_key_last_used_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.api_key_last_used_at IS 'API key last used timestamp';


--
-- Name: COLUMN users.rate_limit_override; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.rate_limit_override IS 'Custom rate limit for this user';


--
-- Name: COLUMN users.avatar_url; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.avatar_url IS 'Profile picture URL';


--
-- Name: COLUMN users.department; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.department IS 'User''s department or team';


--
-- Name: COLUMN users.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.organization_id IS 'Organization/company this user belongs to';


--
-- Name: COLUMN users.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.notes IS 'Internal notes';


--
-- Name: COLUMN users.extra_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.extra_metadata IS 'JSON metadata storage';


--
-- Name: COLUMN users.organization_role; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.organization_role IS 'Role within the user''s organization';


--
-- Name: COLUMN users.invited_by_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.invited_by_id IS 'User who invited this member';


--
-- Name: COLUMN users.invited_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.invited_at IS 'When user was invited to organization';


--
-- Name: COLUMN users.joined_organization_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.joined_organization_at IS 'When user joined the organization';


--
-- Name: COLUMN users.clerk_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.clerk_id IS 'Clerk user ID for authentication service integration';


--
-- Name: agent_actions agent_actions_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_actions
    ADD CONSTRAINT agent_actions_id_key UNIQUE (id);


--
-- Name: agent_actions agent_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_actions
    ADD CONSTRAINT agent_actions_pkey PRIMARY KEY (id);


--
-- Name: agent_files agent_files_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_files
    ADD CONSTRAINT agent_files_id_key UNIQUE (id);


--
-- Name: agent_files agent_files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_files
    ADD CONSTRAINT agent_files_pkey PRIMARY KEY (id);


--
-- Name: agent_history agent_history_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_history
    ADD CONSTRAINT agent_history_id_key UNIQUE (id);


--
-- Name: agent_history agent_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_history
    ADD CONSTRAINT agent_history_pkey PRIMARY KEY (id);


--
-- Name: agent_tasks agent_tasks_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tasks
    ADD CONSTRAINT agent_tasks_id_key UNIQUE (id);


--
-- Name: agent_tasks agent_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tasks
    ADD CONSTRAINT agent_tasks_pkey PRIMARY KEY (id);


--
-- Name: agent_usage_stats agent_usage_stats_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_usage_stats
    ADD CONSTRAINT agent_usage_stats_id_key UNIQUE (id);


--
-- Name: agent_usage_stats agent_usage_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_usage_stats
    ADD CONSTRAINT agent_usage_stats_pkey PRIMARY KEY (id);


--
-- Name: agents agents_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_id_key UNIQUE (id);


--
-- Name: agents agents_id_key1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_id_key1 UNIQUE (id);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: ai_agent_configs ai_agent_configs_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_agent_configs
    ADD CONSTRAINT ai_agent_configs_id_key UNIQUE (id);


--
-- Name: ai_agent_configs ai_agent_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_agent_configs
    ADD CONSTRAINT ai_agent_configs_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: api_tokens api_tokens_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_tokens
    ADD CONSTRAINT api_tokens_id_key UNIQUE (id);


--
-- Name: api_tokens api_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_tokens
    ADD CONSTRAINT api_tokens_pkey PRIMARY KEY (id);


--
-- Name: avatar_variants avatar_variants_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.avatar_variants
    ADD CONSTRAINT avatar_variants_id_key UNIQUE (id);


--
-- Name: avatar_variants avatar_variants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.avatar_variants
    ADD CONSTRAINT avatar_variants_pkey PRIMARY KEY (id);


--
-- Name: file_storage_metadata file_storage_metadata_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_storage_metadata
    ADD CONSTRAINT file_storage_metadata_id_key UNIQUE (id);


--
-- Name: file_storage_metadata file_storage_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_storage_metadata
    ADD CONSTRAINT file_storage_metadata_pkey PRIMARY KEY (id);


--
-- Name: files files_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_id_key UNIQUE (id);


--
-- Name: files files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_pkey PRIMARY KEY (id);


--
-- Name: integrations integrations_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_id_key UNIQUE (id);


--
-- Name: integrations integrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: organization_invitations organization_invitations_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_invitations
    ADD CONSTRAINT organization_invitations_id_key UNIQUE (id);


--
-- Name: organization_invitations organization_invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_invitations
    ADD CONSTRAINT organization_invitations_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_id_key UNIQUE (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: ticket_comments pk_ticket_comments; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_comments
    ADD CONSTRAINT pk_ticket_comments PRIMARY KEY (id);


--
-- Name: threads threads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.threads
    ADD CONSTRAINT threads_pkey PRIMARY KEY (id);


--
-- Name: tickets tickets_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_id_key UNIQUE (id);


--
-- Name: tickets tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_pkey PRIMARY KEY (id);


--
-- Name: api_tokens unique_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_tokens
    ADD CONSTRAINT unique_token_hash UNIQUE (token_hash);


--
-- Name: api_tokens unique_user_token_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_tokens
    ADD CONSTRAINT unique_user_token_name UNIQUE (user_id, name);


--
-- Name: users users_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_id_key UNIQUE (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_messages_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_created_at ON public.messages USING btree (created_at);


--
-- Name: idx_messages_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_role ON public.messages USING btree (role);


--
-- Name: idx_messages_thread_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_thread_id ON public.messages USING btree (thread_id);


--
-- Name: idx_threads_agent_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_threads_agent_org ON public.threads USING btree (agent_id, organization_id);


--
-- Name: idx_threads_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_threads_created_at ON public.threads USING btree (created_at);


--
-- Name: idx_threads_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_threads_updated_at ON public.threads USING btree (updated_at);


--
-- Name: idx_threads_user_archived; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_threads_user_archived ON public.threads USING btree (user_id, archived);


--
-- Name: idx_ticket_comments_author_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ticket_comments_author_email ON public.ticket_comments USING btree (author_email);


--
-- Name: idx_ticket_comments_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ticket_comments_created_at ON public.ticket_comments USING btree (created_at);


--
-- Name: idx_ticket_comments_external_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ticket_comments_external_id ON public.ticket_comments USING btree (external_comment_id);


--
-- Name: idx_ticket_comments_integration_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ticket_comments_integration_id ON public.ticket_comments USING btree (integration_id);


--
-- Name: idx_ticket_comments_ticket_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ticket_comments_ticket_id ON public.ticket_comments USING btree (ticket_id);


--
-- Name: ix_agent_actions_action_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_actions_action_type ON public.agent_actions USING btree (action_type);


--
-- Name: ix_agent_actions_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_actions_agent_id ON public.agent_actions USING btree (agent_id);


--
-- Name: ix_agent_actions_conversation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_actions_conversation_id ON public.agent_actions USING btree (conversation_id);


--
-- Name: ix_agent_actions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_actions_created_at ON public.agent_actions USING btree (created_at);


--
-- Name: ix_agent_actions_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_actions_deleted_at ON public.agent_actions USING btree (deleted_at);


--
-- Name: ix_agent_actions_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_actions_session_id ON public.agent_actions USING btree (session_id);


--
-- Name: ix_agent_actions_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_actions_started_at ON public.agent_actions USING btree (started_at);


--
-- Name: ix_agent_actions_success; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_actions_success ON public.agent_actions USING btree (success);


--
-- Name: ix_agent_actions_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_actions_updated_at ON public.agent_actions USING btree (updated_at);


--
-- Name: ix_agent_files_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_files_agent_id ON public.agent_files USING btree (agent_id);


--
-- Name: ix_agent_files_content_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_files_content_hash ON public.agent_files USING btree (content_hash);


--
-- Name: ix_agent_files_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_files_created_at ON public.agent_files USING btree (created_at);


--
-- Name: ix_agent_files_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_files_deleted_at ON public.agent_files USING btree (deleted_at);


--
-- Name: ix_agent_files_file_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_files_file_id ON public.agent_files USING btree (file_id);


--
-- Name: ix_agent_files_processing_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_files_processing_status ON public.agent_files USING btree (processing_status);


--
-- Name: ix_agent_files_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_files_updated_at ON public.agent_files USING btree (updated_at);


--
-- Name: ix_agent_history_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_history_agent_id ON public.agent_history USING btree (agent_id);


--
-- Name: ix_agent_history_change_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_history_change_timestamp ON public.agent_history USING btree (change_timestamp);


--
-- Name: ix_agent_history_change_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_history_change_type ON public.agent_history USING btree (change_type);


--
-- Name: ix_agent_history_changed_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_history_changed_by_user_id ON public.agent_history USING btree (changed_by_user_id);


--
-- Name: ix_agent_history_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_history_created_at ON public.agent_history USING btree (created_at);


--
-- Name: ix_agent_history_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_history_deleted_at ON public.agent_history USING btree (deleted_at);


--
-- Name: ix_agent_history_field_changed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_history_field_changed ON public.agent_history USING btree (field_changed);


--
-- Name: ix_agent_history_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_history_updated_at ON public.agent_history USING btree (updated_at);


--
-- Name: ix_agent_tasks_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tasks_agent_id ON public.agent_tasks USING btree (agent_id);


--
-- Name: ix_agent_tasks_celery_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tasks_celery_task_id ON public.agent_tasks USING btree (celery_task_id);


--
-- Name: ix_agent_tasks_correlation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tasks_correlation_id ON public.agent_tasks USING btree (correlation_id);


--
-- Name: ix_agent_tasks_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tasks_created_at ON public.agent_tasks USING btree (created_at);


--
-- Name: ix_agent_tasks_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tasks_deleted_at ON public.agent_tasks USING btree (deleted_at);


--
-- Name: ix_agent_tasks_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tasks_priority ON public.agent_tasks USING btree (priority);


--
-- Name: ix_agent_tasks_scheduled_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tasks_scheduled_at ON public.agent_tasks USING btree (scheduled_at);


--
-- Name: ix_agent_tasks_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tasks_status ON public.agent_tasks USING btree (status);


--
-- Name: ix_agent_tasks_task_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tasks_task_type ON public.agent_tasks USING btree (task_type);


--
-- Name: ix_agent_tasks_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tasks_updated_at ON public.agent_tasks USING btree (updated_at);


--
-- Name: ix_agent_usage_stats_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_usage_stats_agent_id ON public.agent_usage_stats USING btree (agent_id);


--
-- Name: ix_agent_usage_stats_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_usage_stats_created_at ON public.agent_usage_stats USING btree (created_at);


--
-- Name: ix_agent_usage_stats_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_usage_stats_deleted_at ON public.agent_usage_stats USING btree (deleted_at);


--
-- Name: ix_agent_usage_stats_period_end; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_usage_stats_period_end ON public.agent_usage_stats USING btree (period_end);


--
-- Name: ix_agent_usage_stats_period_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_usage_stats_period_start ON public.agent_usage_stats USING btree (period_start);


--
-- Name: ix_agent_usage_stats_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_usage_stats_updated_at ON public.agent_usage_stats USING btree (updated_at);


--
-- Name: ix_agents_agent_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_agent_type ON public.agents USING btree (agent_type);


--
-- Name: ix_agents_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_created_at ON public.agents USING btree (created_at);


--
-- Name: ix_agents_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_deleted_at ON public.agents USING btree (deleted_at);


--
-- Name: ix_agents_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_is_active ON public.agents USING btree (is_active);


--
-- Name: ix_agents_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_organization_id ON public.agents USING btree (organization_id);


--
-- Name: ix_agents_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_status ON public.agents USING btree (status);


--
-- Name: ix_agents_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_updated_at ON public.agents USING btree (updated_at);


--
-- Name: ix_ai_agent_configs_agent_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_agent_configs_agent_type ON public.ai_agent_configs USING btree (agent_type);


--
-- Name: ix_ai_agent_configs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_agent_configs_created_at ON public.ai_agent_configs USING btree (created_at);


--
-- Name: ix_ai_agent_configs_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_agent_configs_deleted_at ON public.ai_agent_configs USING btree (deleted_at);


--
-- Name: ix_ai_agent_configs_environment; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_agent_configs_environment ON public.ai_agent_configs USING btree (environment);


--
-- Name: ix_ai_agent_configs_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_agent_configs_is_active ON public.ai_agent_configs USING btree (is_active);


--
-- Name: ix_ai_agent_configs_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_agent_configs_updated_at ON public.ai_agent_configs USING btree (updated_at);


--
-- Name: ix_api_tokens_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_tokens_created_at ON public.api_tokens USING btree (created_at);


--
-- Name: ix_api_tokens_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_tokens_deleted_at ON public.api_tokens USING btree (deleted_at);


--
-- Name: ix_api_tokens_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_tokens_is_active ON public.api_tokens USING btree (is_active);


--
-- Name: ix_api_tokens_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_tokens_organization_id ON public.api_tokens USING btree (organization_id);


--
-- Name: ix_api_tokens_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_api_tokens_token_hash ON public.api_tokens USING btree (token_hash);


--
-- Name: ix_api_tokens_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_tokens_updated_at ON public.api_tokens USING btree (updated_at);


--
-- Name: ix_api_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_tokens_user_id ON public.api_tokens USING btree (user_id);


--
-- Name: ix_avatar_variants_base_file_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_avatar_variants_base_file_id ON public.avatar_variants USING btree (base_file_id);


--
-- Name: ix_avatar_variants_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_avatar_variants_created_at ON public.avatar_variants USING btree (created_at);


--
-- Name: ix_avatar_variants_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_avatar_variants_deleted_at ON public.avatar_variants USING btree (deleted_at);


--
-- Name: ix_avatar_variants_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_avatar_variants_entity ON public.avatar_variants USING btree (entity_type, entity_id);


--
-- Name: ix_avatar_variants_entity_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_avatar_variants_entity_id ON public.avatar_variants USING btree (entity_id);


--
-- Name: ix_avatar_variants_entity_size; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_avatar_variants_entity_size ON public.avatar_variants USING btree (entity_id, size_variant);


--
-- Name: ix_avatar_variants_entity_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_avatar_variants_entity_type ON public.avatar_variants USING btree (entity_type);


--
-- Name: ix_avatar_variants_storage_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_avatar_variants_storage_key ON public.avatar_variants USING btree (storage_key);


--
-- Name: ix_avatar_variants_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_avatar_variants_updated_at ON public.avatar_variants USING btree (updated_at);


--
-- Name: ix_file_storage_metadata_content_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_file_storage_metadata_content_type ON public.file_storage_metadata USING btree (content_type);


--
-- Name: ix_file_storage_metadata_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_file_storage_metadata_created_at ON public.file_storage_metadata USING btree (created_at);


--
-- Name: ix_file_storage_metadata_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_file_storage_metadata_deleted_at ON public.file_storage_metadata USING btree (deleted_at);


--
-- Name: ix_file_storage_metadata_storage_backend; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_file_storage_metadata_storage_backend ON public.file_storage_metadata USING btree (storage_backend);


--
-- Name: ix_file_storage_metadata_storage_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_file_storage_metadata_storage_key ON public.file_storage_metadata USING btree (storage_key);


--
-- Name: ix_file_storage_metadata_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_file_storage_metadata_updated_at ON public.file_storage_metadata USING btree (updated_at);


--
-- Name: ix_files_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_created_at ON public.files USING btree (created_at);


--
-- Name: ix_files_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_deleted_at ON public.files USING btree (deleted_at);


--
-- Name: ix_files_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_expires_at ON public.files USING btree (expires_at);


--
-- Name: ix_files_file_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_files_file_hash ON public.files USING btree (file_hash);


--
-- Name: ix_files_file_path; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_files_file_path ON public.files USING btree (file_path);


--
-- Name: ix_files_file_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_file_type ON public.files USING btree (file_type);


--
-- Name: ix_files_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_organization_id ON public.files USING btree (organization_id);


--
-- Name: ix_files_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_status ON public.files USING btree (status);


--
-- Name: ix_files_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_updated_at ON public.files USING btree (updated_at);


--
-- Name: ix_files_uploaded_by_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_uploaded_by_id ON public.files USING btree (uploaded_by_id);


--
-- Name: ix_integrations_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integrations_created_at ON public.integrations USING btree (created_at);


--
-- Name: ix_integrations_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integrations_deleted_at ON public.integrations USING btree (deleted_at);


--
-- Name: ix_integrations_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integrations_enabled ON public.integrations USING btree (enabled);


--
-- Name: ix_integrations_integration_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integrations_integration_category ON public.integrations USING btree (integration_category);


--
-- Name: ix_integrations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integrations_organization_id ON public.integrations USING btree (organization_id);


--
-- Name: ix_integrations_platform_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integrations_platform_name ON public.integrations USING btree (platform_name);


--
-- Name: ix_integrations_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integrations_status ON public.integrations USING btree (status);


--
-- Name: ix_integrations_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integrations_updated_at ON public.integrations USING btree (updated_at);


--
-- Name: ix_messages_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_messages_deleted_at ON public.messages USING btree (deleted_at);


--
-- Name: ix_messages_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_messages_updated_at ON public.messages USING btree (updated_at);


--
-- Name: ix_organization_invitations_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_invitations_created_at ON public.organization_invitations USING btree (created_at);


--
-- Name: ix_organization_invitations_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_invitations_deleted_at ON public.organization_invitations USING btree (deleted_at);


--
-- Name: ix_organization_invitations_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_invitations_email ON public.organization_invitations USING btree (email);


--
-- Name: ix_organization_invitations_invitation_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_organization_invitations_invitation_token ON public.organization_invitations USING btree (invitation_token);


--
-- Name: ix_organization_invitations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_invitations_organization_id ON public.organization_invitations USING btree (organization_id);


--
-- Name: ix_organization_invitations_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_invitations_status ON public.organization_invitations USING btree (status);


--
-- Name: ix_organization_invitations_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_invitations_updated_at ON public.organization_invitations USING btree (updated_at);


--
-- Name: ix_organizations_clerk_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_organizations_clerk_organization_id ON public.organizations USING btree (clerk_organization_id);


--
-- Name: ix_organizations_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organizations_created_at ON public.organizations USING btree (created_at);


--
-- Name: ix_organizations_custom_domain; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_organizations_custom_domain ON public.organizations USING btree (custom_domain);


--
-- Name: ix_organizations_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organizations_deleted_at ON public.organizations USING btree (deleted_at);


--
-- Name: ix_organizations_domain; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organizations_domain ON public.organizations USING btree (domain);


--
-- Name: ix_organizations_is_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organizations_is_enabled ON public.organizations USING btree (is_enabled);


--
-- Name: ix_organizations_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organizations_name ON public.organizations USING btree (name);


--
-- Name: ix_organizations_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organizations_updated_at ON public.organizations USING btree (updated_at);


--
-- Name: ix_threads_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_threads_deleted_at ON public.threads USING btree (deleted_at);


--
-- Name: ix_tickets_assigned_to_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_assigned_to_id ON public.tickets USING btree (assigned_to_id);


--
-- Name: ix_tickets_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_category ON public.tickets USING btree (category);


--
-- Name: ix_tickets_closed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_closed_at ON public.tickets USING btree (closed_at);


--
-- Name: ix_tickets_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_created_at ON public.tickets USING btree (created_at);


--
-- Name: ix_tickets_created_by_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_created_by_id ON public.tickets USING btree (created_by_id);


--
-- Name: ix_tickets_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_deleted_at ON public.tickets USING btree (deleted_at);


--
-- Name: ix_tickets_department; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_department ON public.tickets USING btree (department);


--
-- Name: ix_tickets_external_ticket_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_external_ticket_id ON public.tickets USING btree (external_ticket_id);


--
-- Name: ix_tickets_first_response_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_first_response_at ON public.tickets USING btree (first_response_at);


--
-- Name: ix_tickets_integration_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_integration_id ON public.tickets USING btree (integration_id);


--
-- Name: ix_tickets_last_activity_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_last_activity_at ON public.tickets USING btree (last_activity_at);


--
-- Name: ix_tickets_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_organization_id ON public.tickets USING btree (organization_id);


--
-- Name: ix_tickets_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_priority ON public.tickets USING btree (priority);


--
-- Name: ix_tickets_resolved_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_resolved_at ON public.tickets USING btree (resolved_at);


--
-- Name: ix_tickets_sla_due_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_sla_due_date ON public.tickets USING btree (sla_due_date);


--
-- Name: ix_tickets_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_status ON public.tickets USING btree (status);


--
-- Name: ix_tickets_title; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_title ON public.tickets USING btree (title);


--
-- Name: ix_tickets_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_updated_at ON public.tickets USING btree (updated_at);


--
-- Name: ix_users_api_key_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_api_key_hash ON public.users USING btree (api_key_hash);


--
-- Name: ix_users_clerk_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_clerk_id ON public.users USING btree (clerk_id);


--
-- Name: ix_users_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_created_at ON public.users USING btree (created_at);


--
-- Name: ix_users_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_deleted_at ON public.users USING btree (deleted_at);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_external_auth_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_external_auth_id ON public.users USING btree (external_auth_id);


--
-- Name: ix_users_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_is_active ON public.users USING btree (is_active);


--
-- Name: ix_users_is_admin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_is_admin ON public.users USING btree (is_admin);


--
-- Name: ix_users_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_organization_id ON public.users USING btree (organization_id);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: ix_users_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_updated_at ON public.users USING btree (updated_at);


--
-- Name: agent_actions agent_actions_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_actions
    ADD CONSTRAINT agent_actions_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_actions agent_actions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_actions
    ADD CONSTRAINT agent_actions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: agent_files agent_files_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_files
    ADD CONSTRAINT agent_files_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_files agent_files_attached_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_files
    ADD CONSTRAINT agent_files_attached_by_user_id_fkey FOREIGN KEY (attached_by_user_id) REFERENCES public.users(id);


--
-- Name: agent_files agent_files_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_files
    ADD CONSTRAINT agent_files_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.files(id) ON DELETE CASCADE;


--
-- Name: agent_history agent_history_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_history
    ADD CONSTRAINT agent_history_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_history agent_history_changed_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_history
    ADD CONSTRAINT agent_history_changed_by_user_id_fkey FOREIGN KEY (changed_by_user_id) REFERENCES public.users(id);


--
-- Name: agent_tasks agent_tasks_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tasks
    ADD CONSTRAINT agent_tasks_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_tasks agent_tasks_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tasks
    ADD CONSTRAINT agent_tasks_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: agent_tasks agent_tasks_parent_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tasks
    ADD CONSTRAINT agent_tasks_parent_task_id_fkey FOREIGN KEY (parent_task_id) REFERENCES public.agent_tasks(id);


--
-- Name: agent_usage_stats agent_usage_stats_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_usage_stats
    ADD CONSTRAINT agent_usage_stats_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agents agents_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: ai_agent_configs ai_agent_configs_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_agent_configs
    ADD CONSTRAINT ai_agent_configs_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: ai_agent_configs ai_agent_configs_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_agent_configs
    ADD CONSTRAINT ai_agent_configs_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: ai_agent_configs ai_agent_configs_parent_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_agent_configs
    ADD CONSTRAINT ai_agent_configs_parent_config_id_fkey FOREIGN KEY (parent_config_id) REFERENCES public.ai_agent_configs(id);


--
-- Name: api_tokens api_tokens_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_tokens
    ADD CONSTRAINT api_tokens_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: api_tokens api_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_tokens
    ADD CONSTRAINT api_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: avatar_variants avatar_variants_base_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.avatar_variants
    ADD CONSTRAINT avatar_variants_base_file_id_fkey FOREIGN KEY (base_file_id) REFERENCES public.file_storage_metadata(id) ON DELETE CASCADE;


--
-- Name: files files_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: files files_uploaded_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_uploaded_by_id_fkey FOREIGN KEY (uploaded_by_id) REFERENCES public.users(id);


--
-- Name: ticket_comments fk_ticket_comments_integration_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_comments
    ADD CONSTRAINT fk_ticket_comments_integration_id FOREIGN KEY (integration_id) REFERENCES public.integrations(id);


--
-- Name: ticket_comments fk_ticket_comments_ticket_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_comments
    ADD CONSTRAINT fk_ticket_comments_ticket_id FOREIGN KEY (ticket_id) REFERENCES public.tickets(id) ON DELETE CASCADE;


--
-- Name: integrations integrations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: messages messages_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.threads(id);


--
-- Name: organization_invitations organization_invitations_invited_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_invitations
    ADD CONSTRAINT organization_invitations_invited_by_id_fkey FOREIGN KEY (invited_by_id) REFERENCES public.users(id);


--
-- Name: organization_invitations organization_invitations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_invitations
    ADD CONSTRAINT organization_invitations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: threads threads_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.threads
    ADD CONSTRAINT threads_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: threads threads_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.threads
    ADD CONSTRAINT threads_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: tickets tickets_assigned_to_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_assigned_to_id_fkey FOREIGN KEY (assigned_to_id) REFERENCES public.users(id);


--
-- Name: tickets tickets_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: tickets tickets_escalated_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_escalated_by_id_fkey FOREIGN KEY (escalated_by_id) REFERENCES public.users(id);


--
-- Name: tickets tickets_integration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_integration_id_fkey FOREIGN KEY (integration_id) REFERENCES public.integrations(id);


--
-- Name: tickets tickets_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: users users_invited_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_invited_by_id_fkey FOREIGN KEY (invited_by_id) REFERENCES public.users(id);


--
-- Name: users users_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 4gMemcXX4vbG40HCGI2yygik3kbgnYbcJJiUK3L8gqeEYhompQ1h4kzvz2BPBbQ

