# Enhanced main.tf with new modules
terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# --- Get current account ID for dynamic ARNs ---
data "aws_caller_identity" "current" {}

# --- Existing modules (unchanged) ---
module "s3_invoice_bucket" {
  source      = "./modules/s3_invoice_bucket"
  project     = var.project
  environment = var.environment
}

module "dynamodb" {
  source      = "./modules/dynamodb"
  project     = var.project
  environment = var.environment
}

module "iam" {
  source             = "./modules/iam"
  project            = var.project
  environment        = var.environment
  s3_bucket_arn      = module.s3_invoice_bucket.bucket_arn
  dynamodb_table_arn = module.dynamodb.table_arn
}

module "lambda_upload" {
  source                  = "./modules/lambda_upload"
  project                 = var.project
  environment             = var.environment
  lambda_zip_path         = "${path.module}/../lambda/upload_handler/lambda.zip"
  lambda_role_arn         = module.iam.lambda_role_arn
  s3_bucket_name          = module.s3_invoice_bucket.bucket_name
  api_gateway_source_arn  = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:${module.api_gateway.api_id}/${var.environment}/POST/upload"
}

module "lambda_infer" {
  source               = "./modules/lambda_infer"
  project              = var.project
  environment          = var.environment
  lambda_zip_path      = "${path.module}/../lambda/inference_handler/lambda.zip"
  lambda_role_arn      = module.iam.lambda_role_arn
  s3_bucket_id         = module.s3_invoice_bucket.bucket_name
  s3_bucket_arn        = module.s3_invoice_bucket.bucket_arn
  dynamodb_table_name  = module.dynamodb.table_name
}

module "api_gateway" {
  source            = "./modules/api_gateway"
  project           = var.project
  environment       = var.environment
  lambda_invoke_arn = module.lambda_upload.lambda_arn
}

# --- NEW ENHANCEMENT MODULES ---

# Monitoring and Observability
module "monitoring" {
  source                   = "./modules/monitoring"
  project                  = var.project
  environment              = var.environment
  region                   = var.region
  upload_function_name     = module.lambda_upload.function_name
  inference_function_name  = module.lambda_infer.function_name
  s3_bucket_name          = module.s3_invoice_bucket.bucket_name
  dynamodb_table_name     = module.dynamodb.table_name
}

# Error Handling and Dead Letter Queues
module "error_handling" {
  source              = "./modules/error_handling"
  project             = var.project
  environment         = var.environment
  lambda_role_arn     = module.iam.lambda_role_arn
  dlq_lambda_zip_path = "${path.module}/../lambda/dlq_processor/lambda.zip"
  sns_topic_arn       = module.monitoring.sns_topic_arn
}

# Security Enhancements
module "security" {
  source              = "./modules/security"
  project             = var.project
  environment         = var.environment
  region              = var.region
  api_gateway_arn     = module.api_gateway.api_arn
  create_vpc_endpoint = var.enable_vpc_endpoint
  vpc_id              = var.vpc_id
}

# Performance Optimizations
module "performance" {
  source                        = "./modules/performance"
  project                       = var.project
  environment                   = var.environment
  s3_bucket_name               = module.s3_invoice_bucket.bucket_name
  dynamodb_table_name          = module.dynamodb.table_name
  upload_function_name         = module.lambda_upload.function_name
  enable_provisioned_concurrency = var.enable_provisioned_concurrency
  provisioned_concurrency_count = var.provisioned_concurrency_count
  enable_cache                 = var.enable_cache
  vpc_id                       = var.vpc_id
  vpc_cidr                     = var.vpc_cidr
  private_subnet_ids           = var.private_subnet_ids
}
