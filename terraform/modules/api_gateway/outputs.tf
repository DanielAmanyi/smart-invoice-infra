output "api_id" {
  description = "API Gateway ID"
  value       = aws_api_gateway_rest_api.smart_invoice_api.id
}

output "invoke_url" {
  description = "Base invoke URL for the deployed API"
  value       = "https://${aws_api_gateway_rest_api.smart_invoice_api.id}.execute-api.${var.region}.amazonaws.com/${var.environment}"
}
