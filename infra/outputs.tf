output "sessions_table" {
  value = aws_dynamodb_table.sessions.name
}

output "corpus_bucket" {
  value = aws_s3_bucket.corpus.bucket
}

output "api_url" {
  value = "${aws_api_gateway_stage.prod.invoke_url}/chat"
}

output "user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "user_pool_client_id" {
  value = aws_cognito_user_pool_client.web.id
}
