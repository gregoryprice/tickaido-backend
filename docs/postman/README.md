# AI Ticket Creator API - Postman Collections

This directory contains Postman collections and environment files for testing the AI Ticket Creator Backend API.

## Files

1. **`AI-Ticket-Creator-API.postman_collection.json`** - Complete API collection with all endpoints
2. **`AI-Ticket-Creator-Environment.postman_environment.json`** - Environment variables for local development

## Quick Setup

### 1. Import Collections into Postman

1. Open Postman
2. Click **Import** button
3. Select **Upload Files** 
4. Import both files:
   - `AI-Ticket-Creator-API.postman_collection.json`
   - `AI-Ticket-Creator-Environment.postman_environment.json`

### 2. Configure Environment

1. In Postman, click the environment dropdown (top right)
2. Select **AI Ticket Creator - Local Development**
3. Update the following variables with your credentials:
   - `jira_api_token` - Your JIRA API token
   - `salesforce_password` - Your Salesforce password  
   - `salesforce_security_token` - Your Salesforce security token
   - `salesforce_client_id` - Your Salesforce Connected App client ID
   - `salesforce_client_secret` - Your Salesforce Connected App client secret

### 3. Test the API

1. **Start with Authentication:**
   - Run `Authentication > Register User` (if you need a new account)
   - Run `Authentication > Login` (this will automatically save your access token)

2. **Create AI-Powered Tickets:**
   - Run `Tickets > Create AI-Powered Ticket`
   - The default input is: "My password reset email is not arriving, I have been waiting for 30 minutes"

3. **Manage Integrations:**
   - Run `Integrations > Create JIRA Integration`
   - Run `Integrations > Test Integration Connection`

## Collection Features

### 🔐 **Automatic Authentication**
- Login request automatically saves access token to environment
- All authenticated requests use the saved token
- Token refresh functionality included

### 🎫 **Complete Ticket Management**
- AI-powered ticket creation with natural language processing
- Manual ticket creation and management
- Ticket status updates and assignment
- Comprehensive search and filtering

### 🔗 **Integration Management**
- JIRA integration setup with sample configurations
- Salesforce integration with field mapping
- Integration testing and health checks
- Manual synchronization triggers

### 📊 **System Monitoring**
- Health checks and status endpoints
- API documentation access
- OpenAPI specification retrieval

## Environment Variables

### Authentication
- `user_email` - Email for login (default: ai-test@acme.com)
- `user_password` - Password for login (default: testpass123)
- `access_token` - JWT token (auto-populated by login)
- `refresh_token` - Refresh token (auto-populated by login)

### JIRA Integration
- `jira_url` - Your JIRA instance URL
- `jira_email` - JIRA user email
- `jira_api_token` - JIRA API token (⚠️ **Required**)
- `jira_project_key` - JIRA project key (default: SUP)

### Salesforce Integration  
- `salesforce_instance_url` - Salesforce org URL
- `salesforce_username` - Salesforce username
- `salesforce_password` - Salesforce password (⚠️ **Required**)
- `salesforce_security_token` - Security token (⚠️ **Required**)
- `salesforce_client_id` - Connected App client ID (⚠️ **Required**)
- `salesforce_client_secret` - Connected App secret (⚠️ **Required**)

### Dynamic Variables
- `ticket_id` - Auto-populated when creating tickets
- `integration_id` - Auto-populated when creating integrations

## Example Workflows

### 1. Complete AI Ticket Creation Flow
```
1. Authentication > Login
2. Tickets > Create AI-Powered Ticket
3. Tickets > List Tickets (to see your created ticket)
4. Tickets > Get Ticket by ID (using the ticket_id from response)
```

### 2. JIRA Integration Setup Flow
```
1. Authentication > Login  
2. Integrations > Create JIRA Integration
3. Integrations > Test Integration Connection
4. Integrations > Get Integration Status
```

### 3. Complete Integration Testing Flow
```
1. Authentication > Login
2. Integrations > Create JIRA Integration
3. Integrations > Test Integration Connection
4. Tickets > Create AI-Powered Ticket
5. Integrations > Trigger Manual Sync
```

## Sample Requests

### AI Ticket Creation
The collection includes various sample inputs for AI ticket creation:
- Password reset issues
- Email server downtime
- Website performance problems
- Login difficulties

### Integration Testing
Pre-configured requests for:
- JIRA project management integration
- Salesforce case management integration
- Connection testing and validation
- Manual synchronization triggers

## Troubleshooting

### Authentication Issues
- Ensure the API server is running on `http://localhost:8000`
- Check that you've registered a user account first
- Verify login credentials in environment variables

### Integration Issues
- Ensure all required credentials are set in environment variables
- Test individual integration endpoints before full workflows
- Check integration setup guide at `/docs/integration-guide`

### API Server Issues
- Run `System > Health Check` to verify API status
- Check Docker containers are running: `docker ps`
- Verify database connectivity

## Getting Help

- 📖 **Integration Guide**: Run `System > Integration Setup Guide`
- 🔧 **API Documentation**: Visit `http://localhost:8000/docs`
- 📋 **OpenAPI Spec**: Run `System > OpenAPI Specification`
- 🏠 **API Home**: Run `System > API Home`

## Security Notes

⚠️ **Important Security Reminders:**
- Never commit API tokens or passwords to version control
- Use environment-specific credentials for different environments
- Regularly rotate API tokens and passwords
- Use HTTPS in production environments

The environment file includes placeholder values - replace them with your actual credentials before testing integrations.