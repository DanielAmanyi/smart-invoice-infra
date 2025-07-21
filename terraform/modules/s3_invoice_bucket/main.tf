resource "aws_s3_bucket" "invoice_storage" {
  bucket = "${var.project}-${var.environment}-invoices"

  tags = {
    Name        = "invoice-storage"
    Environment = var.environment
    Project     = var.project
  }

  force_destroy = true
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.invoice_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "sse" {
  bucket = aws_s3_bucket.invoice_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "block_all" {
  bucket = aws_s3_bucket.invoice_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
