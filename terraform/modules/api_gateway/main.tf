resource "aws_api_gateway_rest_api" "smart_invoice_api" {
  name        = "${var.project}-${var.environment}-api"
  description = "Smart Invoice API Gateway"
}

resource "aws_api_gateway_resource" "upload" {
  rest_api_id = aws_api_gateway_rest_api.smart_invoice_api.id
  parent_id   = aws_api_gateway_rest_api.smart_invoice_api.root_resource_id
  path_part   = "upload"
}

resource "aws_api_gateway_method" "upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.smart_invoice_api.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "upload_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.smart_invoice_api.id
  resource_id             = aws_api_gateway_resource.upload.id
  http_method             = aws_api_gateway_method.upload_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

resource "aws_api_gateway_deployment" "deployment" {
  depends_on = [
    aws_api_gateway_integration.upload_lambda
  ]
  rest_api_id = aws_api_gateway_rest_api.smart_invoice_api.id
  stage_name  = var.environment
}
