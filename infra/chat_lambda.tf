data "archive_file" "chat" {
  type        = "zip"
  source_dir  = "${path.module}/../orchestrator"
  output_path = "${path.module}/chat.zip"
  excludes    = [".gitkeep"]
}

resource "aws_lambda_function" "chat" {
  tracing_config {
    mode = "Active"
  }
  function_name    = "${var.project_name}-chat"
  role             = data.aws_iam_role.lab.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.chat.output_path
  source_code_hash = data.archive_file.chat.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      SESSIONS_TABLE        = aws_dynamodb_table.sessions.name
      LLM_SECRET_ARN        = aws_secretsmanager_secret.llm_key.arn
      LLM_MODEL             = "llama-3.3-70b-versatile"
      LLM_API_URL           = "https://api.groq.com/openai/v1/chat/completions"
      AGENT_MAX_ITERS       = "5"
      CHUNKS_TABLE          = aws_dynamodb_table.corpus_chunks.name
      EMBEDDINGS_SECRET_ARN = aws_secretsmanager_secret.embeddings_key.arn
      EMBEDDINGS_API_URL    = "https://api.jina.ai/v1/embeddings"
      EMBEDDINGS_MODEL      = "jina-embeddings-v3"
    }
  }
}
