# SQS Dead Letter Queue for failed processing
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.project}-${var.environment}-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

# SQS Queue for retry mechanism
resource "aws_sqs_queue" "retry_queue" {
  name                      = "${var.project}-${var.environment}-retry"
  visibility_timeout_seconds = 300
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

# Lambda function for processing DLQ messages
resource "aws_lambda_function" "dlq_processor" {
  filename         = var.dlq_lambda_zip_path
  function_name    = "${var.project}-${var.environment}-dlq-processor"
  role            = var.lambda_role_arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300

  environment {
    variables = {
      SNS_TOPIC_ARN = var.sns_topic_arn
    }
  }

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

# EventBridge rule for DLQ monitoring
resource "aws_cloudwatch_event_rule" "dlq_monitor" {
  name        = "${var.project}-${var.environment}-dlq-monitor"
  description = "Monitor DLQ for failed invoice processing"

  event_pattern = jsonencode({
    source      = ["aws.sqs"]
    detail-type = ["SQS Queue Attributes Changed"]
    detail = {
      queueName = [aws_sqs_queue.dlq.name]
    }
  })
}

resource "aws_cloudwatch_event_target" "dlq_target" {
  rule      = aws_cloudwatch_event_rule.dlq_monitor.name
  target_id = "DLQProcessorTarget"
  arn       = aws_lambda_function.dlq_processor.arn
}
