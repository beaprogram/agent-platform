# Agent Platform — Serverless Agentic AI Assistant on AWS

A production-style, cloud-native agentic AI assistant built for CSCI 5411
(Advanced Cloud Architecting). The assistant plans, calls tools, remembers the
conversation, and answers questions grounded in an ingested document corpus
(Retrieval-Augmented Generation). The entire stack is serverless and defined as
code with Terraform.

## What it does

- Reason -> Act -> Observe agent loop: the model decides when to call tools,
  reads the results, and iterates (bounded to a maximum number of steps).
- Tools: current time, a sandboxed arithmetic evaluator (AST-based, rejects code
  injection), and search_corpus for semantic retrieval.
- Session memory: prior turns are loaded from DynamoDB with a strongly
  consistent read, so follow-up questions retain context.
- RAG ingestion: documents dropped in S3 trigger a Lambda that chunks, embeds
  (Jina embeddings), and stores vectors in DynamoDB.
- Authentication: every request is authorized by Amazon Cognito.

## AWS services used

| Category    | Service              | Role                              |
|-------------|----------------------|-----------------------------------|
| Compute     | AWS Lambda           | Chat orchestrator + ingestion     |
| Networking  | Amazon API Gateway   | REST entry point (POST /chat)     |
| Identity    | Amazon Cognito       | User pool + JWT authorizer        |
| Storage     | Amazon DynamoDB (x2) | Session memory + vector store     |
| Storage     | Amazon S3            | Document corpus + traces          |
| Security    | AWS Secrets Manager  | LLM and embeddings API keys       |
| Integration | S3 Event Notify      | Event-driven ingestion trigger    |
| Monitoring  | Amazon CloudWatch    | Logs for both Lambdas             |

## Repository layout

    infra/          Terraform IaC (one file per concern)
    orchestrator/   Chat Lambda — agent loop, memory, retrieval tool
    ingestion/      Ingest Lambda — chunk + embed + store
    tests/          Offline unit tests (calculator, cosine, chunker)
    .github/        CI workflow (lint, test, terraform validate)

## Deploy

    cd infra && terraform init && terraform apply
    aws secretsmanager put-secret-value --secret-id agent-platform/llm-api-key        --secret-string 'YOUR_LLM_KEY'
    aws secretsmanager put-secret-value --secret-id agent-platform/embeddings-api-key --secret-string 'YOUR_EMBEDDINGS_KEY'
    aws s3 cp handbook.txt s3://<corpus_bucket>/corpus/handbook.txt

## Test

    pip install -r requirements-dev.txt && ruff check . && pytest -q

## CI/CD

- CI runs on every push/PR: Ruff lint, unit tests, terraform validate — no cloud
  credentials needed.
- CD deploys with short-lived credentials in GitHub secrets. The lab forbids IAM
  role creation, so GitHub OIDC (the production approach) is unavailable; this
  trade-off is documented.

## AI-assisted development disclosure

Portions of this codebase were generated with AI assistance and then reviewed,
tested, and integrated by the author. The exact percentage is disclosed in the
project report.

## Limitations (lab environment)

- No custom IAM roles: Lambdas reuse the pre-provisioned LabRole.
- No Amazon Bedrock: inference and embeddings use external APIs.
- Brute-force vector search: fine at this corpus size; production would use ANN
  (pgvector / OpenSearch).
- Local Terraform state: a team setup would use a remote backend.
