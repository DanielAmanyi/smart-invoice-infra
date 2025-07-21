terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "smart-invoice-infra/prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "your-terraform-lock-table"
    encrypt        = true
  }
}
