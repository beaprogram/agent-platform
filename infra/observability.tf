resource "aws_cloudwatch_dashboard" "ops" {
  dashboard_name = "${var.project_name}-ops"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = "# Agent Platform — Operations\nServerless agentic RAG assistant · us-east-1 · Lambda + API Gateway + DynamoDB"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 12
        height = 6
        properties = {
          title   = "Lambda invocations"
          region  = "us-east-1"
          view    = "timeSeries"
          stacked = false
          stat    = "Sum"
          period  = 300
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.chat.function_name, { label = "chat" }],
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.ingest.function_name, { label = "ingest" }],
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.frontend.function_name, { label = "frontend" }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 2
        width  = 12
        height = 6
        properties = {
          title   = "Lambda errors + throttles"
          region  = "us-east-1"
          view    = "timeSeries"
          stacked = false
          stat    = "Sum"
          period  = 300
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.chat.function_name, { label = "chat errors" }],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.ingest.function_name, { label = "ingest errors" }],
            ["AWS/Lambda", "Throttles", "FunctionName", aws_lambda_function.chat.function_name, { label = "chat throttles" }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 12
        height = 6
        properties = {
          title  = "Chat Lambda duration (ms)"
          region = "us-east-1"
          view   = "timeSeries"
          period = 300
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.chat.function_name, { stat = "Average", label = "avg" }],
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.chat.function_name, { stat = "p99", label = "p99" }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 8
        width  = 12
        height = 6
        properties = {
          title   = "API Gateway requests + errors"
          region  = "us-east-1"
          view    = "timeSeries"
          stacked = false
          stat    = "Sum"
          period  = 300
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.api.name, "Stage", aws_api_gateway_stage.prod.stage_name, { label = "requests" }],
            ["AWS/ApiGateway", "4XXError", "ApiName", aws_api_gateway_rest_api.api.name, "Stage", aws_api_gateway_stage.prod.stage_name, { label = "4XX" }],
            ["AWS/ApiGateway", "5XXError", "ApiName", aws_api_gateway_rest_api.api.name, "Stage", aws_api_gateway_stage.prod.stage_name, { label = "5XX" }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 14
        width  = 12
        height = 6
        properties = {
          title  = "API Gateway latency (ms)"
          region = "us-east-1"
          view   = "timeSeries"
          period = 300
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiName", aws_api_gateway_rest_api.api.name, "Stage", aws_api_gateway_stage.prod.stage_name, { stat = "Average", label = "avg" }],
            ["AWS/ApiGateway", "Latency", "ApiName", aws_api_gateway_rest_api.api.name, "Stage", aws_api_gateway_stage.prod.stage_name, { stat = "p99", label = "p99" }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 14
        width  = 12
        height = 6
        properties = {
          title   = "DynamoDB consumed capacity"
          region  = "us-east-1"
          view    = "timeSeries"
          stacked = false
          stat    = "Sum"
          period  = 300
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.sessions.name, { label = "sessions read" }],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", aws_dynamodb_table.sessions.name, { label = "sessions write" }],
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.corpus_chunks.name, { label = "corpus read" }],
          ]
        }
      },
    ]
  })
}

output "dashboard_url" {
  value = "https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/${aws_cloudwatch_dashboard.ops.dashboard_name}"
}
