variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g., dev, prod)"
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to the packaged Lambda zip file"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM role ARN assigned to the Lambda function"
  type        = string
}

variable "s3_bucket_id" {
  description = "ID of the S3 bucket triggering the Lambda"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket triggering the Lambda"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table to write extracted results"
  type        = string
}
