# AWS COST GUARDIAN v1

# AI-Powered AWS FinOps & Cost Optimization Advisor

You are a senior:

- AWS Solutions Architect
- FinOps engineer
- Cloud cost optimization specialist
- Python/FastAPI engineer
- React/TypeScript engineer
- AI agent engineer
- Security engineer

Build a production-quality internal application called:

AWS Cost Guardian

Tagline:

"Understand your AWS bill. Find the waste. Explain the trade-offs. Save with confidence."

============================================================

1. PRODUCT OBJECTIVE

============================================================

AWS Cost Guardian is an internal AI-powered AWS FinOps application.

The application connects to AWS using READ-ONLY access.

It analyzes:

- AWS costs
- AWS services
- resources
- CloudWatch utilization
- resource configuration
- AWS Compute Optimizer recommendations
- AWS Cost Optimization Hub recommendations
- cost trends
- architecture signals
- resource relationships
- tagging

The application then uses an AI FinOps Advisor to investigate the available evidence and generate prioritized cost optimization recommendations.

The core workflow is:

OBSERVE
   ↓
INVESTIGATE
   ↓
REASON
   ↓
SIMULATE
   ↓
RECOMMEND
   ↓
VALIDATE
   ↓
SAVE

IMPORTANT:

The application must NOT automatically modify AWS infrastructure in v1.

No automatic:

- EC2 termination
- EC2 stop/start
- EC2 resizing
- RDS modification
- EBS deletion
- snapshot deletion
- S3 lifecycle modification
- networking modification
- security group modification

v1 is:

READ → ANALYZE → RECOMMEND

Human approval is required for every infrastructure change.

============================================================
2. KEY DIFFERENTIATOR
============================================================

DO NOT build a generic AWS billing dashboard.

AWS already provides:

- Cost Explorer
- Cost Optimization Hub
- Compute Optimizer
- AWS Budgets
- CloudWatch

AWS Cost Guardian should provide an intelligence layer on top.

The application should answer:

1. Where is money being spent?
2. Why did cost change?
3. What appears wasteful?
4. What are the safest savings opportunities?
5. How much could potentially be saved?
6. What evidence supports the recommendation?
7. What could go wrong?
8. What should be validated before implementation?
9. Which recommendation should be implemented first?
10. What would happen under a proposed change?

============================================================
3. AI-FIRST DESIGN
============================================================

AI IS a core component.

However:

AI must NOT invent numerical AWS costs.

AI must NOT invent resource utilization.

AI must NOT invent savings.

AI must NOT claim guaranteed savings.

Numerical calculations must come from deterministic application services.

AI receives trusted structured evidence.

Architecture:

AWS APIs
   ↓
Data Collection Layer
   ↓
Normalization Layer
   ↓
Cost Engine
   ↓
Metrics Engine
   ↓
Rules Engine
   ↓
AWS Recommendation Engine
   ↓
Evidence Store
   ↓
AI FinOps Advisor
   ↓
Risk Engine
   ↓
Savings Engine
   ↓
Final Recommendations

AI can:

- investigate
- compare
- reason
- prioritize
- explain
- identify missing information
- propose alternatives
- perform what-if analysis
- generate reports

============================================================
4. TECHNOLOGY STACK
============================================================

Backend:

Python 3.12+
FastAPI
Pydantic v2
SQLAlchemy 2
Alembic
boto3
httpx
pytest

Frontend:

React
TypeScript
Vite
Material UI
TanStack Query
React Router
Recharts
Monaco Editor optional

Database:

Development:
SQLite

Production-ready:
PostgreSQL

AI:

Provider abstraction supporting:

1. Ollama
2. Groq
3. AWS Bedrock

Environment variables:

AI_PROVIDER=ollama

OLLAMA_BASE_URL=[http://localhost:11434](http://localhost:11434)
OLLAMA_MODEL=

GROQ_API_KEY=
GROQ_MODEL=

AWS_BEDROCK_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=

The application must function fully without AI.

============================================================
5. PROJECT STRUCTURE
============================================================

Create:

aws-cost-guardian/

backend/
    app/
        main.py

```
    api/
        routes/
            health.py
            aws.py
            costs.py
            resources.py
            recommendations.py
            savings.py
            reports.py
            ai.py
            simulation.py

    core/
        config.py
        logging.py
        exceptions.py

    db/
        database.py
        models.py
        repositories/

    aws/
        client.py
        credentials.py
        sts.py
        cost_explorer.py
        ec2.py
        ebs.py
        rds.py
        s3.py
        lambda_service.py
        cloudwatch.py
        elb.py
        nat_gateway.py
        compute_optimizer.py
        cost_optimization_hub.py

    services/
        scan_service.py
        cost_service.py
        resource_service.py
        metric_service.py
        recommendation_service.py
        savings_service.py
        risk_service.py
        simulation_service.py
        report_service.py
        tagging_service.py

    rules/
        base.py
        registry.py
        ec2_rules.py
        ebs_rules.py
        rds_rules.py
        s3_rules.py
        lambda_rules.py
        nat_rules.py
        elastic_ip_rules.py
        tagging_rules.py

    ai/
        agent.py
        prompts.py
        tools.py
        provider.py
        ollama_provider.py
        groq_provider.py
        bedrock_provider.py
        context_builder.py
        guardrails.py

    schemas/
        account.py
        cost.py
        resource.py
        metric.py
        recommendation.py
        savings.py
        report.py
        ai.py
        simulation.py

tests/
    unit/
    integration/
```

frontend/
    src/
        app/
        components/
        pages/
        layouts/
        hooks/
        services/
        types/
        utils/
        charts/

infra/
    iam/
        aws-cost-guardian-readonly-policy.json
        trust-policy-example.json

docs/
    architecture.md
    security.md
    ai-agent.md
    optimization-rules.md
    aws-setup.md
    api.md

mock_data/
    costs/
    resources/
    metrics/
    recommendations/

.env.example
README.md
docker-compose.yml

============================================================
6. AWS SECURITY MODEL
============================================================

NEVER request AWS root credentials.

NEVER expose AWS credentials to the browser.

NEVER store AWS secret keys in the database.

Preferred production model:

Client AWS Account
       |
       |
       | AssumeRole
       |
       v
AWS Cost Guardian ReadOnly Role
       |
       v
AWS Cost Guardian Backend

Support two modes.

LOCAL DEVELOPMENT:

AWS_PROFILE
AWS_REGION

CLIENT MODE:

AWS_ROLE_ARN
AWS_EXTERNAL_ID
AWS_REGION

Use STS:

sts:GetCallerIdentity

to verify account identity.

Display:

AWS Account ID
Account Alias if available
Region
Authenticated role
Last scan time

============================================================
7. READ-ONLY IAM POLICY
============================================================

Create:

infra/iam/aws-cost-guardian-readonly-policy.json

Use least privilege.

Required permissions should include:

STS:

sts:GetCallerIdentity

Cost Explorer:

ce:GetCostAndUsage
ce:GetCostForecast
ce:GetDimensionValues
ce:GetTags

EC2:

ec2:DescribeInstances
ec2:DescribeVolumes
ec2:DescribeSnapshots
ec2:DescribeAddresses
ec2:DescribeImages
ec2:DescribeRegions
ec2:DescribeTags

RDS:

rds:DescribeDBInstances
rds:DescribeDBClusters
rds:DescribeDBSnapshots
rds:ListTagsForResource

S3:

s3:ListAllMyBuckets
s3:GetBucketLocation
s3:GetBucketTagging
s3:GetBucketLifecycleConfiguration
s3:GetBucketVersioning

Lambda:

lambda:ListFunctions
lambda:GetFunction
lambda:ListTags

CloudWatch:

cloudwatch:GetMetricData
cloudwatch:GetMetricStatistics
cloudwatch:ListMetrics

ELB:

elasticloadbalancing:DescribeLoadBalancers
elasticloadbalancing:DescribeTargetGroups
elasticloadbalancing:DescribeListeners

Compute Optimizer:

compute-optimizer:GetEnrollmentStatus
compute-optimizer:GetEC2InstanceRecommendations
compute-optimizer:GetEBSVolumeRecommendations
compute-optimizer:GetAutoScalingGroupRecommendations
compute-optimizer:GetLambdaFunctionRecommendations
compute-optimizer:GetRDSDatabaseRecommendations

Cost Optimization Hub:

cost-optimization-hub:ListRecommendations
cost-optimization-hub:GetRecommendation

VPC/NAT discovery:

ec2:DescribeNatGateways
ec2:DescribeRouteTables
ec2:DescribeVpcEndpoints
ec2:DescribeSubnets

IMPORTANT:

No destructive permissions.

DO NOT add:

ec2:TerminateInstances
ec2:StopInstances
ec2:ModifyInstanceAttribute
ec2:DeleteVolume
ec2:DeleteSnapshot
rds:DeleteDBInstance
rds:ModifyDBInstance
s3:DeleteBucket
s3:PutBucketLifecycleConfiguration
lambda:DeleteFunction
ec2:CreateVpcEndpoint
ec2:DeleteNatGateway
ec2:ModifyRouteTable

============================================================
8. DATABASE
============================================================

Use SQLAlchemy.

Account:

id
aws_account_id
account_alias
region
role_arn
last_scan_at
created_at
updated_at

CostRecord:

id
account_id
date
service
region
usage_type
amount
currency
source

Resource:

id
account_id
resource_id
resource_type
service
region
name
state
instance_type
environment
tags_json
metadata_json
created_at
updated_at

Metric:

id
resource_id
metric_name
timestamp
period
average
minimum
maximum
sample_count

Recommendation:

id
account_id
resource_id
rule_id
source
service
title
description
evidence_json
current_monthly_cost
estimated_monthly_savings
estimated_annual_savings
confidence
data_quality
risk_level
priority
action_type
status
created_at
updated_at

Recommendation sources:

INTERNAL_RULE
COMPUTE_OPTIMIZER
COST_OPTIMIZATION_HUB
AI_ANALYSIS

Recommendation status:

OPEN
REVIEWED
DISMISSED
IMPLEMENTED

Simulation:

id
account_id
name
scenario_type
input_json
current_cost
projected_cost
potential_savings
assumptions_json
risk_level
created_at

Report:

id
account_id
report_month
total_cost
previous_month_cost
potential_savings
realized_savings
report_json
created_at

============================================================
9. COST DATA
============================================================

Implement Cost Explorer integration.

Collect:

- current month
- previous month
- daily costs
- service costs
- regional costs
- usage type where useful

Do not hard-code AWS prices.

Create:

PricingService

where possible.

If a price cannot be confidently calculated:

return:

pricing_available=false

Do not fabricate pricing.

All savings must be labelled:

"Estimated potential savings"

Never:

"Guaranteed savings"

============================================================
10. RESOURCE INVENTORY
============================================================

Inventory:

EC2
EBS
Elastic IP
RDS
S3
Lambda
ALB
NAT Gateway
VPC endpoints
Snapshots

Resource inventory must be normalized into a common model.

Example:

{
    "resource_id": "i-123",
    "service": "EC2",
    "resource_type": "instance",
    "region": "us-east-1",
    "state": "running",
    "tags": {},
    "metadata": {}
}

============================================================
11. CLOUDWATCH METRICS
============================================================

Collect relevant metrics.

EC2:

CPUUtilization
NetworkIn
NetworkOut
DiskReadOps
DiskWriteOps
StatusCheckFailed

RDS:

CPUUtilization
DatabaseConnections
FreeStorageSpace
ReadIOPS
WriteIOPS
ReadLatency
WriteLatency

Lambda:

Invocations
Duration
Errors
Throttles

NAT Gateway:

BytesInFromSource
BytesOutToDestination
BytesInFromDestination
BytesOutToSource

Do not assume a metric exists.

If unavailable:

record missing evidence.

============================================================
12. INTERNAL RULE ENGINE
============================================================

Implement a pluggable rule engine.

Base:

class CostRule:

```
rule_id
name
service
description

def evaluate(context):
    ...
```

Create registry:

RuleRegistry

Each rule produces zero or more recommendations.

Rules must include:

- evidence
- confidence
- data quality
- risk
- estimated savings
- assumptions

============================================================
13. EC2 RULES
============================================================

EC2-001

UNDERUTILIZED_EC2

Example trigger:

Average CPU < 10%
over at least 14 days

But do NOT recommend resizing solely based on CPU.

If memory evidence is unavailable:

state:

"Additional validation required."

Evidence:

- CPU average
- CPU peak
- network
- running hours
- environment
- instance type

============================================================

EC2-002

DEV_INSTANCE_RUNNING_24X7

Detect:

Environment=dev
Environment=development

and continuous operation.

Recommend:

scheduling.

Estimate:

business-hours schedule.

Clearly display assumptions.

============================================================

EC2-003

OLD_INSTANCE_GENERATION

Detect old instance families.

Recommendation:

"Review migration to a current-generation equivalent."

Do not claim savings unless pricing data is available.

============================================================
14. EBS RULES
============================================================

EBS-001

UNATTACHED_VOLUME

Detect:

state=available

Potential saving:

current estimated storage cost.

Risk:

LOW

============================================================

EBS-002

GP2_REVIEW

Detect gp2 volumes.

Recommend:

review migration to gp3 where appropriate.

Do not claim guaranteed savings.

============================================================

EBS-003

OLD_SNAPSHOT

Identify old snapshots.

Do not automatically recommend deletion.

Show:

age
size if available
retention policy
dependency considerations

Risk:

MEDIUM

============================================================
15. RDS RULES
============================================================

Analyze:

- instance class
- CPU
- connections
- storage
- IOPS
- Multi-AZ
- environment
- uptime

Potential:

RDS underutilization

RDS dev environment scheduling

storage optimization

instance rightsizing review

IMPORTANT:

Do not recommend downsizing from CPU alone.

If memory data is unavailable:

confidence must be reduced.

============================================================
16. S3 RULES
============================================================

Analyze:

- bucket
- size where available
- versioning
- lifecycle
- object storage characteristics where available

Potential:

- missing lifecycle policy
- version accumulation
- storage class optimization opportunity
- incomplete multipart uploads if discoverable

Do not modify anything.

============================================================
17. NAT GATEWAY ANALYSIS
============================================================

Analyze:

- NAT gateways
- data processed
- VPC
- route tables
- endpoints
- region

Look for:

S3 traffic candidates
DynamoDB traffic candidates
cross-AZ architecture
low-utilization NAT gateways

Recommendation:

"Architecture review required."

Never guarantee savings.

============================================================
18. TAGGING ANALYSIS
============================================================

Recommended tags:

Environment
Application
Owner
Project
CostCenter
ManagedBy

Calculate coverage.

Example:

Environment:
94%

Owner:
72%

CostCenter:
61%

Generate:

TAGGING_GAP

This is not necessarily direct cost savings.

Classify as:

Governance improvement.

============================================================
19. AWS RECOMMENDATIONS
============================================================

Integrate:

AWS Cost Optimization Hub

and

AWS Compute Optimizer.

Normalize AWS recommendations.

Store source.

Deduplicate recommendations.

AI should be able to inspect these recommendations and challenge them when evidence is insufficient.

============================================================
20. AI FINOPS AGENT
============================================================

Create:

backend/app/ai/agent.py

The AI FinOps Agent should use tools.

The agent is NOT allowed to directly call arbitrary AWS APIs.

Instead it uses controlled read-only application tools.

Tools:

get_account_summary()

get_monthly_cost()

get_cost_trend()

get_service_cost()

get_resource_cost()

get_ec2_inventory()

get_ec2_utilization()

get_rds_inventory()

get_rds_utilization()

get_ebs_inventory()

get_s3_inventory()

get_lambda_inventory()

get_nat_gateway_usage()

get_aws_recommendations()

get_compute_optimizer_recommendations()

get_cost_optimization_hub_recommendations()

get_existing_recommendations()

calculate_savings()

get_resource_dependencies()

run_cost_simulation()

============================================================
21. AGENT BEHAVIOR
============================================================

The agent should reason in this sequence:

1. Understand user question.
2. Identify required evidence.
3. Call appropriate read-only tools.
4. Compare current state.
5. Identify opportunities.
6. Check AWS recommendations.
7. Check conflicting evidence.
8. Calculate or retrieve deterministic savings.
9. Assess risk.
10. Identify missing evidence.
11. Prioritize recommendations.
12. Respond with facts, assumptions, estimates, and risks.

The agent must NOT fabricate evidence.

============================================================
22. AI SYSTEM PROMPT
============================================================

Use this base system prompt:

"You are AWS Cost Guardian, an AI FinOps and cloud architecture advisor.

Your job is to help users understand AWS spending and identify responsible cost optimization opportunities.

You have access only to read-only AWS information supplied through approved tools.

Rules:

1. Never invent AWS resources.
2. Never invent AWS costs.
3. Never invent utilization metrics.
4. Never invent savings.
5. Never claim guaranteed savings.
6. Clearly distinguish facts from assumptions.
7. Use deterministic application calculations for financial numbers.
8. Prefer low-risk optimization opportunities.
9. Consider application architecture before recommending infrastructure changes.
10. Do not recommend production changes without appropriate validation.
11. If evidence is missing, say what evidence is required.
12. Challenge an AWS recommendation when available evidence does not support it.
13. Never execute infrastructure mutations.
14. Never request AWS credentials.
15. Explain technical trade-offs in CTO-friendly language.

Every recommendation should include:

Observation
Evidence
Recommendation
Estimated potential savings
Risk
Confidence
Assumptions
Validation steps

Your objective is not simply to reduce AWS spending.

Your objective is to reduce unnecessary AWS spending WITHOUT introducing unacceptable application, reliability, security, or operational risk."

============================================================
23. AI RECOMMENDATION EXAMPLE
============================================================

Given:

EC2:

t3.small
CPU average: 7%
CPU peak: 19%
Running 24x7
Environment: development
MySQL hosted on same instance

AI should NOT say:

"Downsize the instance."

Instead:

"EC2 appears underutilized based on CPU metrics. However, the instance also hosts MySQL. CPU alone is insufficient evidence for safe rightsizing. Before changing instance size, validate memory utilization, disk I/O, database connections and application latency.

A lower-risk opportunity is scheduling the development environment outside business hours."

============================================================
24. WHAT-IF SIMULATION
============================================================

Create:

POST /api/simulation

Example:

"What if development EC2 instances run only 12 hours/day on weekdays?"

Input:

resources
schedule
assumptions

Output:

current monthly cost
projected monthly cost
potential savings
annualized savings
assumptions
risk

Example:

Current:
₹4,200

Projected:
₹1,500

Potential:
₹2,700/month

Annualized:
₹32,400/year

Clearly mark:

ESTIMATE

============================================================
25. AI NAT ANALYSIS
============================================================

Example user question:

"Why is NAT Gateway expensive?"

Agent should:

1. retrieve NAT cost
2. retrieve traffic
3. inspect route/VPC information
4. inspect endpoints
5. identify potential S3/DynamoDB traffic
6. estimate potential savings if calculation is supported
7. explain architecture implications

Response structure:

Observation

Evidence

Possible cause

Potential solution

Estimated savings

Risk

Validation required

============================================================
26. AI COST INVESTIGATION
============================================================

User:

"Why did my AWS bill increase this month?"

Agent should:

1. compare current vs previous month
2. identify largest service changes
3. inspect resource changes where possible
4. inspect utilization
5. identify unusual increases
6. summarize probable causes

Do not state:

"Cause = X"

unless evidence supports it.

Use:

"Likely contributor"

when appropriate.

============================================================
27. AI SAVINGS REQUEST
============================================================

User:

"Find ways to save ₹5,000 per month."

Agent should:

1. calculate current spend
2. identify top services
3. investigate largest cost contributors
4. gather utilization
5. retrieve AWS recommendations
6. run internal rules
7. deduplicate
8. rank by savings/risk
9. select opportunities
10. calculate aggregate potential

Output:

Target savings:
₹5,000/month

Potential identified:
₹6,200/month

Recommended low-risk:
₹3,100/month

Requires architecture review:
₹3,100/month

============================================================
28. PRIORITIZATION MODEL
============================================================

Recommendation priority should consider:

Savings
Risk
Confidence
Data quality
Implementation complexity
Production impact

Example score:

## priority_score =
savings_score
+
confidence_score
+
safety_score

complexity_score

Keep formula deterministic.

AI can explain the ranking.

============================================================
29. OPTIMIZATION SCORE
============================================================

Create:

Cost Optimization Score

0-100

Factors:

- idle resources
- underutilization
- cost anomalies
- tagging
- dev scheduling
- optimization recommendations
- orphaned resources
- architecture opportunities

Example:

72/100

Show:

Strengths

Opportunities

Top three improvements

============================================================
30. DASHBOARD
============================================================

Create modern enterprise dashboard.

Top:

AWS COST GUARDIAN

Account:
123456789012

Region:
us-east-1

Last scan:
...

Cards:

Current Monthly Cost
Previous Monthly Cost
MoM Change
Potential Monthly Savings
Potential Annual Savings
Optimization Score

Charts:

Daily cost
Service cost
Regional cost

Recommendation sections:

SAFE SAVINGS

REVIEW REQUIRED

ARCHITECTURE OPPORTUNITIES

============================================================
31. RECOMMENDATIONS PAGE
============================================================

Filters:

Service
Risk
Confidence
Savings
Status
Source

Cards should show:

Title
Resource
Current cost
Potential savings
Evidence
Risk
Confidence
Source

Example:

---

DEV EC2 SCHEDULING

Resource:
i-123456

Current:
₹2,400/month

Potential:
₹1,200/month

Risk:
LOW

Confidence:
HIGH

Evidence:
Running 24x7
Environment=dev
Usage concentrated during business hours

Source:
AI + Internal Rule

[View Analysis]

---

============================================================
32. RECOMMENDATION DETAILS
============================================================

Show:

Observation

Evidence

Current architecture

Recommendation

Estimated savings

Risk

Confidence

Assumptions

Potential side effects

Validation checklist

AWS recommendation

AI reasoning

Related resources

============================================================
33. COST EXPLORER PAGE
============================================================

Filters:

Date range
Service
Region

Charts:

Daily cost
Monthly cost
Service distribution
Regional distribution

Table:

Service
Current
Previous
Change
Percentage

============================================================
34. RESOURCE PAGE
============================================================

Resource list.

Filters:

Service
Region
Environment
Tag
State

Resource detail:

configuration
cost
metrics
tags
dependencies
recommendations
historical trend

============================================================
35. AI ADVISOR PAGE
============================================================

Create chat UI.

Suggested questions:

Why did my AWS bill increase?

How can I save ₹5,000/month?

What should I optimize first?

Which recommendations are safest?

Explain this EC2 recommendation.

Should I resize this EC2 instance?

Why is NAT Gateway expensive?

What happens if I schedule development servers?

Generate an executive summary.

============================================================
36. AI RESPONSE UI
============================================================

AI response should render structured sections:

Summary

Evidence

Recommendations

Potential Savings

Risk

Assumptions

Validation

Use badges.

Example:

Potential Savings:
₹1,200/month

Risk:
LOW

Confidence:
HIGH

============================================================
37. REPORTING
============================================================

Create monthly report.

Report:

AWS COST OPTIMIZATION REPORT

Month

Current spend

Previous spend

MoM change

Potential savings

Realized savings

Top opportunities

Top risks

Architecture observations

AI executive summary

Generate HTML.

Design PDF generation as future enhancement.

============================================================
38. API
============================================================

Create:

GET /api/health

GET /api/aws/account

POST /api/aws/connect

POST /api/aws/scan

GET /api/costs/summary

GET /api/costs/daily

GET /api/costs/services

GET /api/costs/regions

GET /api/resources

GET /api/resources/{id}

GET /api/recommendations

GET /api/recommendations/{id}

PATCH /api/recommendations/{id}

GET /api/savings

GET /api/optimization-score

POST /api/simulation

GET /api/reports/monthly

POST /api/reports/monthly

POST /api/ai/chat

POST /api/ai/explain

POST /api/ai/executive-summary

============================================================
39. AWS SCAN PIPELINE
============================================================

POST /api/aws/scan

Process:

1. Validate credentials.
2. Get account identity.
3. Collect costs.
4. Collect resources.
5. Collect metrics.
6. Collect AWS recommendations.
7. Normalize data.
8. Persist evidence.
9. Run deterministic rules.
10. Calculate savings.
11. Calculate risk.
12. Calculate optimization score.
13. Make evidence available to AI agent.
14. Generate optional AI summary.

If one AWS service fails:

DO NOT fail entire scan.

Record:

service
error
timestamp

Continue scanning.

============================================================
40. MOCK MODE
============================================================

Critical for development.

.env:

MOCK_AWS=true

When true:

No AWS calls.

Use realistic mock data.

Create:

mock_data/

Include:

costs.json
ec2.json
ebs.json
rds.json
s3.json
lambda.json
nat.json
metrics.json
optimizer.json
cost_optimization_hub.json

Demo account:

Monthly cost:
₹18,420

Potential savings:
₹4,250

Optimization score:
68

Create realistic resources.

Display:

DEMO MODE

============================================================
41. AI MOCK MODE
============================================================

If AI provider is unavailable:

Application must continue working.

Display:

"AI Advisor unavailable. Core FinOps analysis is still available."

Do not crash.

============================================================
42. PROVIDER ABSTRACTION
============================================================

Create:

AIProvider

interface:

generate()
stream()
health_check()

Implement:

OllamaProvider
GroqProvider
BedrockProvider

Agent must not depend directly on one provider.

============================================================
43. AI GUARDRAILS
============================================================

Before sending tool results to AI:

- remove secrets
- remove credentials
- validate numerical fields
- validate account identifiers
- limit context size
- sanitize strings

AI output should be parsed into structured recommendation objects where appropriate.

Reject malformed AI responses gracefully.

============================================================
44. AI TOOL SECURITY
============================================================

AI tools must be:

READ ONLY.

Never expose:

boto3 client
AWS credentials
arbitrary Python execution
shell execution
database write tools

AI can only call explicit application functions.

============================================================
45. AUDIT LOG
============================================================

Create audit log for:

AWS scan
AI query
AI recommendation
report generation
recommendation status changes
simulation

Store:

timestamp
user/session
action
resource
result

Do not store secrets.

============================================================
46. TESTING
============================================================

Unit tests:

cost calculations
savings calculations
rules
risk
priority
optimization score
simulation
AI response validation

Integration tests:

FastAPI endpoints

AWS clients must be mocked.

No tests should call real AWS.

============================================================
47. FRONTEND ERROR HANDLING
============================================================

Friendly errors.

Examples:

AWS credentials unavailable.

AWS role assumption failed.

Missing IAM permission.

Cost Explorer unavailable.

CloudWatch metric unavailable.

AI provider unavailable.

Do not show stack traces.

============================================================
48. README
============================================================

Document:

What is AWS Cost Guardian?

Architecture

Features

Installation

Mock mode

AWS setup

IAM policy

Cross-account setup

AI providers

Running Ollama

Groq configuration

Bedrock configuration

Security

Testing

Troubleshooting

Roadmap

============================================================
49. ARCHITECTURE DOCUMENT
============================================================

Create docs/architecture.md.

Include diagrams using Mermaid.

Architecture:

Client AWS Account
        |
        v
ReadOnly IAM Role
        |
        v
AWS Collector
        |
        v
Normalization
        |
        +------ Cost Engine
        |
        +------ Metrics Engine
        |
        +------ Recommendation Engine
        |
        +------ Evidence Store
                    |
                    v
               AI Advisor
                    |
                    v
             Savings Analysis
                    |
                    v
               Dashboard

============================================================
50. AI AGENT DOCUMENT
============================================================

Create docs/ai-agent.md.

Document:

- agent architecture
- tools
- tool permissions
- reasoning workflow
- guardrails
- AI providers
- structured output
- hallucination prevention
- cost calculation separation
- human approval

============================================================
51. FUTURE ROADMAP
============================================================

Do NOT implement in v1.

V2:

- AWS Organizations
- multi-account dashboard
- scheduled scans
- email reports
- Slack notifications
- budgets
- cost anomaly detection

V3:

- approval workflow
- Jira integration
- Terraform recommendations
- CloudFormation recommendations
- infrastructure dependency graph

V4:

- automated remediation with explicit approval
- Savings Plans optimization
- Reserved Instance analysis
- forecasting
- FinOps maturity score
- organization-wide cost allocation

============================================================
52. IMPORTANT CLIENT USE CASE
============================================================

The application must support a scenario where:

Application
+
MySQL database

are hosted on the same EC2 instance.

The AI should understand that:

"Low EC2 CPU utilization does not automatically mean the instance should be downsized."

It should recommend gathering:

- memory utilization
- disk I/O
- DB connections
- application latency
- workload pattern

before rightsizing.

The AI should also be able to compare:

Option A:
Current architecture

Option B:
EC2 rightsizing

Option C:
Scheduled development environment

Option D:
EC2 + RDS

But must clearly distinguish:

COST OPTIMIZATION

from:

ARCHITECTURAL / OPERATIONAL IMPROVEMENT.

RDS should NOT automatically be recommended simply because it is more managed.

============================================================
53. CLIENT REPORT LANGUAGE
============================================================

Avoid overly technical language in executive reports.

Example:

BAD:

"CPUUtilization p95 indicates underprovisioned resource characteristics."

GOOD:

"The development server appears lightly utilized during most of the day. Scheduling it outside business hours could reduce its monthly running cost without changing the application architecture."

============================================================
54. NO OVERCLAIMING
============================================================

Never say:

"You will save ₹5,000."

Say:

"Estimated potential savings are ₹5,000/month, subject to validation."

Never say:

"This resource is definitely safe to delete."

Say:

"This resource appears unused based on the available evidence. Confirm ownership and dependencies before deletion."

============================================================
55. DEVELOPMENT APPROACH
============================================================

Build incrementally.

PHASE 1

Project skeleton
FastAPI
React
Database
Mock AWS
Health API
Basic dashboard

PHASE 2

Cost Explorer
Cost dashboard
Service breakdown
Cost trends

PHASE 3

Resource inventory
EC2
EBS
RDS
S3
Lambda
NAT

PHASE 4

Rules engine
Savings engine
Risk engine
Optimization score

PHASE 5

Compute Optimizer
Cost Optimization Hub

PHASE 6

AI FinOps Agent
AI tools
Ollama
Groq
Bedrock

PHASE 7

What-if simulation

PHASE 8

Reports

PHASE 9

Security hardening
IAM
Cross-account role

PHASE 10

Testing
Documentation
Production polish

============================================================
56. CURSOR EXECUTION RULE
============================================================

Do NOT generate the entire project blindly in one step.

First inspect the repository.

Then implement PHASE 1 only.

After PHASE 1:

- run tests
- start backend
- start frontend
- verify health endpoint
- verify mock AWS mode
- verify dashboard

Then report:

Files created
Files changed
Tests
Known issues
Next phase

Wait for instruction before implementing the next major phase.

Never silently skip tests.

============================================================
57. DEFINITION OF DONE
============================================================

AWS Cost Guardian v1 is complete when:

✓ Mock mode works
✓ Real AWS read-only mode works
✓ AWS account identity displayed
✓ Cost Explorer works
✓ Resource inventory works
✓ CloudWatch metrics work
✓ EC2 analysis works
✓ EBS analysis works
✓ RDS analysis works
✓ S3 analysis works
✓ Lambda analysis works
✓ NAT analysis works
✓ Internal rules work
✓ AWS recommendations integrated
✓ Savings engine works
✓ Risk engine works
✓ Optimization score works
✓ AI FinOps Agent works
✓ Ollama works
✓ Groq works
✓ Bedrock provider exists
✓ AI tools are read-only
✓ What-if simulation works
✓ Monthly report works
✓ IAM policy exists
✓ No destructive permissions
✓ Unit tests pass
✓ API tests pass
✓ Documentation exists

============================================================
58. FINAL PRODUCT PRINCIPLE
============================================================

AWS Cost Guardian should not behave like:

"Here is your AWS bill."

It should behave like:

"I analyzed your AWS environment.

Your current monthly spend is ₹18,420.

I found approximately ₹4,250/month of potential optimization opportunities.

₹1,780 appears low-risk.

₹1,470 requires technical validation.

₹1,000 requires architecture review.

Here is the evidence behind each recommendation.

Here are the assumptions.

Here is what I would implement first.

Here is what I would NOT change yet.

Here is what we should measure after implementation."

That is the intended product behavior.

START WITH PHASE 1 NOW.