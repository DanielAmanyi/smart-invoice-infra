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

# --- MODULE: S3 Bucket for Invoices ---
module "s3_invoice_bucket" {
  source      = "./modules/s3_invoice_bucket"
  project     = var.project
  environment = var.environment
}

# --- MODULE: DynamoDB Table ---
module "dynamodb" {
  source      = "./modules/dynamodb"
  project     = var.project
  environment = var.environment
}

# --- MODULE: IAM Role for Lambda Functions ---
module "iam" {
  source             = "./modules/iam"
  project            = var.project
  environment        = var.environment
  s3_bucket_arn      = module.s3_invoice_bucket.bucket_arn
  dynamodb_table_arn = module.dynamodb.table_arn
}

# --- MODULE: Upload Lambda Function ---
module "lambda_upload" {
  source                  = "./modules/lambda_upload"
  project                 = var.project
  environment             = var.environment
  lambda_zip_path         = "${path.module}/../lambda/upload_handler/lambda.zip"
  lambda_role_arn         = module.iam.lambda_role_arn
  s3_bucket_name          = module.s3_invoice_bucket.bucket_name
  api_gateway_source_arn  = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:${module.api_gateway.api_id}/${var.environment}/POST/upload"
}

# --- MODULE: Inference Lambda Function ---
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

# --- MODULE: API Gateway ---
module "api_gateway" {
  source            = "./modules/api_gateway"
  project           = var.project
  environment       = var.environment
  lambda_invoke_arn = module.lambda_upload.lambda_arn
}
