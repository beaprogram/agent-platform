resource "aws_dynamodb_table" "corpus_chunks" {
  name         = "${var.project_name}-corpus-chunks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "doc_id"
  range_key    = "chunk_id"

  attribute {
    name = "doc_id"
    type = "S"
  }

  attribute {
    name = "chunk_id"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret" "embeddings_key" {
  name                    = "${var.project_name}/embeddings-api-key"
  recovery_window_in_days = 0

  tags = {
    Project = var.project_name
  }
}
