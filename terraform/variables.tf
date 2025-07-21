variable "project" {
  description = "Name of the project"
  type        = string
  default     = "smart-invoice-infra"
}

variable "environment" {
  description = "Deployment environment (e.g., dev, prod)"
  type        = string
  default     = "prod"
}

variable "region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}
