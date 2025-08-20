# Lambda Provisioned Concurrency for consistent performance
resource "aws_lambda_provisioned_concurrency_config" "upload_handler" {
  count                             = var.enable_provisioned_concurrency ? 1 : 0
  function_name                     = var.upload_function_name
  provisioned_concurrent_executions = var.provisioned_concurrency_count
  qualifier                         = aws_lambda_alias.upload_handler[0].name
}

resource "aws_lambda_alias" "upload_handler" {
  count            = var.enable_provisioned_concurrency ? 1 : 0
  name             = "live"
  description      = "Live alias for upload handler"
  function_name    = var.upload_function_name
  function_version = "$LATEST"
}

# S3 Transfer Acceleration
resource "aws_s3_bucket_accelerate_configuration" "invoice_bucket" {
  bucket = var.s3_bucket_name
  status = "Enabled"
}

# ElastiCache for caching frequent queries (optional)
resource "aws_elasticache_subnet_group" "cache_subnet" {
  count      = var.enable_cache ? 1 : 0
  name       = "${var.project}-${var.environment}-cache-subnet"
  subnet_ids = var.private_subnet_ids
}

resource "aws_elasticache_cluster" "invoice_cache" {
  count            = var.enable_cache ? 1 : 0
  cluster_id       = "${var.project}-${var.environment}-cache"
  engine           = "redis"
  node_type        = "cache.t3.micro"
  num_cache_nodes  = 1
  parameter_group_name = "default.redis7"
  port             = 6379
  subnet_group_name = aws_elasticache_subnet_group.cache_subnet[0].name
  security_group_ids = [aws_security_group.cache[0].id]

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_security_group" "cache" {
  count       = var.enable_cache ? 1 : 0
  name_prefix = "${var.project}-${var.environment}-cache-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

# DynamoDB Auto Scaling
resource "aws_appautoscaling_target" "dynamodb_table_read_target" {
  max_capacity       = 100
  min_capacity       = 5
  resource_id        = "table/${var.dynamodb_table_name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "dynamodb_table_read_policy" {
  name               = "${var.project}-${var.environment}-DynamoDBReadCapacityUtilization"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.dynamodb_table_read_target.resource_id
  scalable_dimension = aws_appautoscaling_target.dynamodb_table_read_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.dynamodb_table_read_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = 70
  }
}
