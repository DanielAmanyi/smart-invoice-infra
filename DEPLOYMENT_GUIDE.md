# Deployment Guide - Real AI/ML Implementation

## Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Terraform installed** (>= 1.3.0)
3. **AWS Account with access to**:
   - Lambda
   - S3
   - DynamoDB
   - API Gateway
   - Textract
   - Bedrock (Claude models)

## Step 1: Enable Amazon Bedrock Models

Before deploying, you need to enable Claude models in Bedrock:

1. Go to AWS Console → Amazon Bedrock
2. Navigate to "Model access" in the left sidebar
3. Click "Enable specific models"
4. Enable:
   - `Claude 3 Haiku` (anthropic.claude-3-haiku-20240307-v1:0)
   - `Claude 3 Sonnet` (anthropic.claude-3-sonnet-20240229-v1:0) - optional

**Note**: Model access may take a few minutes to activate.

## Step 2: Configure Terraform Backend

```bash
# Edit terraform/backend.tf with your S3 bucket for state
# Example:
terraform {
  backend "s3" {
    bucket = "your-terraform-state-bucket"
    key    = "smart-invoice/terraform.tfstate"
    region = "us-east-1"
  }
}
```

## Step 3: Set Variables

Create `terraform/terraform.tfvars`:

```hcl
region      = "us-east-1"  # Choose region with Textract + Bedrock
project     = "smart-invoice"
environment = "dev"

# Optional: Enable enhanced features
enable_monitoring = true
alert_email      = "your-email@example.com"
```

## Step 4: Deploy Infrastructure

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Package Lambda functions with real AI/ML code
cd ..
./zip_deploy.sh

# Return to terraform directory
cd terraform

# Plan deployment
terraform plan

# Deploy (this will create real AWS resources)
terraform apply
```

## Step 5: Test the Pipeline

After deployment, you'll get outputs like:

```
api_gateway_url = "https://abc123.execute-api.us-east-1.amazonaws.com/dev"
s3_bucket_name = "smart-invoice-dev-invoices"
```

### Test with a sample invoice:

```bash
# Upload a test invoice (PDF or image)
curl -X POST https://your-api-gateway-url/upload \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test-invoice.pdf",
    "file_base64": "'$(base64 -i sample-invoice.pdf)'"
  }'
```

### Check processing results:

```bash
# Check DynamoDB table for results
aws dynamodb scan --table-name smart-invoice-dev-invoices --region us-east-1
```

## Step 6: Monitor Costs

The real AI/ML implementation has usage-based costs:

### Cost Monitoring Commands:

```bash
# Check Textract usage
aws logs filter-log-events \
  --log-group-name /aws/lambda/smart-invoice-dev-inference \
  --filter-pattern "Textract" \
  --region us-east-1

# Check Bedrock usage
aws logs filter-log-events \
  --log-group-name /aws/lambda/smart-invoice-dev-inference \
  --filter-pattern "Bedrock" \
  --region us-east-1
```

### Expected Costs (per 1000 invoices):
- **Textract**: ~$1.50
- **Bedrock**: ~$0.50
- **Lambda**: ~$0.10
- **Other AWS services**: ~$0.10
- **Total**: ~$2.20 per 1000 invoices

## Step 7: Troubleshooting

### Common Issues:

1. **Bedrock Access Denied**
   - Ensure models are enabled in Bedrock console
   - Check IAM permissions include `bedrock:InvokeModel`

2. **Textract Unsupported Document**
   - Ensure file is PDF, PNG, JPG, TIFF, or BMP
   - Check file size limits (10MB for synchronous processing)

3. **Lambda Timeout**
   - Increase timeout in `terraform/modules/lambda_infer/main.tf`
   - Default is 60 seconds, increase to 300 if needed

### Debug Logs:

```bash
# View Lambda logs
aws logs tail /aws/lambda/smart-invoice-dev-inference --follow --region us-east-1

# View API Gateway logs
aws logs tail /aws/lambda/smart-invoice-dev-upload --follow --region us-east-1
```

## Step 8: Cleanup

To avoid ongoing costs:

```bash
cd terraform
terraform destroy
```

**Warning**: This will delete all resources including stored invoice data.

## Production Considerations

For production deployment:

1. **Enable monitoring module** with CloudWatch dashboards
2. **Set up proper alerting** for failures and cost thresholds
3. **Configure VPC endpoints** for enhanced security
4. **Enable S3 versioning and lifecycle policies**
5. **Set up proper backup strategies** for DynamoDB
6. **Implement rate limiting** and WAF rules
7. **Use separate environments** (dev/staging/prod)

## Security Best Practices

1. **Least privilege IAM policies**
2. **Enable CloudTrail** for audit logging
3. **Use KMS encryption** for sensitive data
4. **Implement proper CORS policies**
5. **Regular security reviews** of extracted data

## Performance Tuning

1. **Monitor Lambda cold starts** - consider provisioned concurrency
2. **Optimize Textract calls** - batch processing for multiple pages
3. **Cache frequent queries** - implement ElastiCache if needed
4. **Monitor DynamoDB performance** - enable auto-scaling
