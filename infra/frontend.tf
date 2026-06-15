resource "aws_s3_bucket" "site" {
  bucket_prefix = "${var.project_name}-site-"
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "index" {
  bucket       = aws_s3_bucket.site.id
  key          = "index.html"
  source       = "${path.module}/../frontend/index.html"
  etag         = filemd5("${path.module}/../frontend/index.html")
  content_type = "text/html"
}

data "archive_file" "frontend" {
  type        = "zip"
  source_dir  = "${path.module}/../frontend_lambda"
  output_path = "${path.module}/frontend.zip"
}

resource "aws_lambda_function" "frontend" {
  function_name    = "${var.project_name}-frontend"
  role             = data.aws_iam_role.lab.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.frontend.output_path
  source_code_hash = data.archive_file.frontend.output_base64sha256
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      SITE_BUCKET = aws_s3_bucket.site.id
    }
  }
}

resource "aws_lambda_permission" "apigw_frontend" {
  statement_id  = "AllowAPIGatewayInvokeFrontend"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.frontend.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

resource "aws_api_gateway_resource" "app" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "app"
}

resource "aws_api_gateway_method" "app_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.app.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "app_get" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.app.id
  http_method             = aws_api_gateway_method.app_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.frontend.invoke_arn
}

output "site_url" {
  value = "${aws_api_gateway_stage.prod.invoke_url}/app"
}
