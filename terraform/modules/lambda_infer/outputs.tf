output "lambda_arn" {
  description = "ARN of the inference Lambda function"
  value       = aws_lambda_function.inference_handler.arn
}

output "lambda_name" {
  description = "Name of the inference Lambda function"
  value       = aws_lambda_function.inference_handler.function_name
}
