data "archive_file" "ingest" {
  type        = "zip"
  source_dir  = "${path.module}/../ingestion"
  output_path = "${path.module}/ingest.zip"
  excludes    = [".gitkeep"]
}

resource "aws_lambda_function" "ingest" {
  function_name    = "${var.project_name}-ingest"
  role             = data.aws_iam_role.lab.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.ingest.output_path
  source_code_hash = data.archive_file.ingest.output_base64sha256
  timeout          = 120
  memory_size      = 256

  environment {
    variables = {
      CHUNKS_TABLE          = aws_dynamodb_table.corpus_chunks.name
      EMBEDDINGS_SECRET_ARN = aws_secretsmanager_secret.embeddings_key.arn
      EMBEDDINGS_API_URL    = "https://api.jina.ai/v1/embeddings"
      EMBEDDINGS_MODEL      = "jina-embeddings-v3"
      CHUNK_SIZE            = "200"
      CHUNK_OVERLAP         = "40"
    }
  }
}

resource "aws_lambda_permission" "s3_invoke_ingest" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.corpus.arn
}

resource "aws_s3_bucket_notification" "corpus" {
  bucket = aws_s3_bucket.corpus.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingest.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "corpus/"
  }

  depends_on = [aws_lambda_permission.s3_invoke_ingest]
}
