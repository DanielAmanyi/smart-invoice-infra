output "bucket_arn" {
  description = "Full ARN of the invoice S3 bucket"
  value       = aws_s3_bucket.invoice_storage.arn
}
