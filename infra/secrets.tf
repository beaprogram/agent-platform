resource "aws_secretsmanager_secret" "llm_key" {
  name                    = "${var.project_name}/llm-api-key"
  recovery_window_in_days = 0
}
