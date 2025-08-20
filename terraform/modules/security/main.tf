# WAF for API Gateway
resource "aws_wafv2_web_acl" "api_protection" {
  name  = "${var.project}-${var.environment}-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # Rate limiting rule
  rule {
    name     = "RateLimitRule"
    priority = 1

    override_action {
      none {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }

    action {
      block {}
    }
  }

  # AWS Managed Rules
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

# Associate WAF with API Gateway
resource "aws_wafv2_web_acl_association" "api_gateway" {
  resource_arn = var.api_gateway_arn
  web_acl_arn  = aws_wafv2_web_acl.api_protection.arn
}

# VPC Endpoint for S3 (optional for enhanced security)
resource "aws_vpc_endpoint" "s3" {
  count = var.create_vpc_endpoint ? 1 : 0
  
  vpc_id       = var.vpc_id
  service_name = "com.amazonaws.${var.region}.s3"
  
  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

# KMS Key for enhanced encryption
resource "aws_kms_key" "invoice_encryption" {
  description             = "KMS key for invoice encryption"
  deletion_window_in_days = 7

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_kms_alias" "invoice_encryption" {
  name          = "alias/${var.project}-${var.environment}-invoices"
  target_key_id = aws_kms_key.invoice_encryption.key_id
}
