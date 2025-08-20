# CloudWatch Dashboard for Invoice Processing Pipeline
resource "aws_cloudwatch_dashboard" "invoice_pipeline" {
  dashboard_name = "${var.project}-${var.environment}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", var.upload_function_name],
            ["AWS/Lambda", "Duration", "FunctionName", var.inference_function_name],
            ["AWS/Lambda", "Errors", "FunctionName", var.upload_function_name],
            ["AWS/Lambda", "Errors", "FunctionName", var.inference_function_name]
          ]
          period = 300
          stat   = "Average"
          region = var.region
          title  = "Lambda Performance Metrics"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/S3", "NumberOfObjects", "BucketName", var.s3_bucket_name, "StorageType", "AllStorageTypes"],
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", var.dynamodb_table_name],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", var.dynamodb_table_name]
          ]
          period = 300
          stat   = "Sum"
          region = var.region
          title  = "Storage Metrics"
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = toset([var.upload_function_name, var.inference_function_name])

  alarm_name          = "${each.key}-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = each.key
  }
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project}-${var.environment}-alerts"
}

# X-Ray Tracing
resource "aws_lambda_function" "enable_xray" {
  count = 0 # Set to 1 to enable, requires updating Lambda modules

  tracing_config {
    mode = "Active"
  }
}
