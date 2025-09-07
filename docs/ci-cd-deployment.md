# PRP: CI/CD Deployment Pipeline for AI Ticket Creator Backend

## Overview

This PRP outlines the comprehensive CI/CD deployment pipeline implementation for the AI Ticket Creator Backend API, establishing automated testing, building, and red/green deployment to AWS using modern DevOps practices.

## Current State Analysis

### Existing Infrastructure
- **Application**: FastAPI backend with Pydantic AI agents
- **Database**: PostgreSQL 15 with SQLAlchemy 2.0
- **Background Tasks**: Celery with Redis broker
- **Containerization**: Docker Compose with multi-service architecture
- **Testing**: Comprehensive pytest suite with coverage
- **Dependencies**: Poetry package management

### Current Services
- Main API (port 8000)
- MCP Server (port 8001)
- PostgreSQL database
- Redis cache/broker
- Celery worker
- Flower monitoring

## Implementation Roadmap

### Phase 1: Repository Setup and GitHub Actions Foundation

#### Step 1.1: GitHub Repository Configuration
```bash
# Required Actions
1. Push current codebase to GitHub repository
2. Set up branch protection rules for main branch
3. Configure repository secrets
4. Enable GitHub Actions
```

**Required GitHub Secrets:**
```yaml
OPENAI_API_KEY: <your-openai-key>
GEMINI_API_KEY: <your-gemini-key>
JWT_SECRET_KEY: <256-bit-secret-key>
AWS_ACCESS_KEY_ID: <aws-access-key>
AWS_SECRET_ACCESS_KEY: <aws-secret-key>
AWS_REGION: us-east-1
ECR_REPOSITORY: ai-ticket-creator
RDS_PASSWORD: <database-password>
REDIS_AUTH_TOKEN: <redis-auth-token>
```

#### Step 1.2: Basic GitHub Actions Workflow
**File**: `.github/workflows/ci.yml`
```yaml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: "3.12"
  POETRY_VERSION: "1.8.3"

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: ai_tickets_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: ${{ env.POETRY_VERSION }}
    
    - name: Install dependencies
      run: poetry install
    
    - name: Run linting
      run: |
        poetry run ruff check .
        poetry run black --check .
    
    - name: Run type checking
      run: poetry run mypy app/
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/ai_tickets_test
        REDIS_URL: redis://localhost:6379/1
        JWT_SECRET_KEY: test-jwt-secret-key-for-testing-only-256-bits-long
        ENVIRONMENT: testing
      run: poetry run pytest tests/ -v --cov=app --cov-report=xml
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

### Phase 2: Docker Image Build and Push

#### Step 2.1: Multi-stage Dockerfile Optimization
**File**: `Dockerfile.prod`
```dockerfile
# Multi-stage build for production
FROM python:3.12-slim as builder

ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VENV_IN_PROJECT=1
ENV POETRY_NO_INTERACTION=1
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --only=main --no-root

# Production stage
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser mcp_server/ ./mcp_server/
COPY --chown=appuser:appuser mcp_client/ ./mcp_client/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser openapi.yaml ./

RUN mkdir -p /app/uploads && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Step 2.2: Build and Push Workflow
**File**: `.github/workflows/build.yml`
```yaml
name: Build and Push

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: ai-ticket-creator

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v2
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}
    
    - name: Build and push
      id: build
      uses: docker/build-push-action@v5
      with:
        context: .
        file: Dockerfile.prod
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

### Phase 3: AWS Infrastructure with Terraform

#### Step 3.1: Terraform Configuration
**Directory Structure:**
```
infrastructure/
├── main.tf
├── variables.tf
├── outputs.tf
├── modules/
│   ├── vpc/
│   ├── rds/
│   ├── redis/
│   ├── ecs/
│   └── alb/
└── environments/
    ├── staging/
    └── production/
```

**File**: `infrastructure/main.tf`
```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "ai-ticket-creator-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"
  
  environment = var.environment
  cidr_block = var.vpc_cidr
}

# RDS Module
module "rds" {
  source = "./modules/rds"
  
  environment = var.environment
  vpc_id = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  db_password = var.db_password
}

# Redis Module
module "redis" {
  source = "./modules/redis"
  
  environment = var.environment
  vpc_id = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
}

# ECS Module
module "ecs" {
  source = "./modules/ecs"
  
  environment = var.environment
  vpc_id = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids = module.vpc.public_subnet_ids
  
  database_url = module.rds.connection_string
  redis_url = module.redis.connection_string
  
  openai_api_key = var.openai_api_key
  gemini_api_key = var.gemini_api_key
  jwt_secret_key = var.jwt_secret_key
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"
  
  environment = var.environment
  vpc_id = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  target_group_arn = module.ecs.target_group_arn
}
```

#### Step 3.2: ECS Service Module
**File**: `infrastructure/modules/ecs/main.tf`
```hcl
resource "aws_ecs_cluster" "main" {
  name = "${var.environment}-ai-ticket-creator"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.environment}-ai-ticket-creator"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn           = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([
    {
      name  = "app"
      image = "${var.ecr_repository}:latest"
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "DATABASE_URL"
          value = var.database_url
        },
        {
          name  = "REDIS_URL" 
          value = var.redis_url
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        }
      ]
      secrets = [
        {
          name      = "OPENAI_API_KEY"
          valueFrom = aws_ssm_parameter.openai_key.arn
        },
        {
          name      = "GEMINI_API_KEY"
          valueFrom = aws_ssm_parameter.gemini_key.arn
        },
        {
          name      = "JWT_SECRET_KEY"
          valueFrom = aws_ssm_parameter.jwt_key.arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "app" {
  name            = "${var.environment}-ai-ticket-creator"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.environment == "production" ? 3 : 1
  launch_type     = "FARGATE"
  
  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 50
    
    deployment_circuit_breaker {
      enable   = true
      rollback = true
    }
  }
  
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8000
  }
  
  depends_on = [aws_lb_listener.app]
  
  tags = {
    Environment = var.environment
  }
}
```

### Phase 4: Red/Green Deployment Strategy

#### Step 4.1: Deployment Workflow
**File**: `.github/workflows/deploy.yml`
```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]
  workflow_run:
    workflows: ["CI Pipeline"]
    types:
      - completed

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: ai-ticket-creator

jobs:
  deploy-staging:
    if: github.ref == 'refs/heads/main' && github.event.workflow_run.conclusion == 'success'
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v3
    
    - name: Deploy to staging
      working-directory: infrastructure/environments/staging
      run: |
        terraform init
        terraform plan -var-file="staging.tfvars"
        terraform apply -auto-approve -var-file="staging.tfvars"
    
    - name: Update ECS service
      run: |
        aws ecs update-service \
          --cluster staging-ai-ticket-creator \
          --service staging-ai-ticket-creator \
          --force-new-deployment
    
    - name: Wait for deployment
      run: |
        aws ecs wait services-stable \
          --cluster staging-ai-ticket-creator \
          --services staging-ai-ticket-creator

  health-check-staging:
    needs: deploy-staging
    runs-on: ubuntu-latest
    
    steps:
    - name: Health check staging
      run: |
        STAGING_URL=$(aws ssm get-parameter \
          --name "/ai-ticket-creator/staging/alb-url" \
          --query 'Parameter.Value' \
          --output text)
        
        # Wait for health check
        for i in {1..30}; do
          if curl -f "$STAGING_URL/health"; then
            echo "Health check passed"
            exit 0
          fi
          sleep 10
        done
        echo "Health check failed"
        exit 1

  deploy-production:
    needs: health-check-staging
    runs-on: ubuntu-latest
    environment: production
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v3
    
    - name: Red/Green Deployment
      working-directory: infrastructure/environments/production
      run: |
        # Create green environment
        terraform init
        terraform plan -var-file="production.tfvars" -var="deployment_color=green"
        terraform apply -auto-approve -var-file="production.tfvars" -var="deployment_color=green"
        
        # Health check green environment
        GREEN_URL=$(aws ssm get-parameter \
          --name "/ai-ticket-creator/production/green-alb-url" \
          --query 'Parameter.Value' \
          --output text)
        
        for i in {1..20}; do
          if curl -f "$GREEN_URL/health"; then
            echo "Green environment healthy"
            break
          fi
          sleep 15
        done
        
        # Switch traffic to green
        aws elbv2 modify-listener \
          --listener-arn $(aws ssm get-parameter \
            --name "/ai-ticket-creator/production/listener-arn" \
            --query 'Parameter.Value' \
            --output text) \
          --default-actions Type=forward,TargetGroupArn=$(aws ssm get-parameter \
            --name "/ai-ticket-creator/production/green-target-group" \
            --query 'Parameter.Value' \
            --output text)
        
        # Cleanup old blue environment after successful switch
        sleep 300  # Wait 5 minutes
        terraform destroy -auto-approve -var-file="production.tfvars" -var="deployment_color=blue" || true
```

### Phase 5: Monitoring and Alerting

#### Step 5.1: CloudWatch and Application Insights
**File**: `infrastructure/modules/monitoring/main.tf`
```hcl
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.environment}-ai-ticket-creator"
  retention_in_days = 30
  
  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.environment}-ai-ticket-creator-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ecs cpu utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    ServiceName = "${var.environment}-ai-ticket-creator"
    ClusterName = "${var.environment}-ai-ticket-creator"
  }
}

resource "aws_cloudwatch_metric_alarm" "high_memory" {
  alarm_name          = "${var.environment}-ai-ticket-creator-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ecs memory utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    ServiceName = "${var.environment}-ai-ticket-creator"
    ClusterName = "${var.environment}-ai-ticket-creator"
  }
}

resource "aws_sns_topic" "alerts" {
  name = "${var.environment}-ai-ticket-creator-alerts"
}
```

### Phase 6: Security and Compliance

#### Step 6.1: Security Scanning Workflow
**File**: `.github/workflows/security.yml`
```yaml
name: Security Scanning

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 1'  # Weekly

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: 'trivy-results.sarif'

  container-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Build image
      run: docker build -t ai-ticket-creator:latest -f Dockerfile.prod .
    
    - name: Run Trivy vulnerability scanner on image
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'ai-ticket-creator:latest'
        format: 'sarif'
        output: 'trivy-image-results.sarif'
    
    - name: Upload image scan results
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: 'trivy-image-results.sarif'

  secrets-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Run gitleaks
      uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Implementation Timeline

### Week 1-2: Foundation Setup
1. Set up GitHub repository with branch protection
2. Configure basic GitHub Actions CI pipeline
3. Create optimized production Dockerfile
4. Set up AWS account and initial IAM roles

### Week 3-4: Infrastructure as Code
1. Implement Terraform modules for VPC, RDS, Redis
2. Create ECS cluster and service definitions
3. Set up Application Load Balancer
4. Configure CloudWatch logging and monitoring

### Week 5-6: Deployment Pipeline
1. Implement ECR image building and pushing
2. Create staging environment deployment
3. Implement red/green production deployment
4. Add comprehensive health checks

### Week 7-8: Security and Optimization
1. Add security scanning workflows
2. Implement secrets management with AWS Systems Manager
3. Configure alerting and monitoring
4. Performance testing and optimization

### Week 9-10: Testing and Validation
1. End-to-end deployment testing
2. Disaster recovery testing
3. Documentation and team training
4. Production cutover

## Cost Estimation

### Monthly AWS Costs (Production)
- **ECS Fargate (3 tasks)**: ~$65/month
- **RDS PostgreSQL (db.t3.medium)**: ~$50/month
- **ElastiCache Redis (cache.t3.micro)**: ~$15/month
- **Application Load Balancer**: ~$20/month
- **Data Transfer**: ~$10/month
- **CloudWatch Logs/Metrics**: ~$5/month
- **ECR Storage**: ~$5/month

**Total Estimated Cost**: ~$170/month for production

### Additional Costs
- **Staging Environment**: ~$85/month (50% of production)
- **Development Environment**: ~$50/month (minimal resources)

## Risk Mitigation

### High-Risk Items
1. **Database Migration**: Use blue/green deployment with database compatibility
2. **Secret Management**: Implement AWS Systems Manager Parameter Store
3. **Zero-Downtime Deployment**: Use ECS rolling deployments with health checks
4. **Cost Management**: Implement budget alerts and resource tagging

### Contingency Plans
1. **Rollback Strategy**: Automated rollback on health check failures
2. **Disaster Recovery**: Multi-AZ deployment with automated backups
3. **Monitoring**: Comprehensive alerting for all critical components
4. **Documentation**: Step-by-step runbooks for common operations

## Success Metrics

1. **Deployment Speed**: < 10 minutes for full production deployment
2. **Reliability**: 99.9% uptime with automated failover
3. **Security**: Zero high/critical vulnerabilities in production
4. **Cost**: Stay within $300/month budget for all environments
5. **Recovery Time**: < 5 minutes RTO, < 1 hour RPO

## Next Steps

1. **Review and Approve**: Stakeholder review of this PRP
2. **AWS Account Setup**: Create AWS account and initial IAM configuration
3. **Repository Preparation**: Clean up codebase and prepare for GitHub
4. **Team Training**: Schedule sessions on new deployment processes
5. **Implementation Kickoff**: Begin Phase 1 implementation

This PRP provides a comprehensive roadmap for implementing a modern, secure, and scalable CI/CD pipeline for the AI Ticket Creator Backend, ensuring reliable deployments and operational excellence.