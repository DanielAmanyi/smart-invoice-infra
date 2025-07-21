resource "aws_lambda_function" "upload_handler" {
  function_name = "${var.project}-${var.environment}-upload-handler"
  role          = var.lambda_role_arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.10"
  timeout       = 10
  memory_size   = 128

  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)

  environment {
    variables = {
      BUCKET_NAME = var.s3_bucket_name
    }
  }

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = var.api_gateway_source_arn
}
