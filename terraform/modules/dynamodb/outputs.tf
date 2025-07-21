output "table_arn" {
  description = "Full ARN of the DynamoDB table"
  value       = aws_dynamodb_table.invoices.arn
}
