# Cost Control Module - Budget alerts and spending limits

resource "aws_budgets_budget" "invoice_processing" {
  name         = "${var.project}-${var.environment}-budget"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  
  cost_filters = {
    Service = [
      "Amazon Textract",
      "Amazon Bedrock",
      "AWS Lambda",
      "Amazon DynamoDB",
      "Amazon S3"
    ]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

# CloudWatch alarm for high Textract costs
resource "aws_cloudwatch_metric_alarm" "textract_cost_alarm" {
  alarm_name          = "${var.project}-${var.environment}-textract-cost-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400" # 24 hours
  statistic           = "Maximum"
  threshold           = var.daily_textract_threshold
  alarm_description   = "This metric monitors Textract daily costs"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    Currency    = "USD"
    ServiceName = "AmazonTextract"
  }

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

# CloudWatch alarm for high Bedrock costs
resource "aws_cloudwatch_metric_alarm" "bedrock_cost_alarm" {
  alarm_name          = "${var.project}-${var.environment}-bedrock-cost-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400" # 24 hours
  statistic           = "Maximum"
  threshold           = var.daily_bedrock_threshold
  alarm_description   = "This metric monitors Bedrock daily costs"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    Currency    = "USD"
    ServiceName = "AmazonBedrock"
  }

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

# SNS topic for cost alerts
resource "aws_sns_topic" "cost_alerts" {
  name = "${var.project}-${var.environment}-cost-alerts"

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_sns_topic_subscription" "cost_email" {
  topic_arn = aws_sns_topic.cost_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Lambda function to implement cost-based throttling
resource "aws_lambda_function" "cost_monitor" {
  filename         = "${path.module}/cost_monitor.zip"
  function_name    = "${var.project}-${var.environment}-cost-monitor"
  role            = aws_iam_role.cost_monitor_role.arn
  handler         = "cost_monitor.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60

  environment {
    variables = {
      DAILY_COST_LIMIT = var.daily_cost_limit
      SNS_TOPIC_ARN    = aws_sns_topic.cost_alerts.arn
    }
  }

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

# IAM role for cost monitor Lambda
resource "aws_iam_role" "cost_monitor_role" {
  name = "${var.project}-${var.environment}-cost-monitor-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "cost_monitor_policy" {
  name = "${var.project}-${var.environment}-cost-monitor-policy"
  role = aws_iam_role.cost_monitor_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetUsageReport"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.cost_alerts.arn
      }
    ]
  })
}

# EventBridge rule to trigger cost monitoring daily
resource "aws_cloudwatch_event_rule" "daily_cost_check" {
  name                = "${var.project}-${var.environment}-daily-cost-check"
  description         = "Trigger cost monitoring daily"
  schedule_expression = "cron(0 8 * * ? *)" # 8 AM UTC daily

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_cloudwatch_event_target" "cost_monitor_target" {
  rule      = aws_cloudwatch_event_rule.daily_cost_check.name
  target_id = "CostMonitorTarget"
  arn       = aws_lambda_function.cost_monitor.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_monitor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_cost_check.arn
}
