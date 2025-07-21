output "s3_bucket_name" {
  description = "Name of the invoice S3 bucket"
  value       = module.s3_invoice_bucket.bucket_name
}

output "upload_lambda_arn" {
  description = "ARN of the upload handler Lambda function"
  value       = module.lambda_upload.lambda_arn
}

output "inference_lambda_arn" {
  description = "ARN of the inference Lambda function"
  value       = module.lambda_infer.lambda_arn
}
