resource "aws_dynamodb_table" "invoices" {
  name           = "${var.project}-${var.environment}-invoices"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "invoice_id"

  attribute {
    name = "invoice_id"
    type = "S"
  }

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}
