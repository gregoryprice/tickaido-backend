# AI Ticket Creator - Backend API

## Project Overview

Backend service for the AI Ticket Creator Chrome extension, providing API endpoints for ticket management, AI-powered automation, and third-party integrations.

## Core Features

### 🎫 Ticket Management
- REST API for normalized ticket CRUD operations
- AI-powered ticket categorization and priority assignment 
- screen recording for the browser
- video recording for the browswer
- transcription using AI
- Automated ticket routing and assignment
- Real-time status updates and notifications

### 🔗 Third-Party Integrations
- **Salesforce**: Case management and synchronization
- **Jira**: Issue tracking integration
- **Zendesk**: Customer support platform
- **Intercom**: Customer support platform
- **GitHub**: Issue creation and management
- **Slack**: Real-time notifications
- **Microsoft Teams**: Enterprise messaging
- **Chrome Extension**: Supports an in browser extention that will be published in the chrome store

### 🤖 AI & Automation
- Natural language processing for ticket descriptions
- Smart categorization and tagging
- Automated priority assignment
- Context-aware suggestions
- Allows capturing screengrabs, files, and transcripts to put in the tickets

### 📊 Analytics & Reporting
- Ticket metrics and trends
- Performance analytics
- Integration usage statistics
- Custom reporting endpoints

### 🔐 Authentication & Security
- JWT-based authentication
- Role-based access control
- API rate limiting
- Data encryption and privacy compliance

# Tech stack
You must use docker containers to manage project. You can use the examples in project: 
/Users/aristotle/projects/shipwell_trade_compliance

you must use poetry to manage packages
you must use pyenv to manage python version
Use python 3

You must use postgres
You must use test driven development and each endpoint and workflow has a test writen in pytest 
You must use celery for workers/jobs
You must use both openapi specification and redocly files in order to generation documentation
The documentation must get update when changes to api are made
You must use a configuration file for local development
You must use a configuration file for ai configuration (use the same structure as in /Users/aristotle/projects/shipwell_trade_compliance/backend/config/ai_config.yaml)