output "lambda_arn" {
  description = "ARN of the upload Lambda function"
  value       = aws_lambda_function.upload_handler.arn
}

output "lambda_name" {
  description = "Name of the upload Lambda function"
  value       = aws_lambda_function.upload_handler.function_name
}
