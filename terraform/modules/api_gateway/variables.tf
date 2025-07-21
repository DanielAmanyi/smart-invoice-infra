variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g., dev, prod)"
  type        = string
}

variable "lambda_invoke_arn" {
  description = "Invoke ARN of the upload Lambda function"
  type        = string
}
