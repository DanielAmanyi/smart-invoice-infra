variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD"
  type        = string
  default     = "100"
}

variable "daily_textract_threshold" {
  description = "Daily Textract cost threshold in USD"
  type        = string
  default     = "10"
}

variable "daily_bedrock_threshold" {
  description = "Daily Bedrock cost threshold in USD"
  type        = string
  default     = "5"
}

variable "daily_cost_limit" {
  description = "Daily total cost limit in USD"
  type        = string
  default     = "20"
}

variable "alert_email" {
  description = "Email address for cost alerts"
  type        = string
}
