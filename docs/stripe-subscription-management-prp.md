# Stripe Subscription Management Integration PRP

## Executive Summary

This PRP outlines the integration of Stripe subscription management and credit card processing into the AI Ticket Creator backend to support tiered subscription plans with usage-based billing. The implementation will enable flexible pricing models including fixed fees with overages and credit burndown options, providing customers choice in how they pay for AI-powered ticket creation services.

## Problem Statement

The current AI Ticket Creator system lacks monetization capabilities and usage controls. Users can create unlimited tickets without any billing or subscription management, making it impossible to:

- Generate revenue from the service
- Control resource usage and costs
- Provide different service tiers
- Scale the business sustainably

## Business Objectives

### Primary Goals
1. **Revenue Generation**: Implement subscription-based pricing to monetize the AI ticket creation service
2. **Usage Control**: Enforce usage limits based on subscription tiers to manage operational costs
3. **Scalable Billing**: Support both fixed fee and usage-based billing models for customer flexibility
4. **Customer Segmentation**: Provide clear upgrade paths from free to paid tiers

### Success Metrics
- Subscription conversion rate from free to paid plans
- Monthly recurring revenue (MRR) growth
- Customer lifetime value (CLV) improvement
- Reduced operational costs through usage controls

## Solution Overview

### Subscription Tiers

| Plan | Monthly Cost | Included Tickets | Overage Rate | Billing Model Options |
|------|--------------|------------------|--------------|---------------------|
| **Free** | $0 | 10 tickets | N/A (blocked) | N/A |
| **Premium** | $199 | 100 tickets | $1.99/ticket | Fixed fee + overage OR Credit burndown |
| **Enterprise** | $599 | 400 tickets | $1.25/ticket | Fixed fee + overage OR Credit burndown |

### Billing Models

#### Fixed Fee + Overage
- Monthly subscription fee includes base ticket allocation
- Additional tickets charged at per-ticket overage rate
- Usage resets on subscription anniversary date
- Immediate prorated billing for plan upgrades

#### Credit Burndown
- Customers prepay for ticket credits
- Credits deducted per ticket creation
- No monthly recurring charges
- Unused credits expire when switching billing models

## Technical Architecture

### Core Components

#### 1. Stripe Integration Layer
```
app/services/billing/
├── stripe_service.py          # Core Stripe API interactions
├── subscription_service.py    # Subscription lifecycle management
├── usage_service.py           # Usage tracking and billing
├── webhook_service.py         # Stripe webhook handlers
└── models/
    ├── subscription.py        # Subscription data model
    ├── usage_record.py       # Usage tracking model
    └── billing_plan.py       # Plan configuration model
```

#### 2. Usage Enforcement System
```
app/middleware/
├── subscription_middleware.py # Pre-request subscription checks
└── usage_limiter.py          # Usage validation and blocking

app/services/
├── entitlement_service.py    # Permission and access control
└── usage_tracker.py          # Real-time usage monitoring
```

#### 3. Data Storage Strategy
- **PostgreSQL**: Persistent subscription data, billing history, usage records
- **Redis**: Real-time usage counters, rate limiting, subscription cache
- **Stripe**: Authoritative billing and payment data

### API Endpoints

#### Subscription Management
```
POST   /api/v1/billing/subscriptions           # Create subscription
GET    /api/v1/billing/subscriptions           # Get current subscription
PATCH  /api/v1/billing/subscriptions           # Modify subscription
DELETE /api/v1/billing/subscriptions           # Cancel subscription

GET    /api/v1/billing/plans                   # List available plans
POST   /api/v1/billing/checkout                # Create Stripe checkout session
GET    /api/v1/billing/portal                  # Generate customer portal URL
```

#### Usage Tracking
```
GET    /api/v1/billing/usage                   # Get current usage stats
POST   /api/v1/billing/usage/record            # Record usage event
GET    /api/v1/billing/usage/history           # Usage history
```

#### Webhook Endpoints
```
POST   /api/v1/webhooks/stripe                 # Stripe webhook handler
```

### Database Schema

#### Subscriptions Table
```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(255) NOT NULL,
    plan_type VARCHAR(50) NOT NULL, -- 'free', 'premium', 'enterprise'
    billing_model VARCHAR(50) NOT NULL, -- 'fixed_fee', 'credit_burndown'
    status VARCHAR(50) NOT NULL, -- 'active', 'canceled', 'past_due', 'unpaid'
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Usage Records Table
```sql
CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    subscription_id UUID REFERENCES subscriptions(id),
    ticket_id UUID REFERENCES tickets(id),
    usage_type VARCHAR(50) NOT NULL, -- 'ticket_creation', 'agent_interaction'
    quantity INTEGER DEFAULT 1,
    billing_period_start TIMESTAMP WITH TIME ZONE,
    billing_period_end TIMESTAMP WITH TIME ZONE,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Billing Credits Table
```sql
CREATE TABLE billing_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    subscription_id UUID REFERENCES subscriptions(id),
    credit_amount DECIMAL(10,2) NOT NULL,
    used_amount DECIMAL(10,2) DEFAULT 0,
    remaining_amount DECIMAL(10,2) GENERATED ALWAYS AS (credit_amount - used_amount) STORED,
    stripe_invoice_id VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Implementation Plan

### Phase 1: Foundation (Week 1-2)
1. **Stripe Account Setup**
   - Configure Stripe products and pricing
   - Set up webhook endpoints
   - Configure test and production environments

2. **Database Schema Implementation**
   - Create subscription, usage, and billing tables
   - Set up Alembic migrations
   - Add foreign key relationships

3. **Core Services Development**
   - Implement `StripeService` for API interactions
   - Build `SubscriptionService` for lifecycle management
   - Create basic usage tracking functionality

### Phase 2: Subscription Management (Week 3-4)
1. **Checkout Integration**
   - Implement Stripe Checkout sessions
   - Add plan selection API endpoints
   - Build subscription creation workflow

2. **Webhook Processing**
   - Handle subscription lifecycle events
   - Process payment succeeded/failed events
   - Implement customer portal integration

3. **Usage Enforcement**
   - Add subscription middleware to API endpoints
   - Implement usage validation for ticket creation
   - Build usage counter management in Redis

### Phase 3: Billing Models (Week 5-6)
1. **Fixed Fee + Overage**
   - Implement monthly usage tracking
   - Add overage calculation and billing
   - Build usage reset on anniversary logic

2. **Credit Burndown System**
   - Implement credit purchase workflow
   - Add credit deduction on usage
   - Build credit balance management

3. **Plan Transitions**
   - Implement immediate plan upgrades with proration
   - Handle billing model switches
   - Manage credit expiration logic

### Phase 4: User Experience (Week 7-8)
1. **Frontend Integration**
   - Add subscription status display
   - Build usage tracking dashboard
   - Implement upgrade prompts and flows

2. **Customer Portal**
   - Integrate Stripe Customer Portal
   - Add billing management links
   - Implement cancel/reactivate flows

3. **Usage Alerts**
   - Build usage tracking display
   - Add approaching limit notifications
   - Implement usage history views

### Phase 5: Testing & Production (Week 9-10)
1. **Comprehensive Testing**
   - Unit tests for all billing services
   - Integration tests for Stripe workflows
   - E2E tests for subscription journeys

2. **Production Deployment**
   - Production Stripe configuration
   - Webhook endpoint security
   - Monitoring and alerting setup

## Technical Specifications

### Usage Tracking Implementation

#### Pre-Request Validation
```python
@subscription_required
async def create_ticket(request: TicketCreateRequest, user: User):
    # Check subscription status and usage limits
    usage_service = UsageService()
    
    if not await usage_service.can_create_ticket(user.id):
        raise HTTPException(
            status_code=403, 
            detail="Usage limit exceeded. Please upgrade your plan."
        )
    
    # Create ticket and record usage
    ticket = await ticket_service.create_ticket(request, user)
    await usage_service.record_usage(user.id, 'ticket_creation', 1)
    
    return ticket
```

#### Redis Usage Counters
```python
class UsageTracker:
    async def get_current_usage(self, user_id: str) -> int:
        key = f"usage:{user_id}:{self._get_billing_period()}"
        return await self.redis.get(key) or 0
    
    async def increment_usage(self, user_id: str, amount: int = 1):
        key = f"usage:{user_id}:{self._get_billing_period()}"
        pipeline = self.redis.pipeline()
        pipeline.incr(key, amount)
        pipeline.expire(key, self._get_period_expiry())
        await pipeline.execute()
```

### Stripe Webhook Handling

#### Subscription Events
```python
@router.post("/webhooks/stripe")
async def handle_stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
    
    if event['type'] == 'customer.subscription.updated':
        await subscription_service.handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        await subscription_service.handle_payment_failed(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        await subscription_service.handle_subscription_canceled(event['data']['object'])
    
    return {"status": "success"}
```

### Free Tier Usage Blocking

#### Chat Interface Disabling
```python
class TicketCreationService:
    async def validate_usage_limits(self, user_id: str) -> bool:
        subscription = await self.get_user_subscription(user_id)
        
        if subscription.plan_type == 'free':
            usage = await self.usage_tracker.get_current_usage(user_id)
            if usage >= 10:
                # Block ticket creation and disable chat
                await self.disable_chat_interface(user_id)
                return False
        
        return True
```

## Risk Assessment & Mitigation

### Technical Risks

#### Risk: Webhook Reliability
- **Impact**: Subscription status desync
- **Mitigation**: Implement webhook retry logic and reconciliation jobs

#### Risk: Usage Counter Accuracy
- **Impact**: Incorrect billing or access
- **Mitigation**: Dual storage (Redis + PostgreSQL) with reconciliation

#### Risk: Payment Failure Handling
- **Impact**: Service disruption
- **Mitigation**: Grace period implementation and dunning management

### Business Risks

#### Risk: Pricing Model Complexity
- **Impact**: Customer confusion
- **Mitigation**: Clear pricing documentation and upgrade flows

#### Risk: Free Tier Abuse
- **Impact**: Resource drain
- **Mitigation**: Strict usage enforcement and account verification

## Security Considerations

### Payment Data Security
- Use Stripe-hosted checkout pages to avoid PCI compliance
- Store only Stripe customer/subscription IDs, never payment methods
- Implement webhook signature verification

### API Security
- Rate limiting on billing endpoints
- Subscription status caching to reduce Stripe API calls
- Secure webhook endpoints with signature validation

### Data Privacy
- Encrypt sensitive billing data at rest
- Implement data retention policies
- Provide customer data export capabilities

## Monitoring & Analytics

### Key Metrics to Track
1. **Subscription Metrics**
   - Monthly Recurring Revenue (MRR)
   - Customer Acquisition Cost (CAC)
   - Churn rate by plan
   - Upgrade/downgrade rates

2. **Usage Metrics**
   - Average tickets per user by plan
   - Overage frequency and amounts
   - Free tier conversion rates

3. **Technical Metrics**
   - Webhook processing success rate
   - Payment processing latency
   - Usage counter accuracy

### Alerting Setup
- Failed payment notifications
- Webhook processing failures
- Usage limit violations
- Subscription cancellations

## Testing Strategy

### Unit Tests
- Subscription service methods
- Usage calculation logic
- Webhook event processing
- Billing model calculations

### Integration Tests
- Stripe API interactions
- Database operations
- Redis cache operations
- End-to-end billing flows

### Load Tests
- Concurrent usage tracking
- High-volume webhook processing
- Redis performance under load

## Deployment Checklist

### Pre-Production
- [ ] Stripe test environment configuration
- [ ] Database migrations tested
- [ ] Webhook endpoints secured
- [ ] Usage tracking validated
- [ ] Payment flow testing

### Production Launch
- [ ] Stripe production keys configured
- [ ] Webhook signatures verified
- [ ] Monitoring dashboards active
- [ ] Customer support documentation ready
- [ ] Rollback plan prepared

## Success Criteria

### Technical Success
- 99.9% webhook processing success rate
- < 100ms usage validation response time
- Zero payment data security incidents
- Accurate billing calculations

### Business Success
- 15% free-to-paid conversion rate within 6 months
- $50K MRR within first year
- < 5% monthly churn rate
- 90%+ customer satisfaction with billing experience

## Future Enhancements

### Phase 2 Features
1. **Advanced Usage Analytics**
   - Per-agent usage tracking
   - Custom usage alerts
   - Usage forecasting

2. **Billing Optimizations**
   - Annual plan discounts
   - Volume pricing tiers
   - Custom enterprise pricing

3. **Customer Experience**
   - In-app billing management
   - Usage recommendations
   - Cost optimization suggestions

---

**Document Version**: 1.0  
**Last Updated**: September 2025  
**Owner**: Product Team  
**Reviewers**: Engineering, Finance, Legal