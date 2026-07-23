# ECS Deployment Assets

Reference templates for Milestone 7 (ECS Deployment) of
[`docs/remote_mcp_deployment_prd.md`](../../docs/remote_mcp_deployment_prd.md).
These files are **examples to adapt**, not applied automatically — no
Terraform/CDK/CloudFormation stack is included, and no AWS account is
provisioned by this repository. Fill in every `<PLACEHOLDER>` before use.

---

## Files

| File | Purpose |
|---|---|
| `task-definition.json` | Fargate task definition: container image, port, environment, secrets, health check, logging. |
| `service-connect-example.json` | Example `aws ecs create-service` payload enabling ECS Service Connect so ResearchMind can resolve `research-intelligence-mcp` by name. |

---

## Prerequisites

- An ECR repository containing a pushed `research-intelligence-mcp` image (see the root [`Dockerfile`](../../Dockerfile)).
- Private subnets with NAT (or a NAT-equivalent egress path) for outbound HTTPS to Semantic Scholar and arXiv.
- An ECS cluster and Service Connect namespace.
- Two IAM roles:
  - **Execution role** — pull from ECR, write to CloudWatch Logs, read the secrets referenced in `task-definition.json`.
  - **Task role** — runtime AWS permissions for the container itself (none are required today; the provider clients only make outbound HTTPS calls).
- Secrets already created in AWS Secrets Manager:
  - `research-intelligence-mcp/semantic-scholar-api-key` (optional — Semantic Scholar works anonymously; omit the `secrets` entry if unused).
  - A JWKS-based issuer for `AUTH_JWKS_URL` if `AUTH_ENABLED=true` (no `AUTH_JWT_SECRET` is needed for RS256/ES256/PS256 — that setting is for local HS256 testing only; see `docs/research_intelligence_mcp_authentication.md`).

## Security groups

```text
ResearchMind service:  outbound TCP 8000 → MCP security group
MCP service:           inbound  TCP 8000  ← ResearchMind security group only
                       outbound TCP 443   → 0.0.0.0/0 (provider APIs)
```

Never open inbound `0.0.0.0/0` on port 8000.

## Deploying

1. Build and push the image:

   ```bash
   aws ecr get-login-password --region <REGION> \
     | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com

   docker build -t <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/research-intelligence-mcp:<IMAGE_TAG> .
   docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/research-intelligence-mcp:<IMAGE_TAG>
   ```

2. Fill in the placeholders in `task-definition.json`, then register it:

   ```bash
   aws ecs register-task-definition --cli-input-json file://task-definition.json
   ```

3. Fill in the placeholders in `service-connect-example.json`, then create (or update) the service:

   ```bash
   aws ecs create-service --cli-input-json file://service-connect-example.json
   # or, once the service already exists:
   aws ecs update-service --cli-input-json file://service-connect-example.json
   ```

4. Confirm the service reaches steady state and the task passes its container health check:

   ```bash
   aws ecs wait services-stable --cluster <CLUSTER_NAME> --services research-intelligence-mcp
   ```

5. From another task on the same Service Connect namespace (for example, the ResearchMind service), run the Level 2 smoke test:

   ```bash
   uv run python deployment/scripts/smoke_test.py \
     --base-url http://research-intelligence-mcp:8000 \
     --auth-token "$MCP_SERVICE_TOKEN"
   ```

## Rollback

- `deploymentCircuitBreaker.rollback` is enabled above: ECS automatically rolls back to the last healthy task definition revision if the new one fails to stabilize.
- Task definition revisions are immutable and retained by ECS; to roll back manually, `update-service` with the previous `taskDefinition` revision ARN.
- Keep the previous revision's tasks running until the new revision passes `services-stable` and the smoke test above.

## What is *not* included

- No live AWS deployment was performed as part of implementing this milestone — these are unapplied templates for the operator running this repository to fill in and deploy.
- No Terraform/CDK module; the `aws ecs` CLI commands above are the reference path.
