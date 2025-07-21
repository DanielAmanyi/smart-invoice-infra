variable "project" {
  description = "Name of the project"
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
  description = "ARN of the IAM role for the Lambda function"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket where files will be stored"
  type        = string
}

variable "api_gateway_source_arn" {
  description = "Source ARN from API Gateway to allow invoke permissions"
  type        = string
}
