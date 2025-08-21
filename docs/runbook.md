# Smart Invoice AI Pipeline - Operations Runbook

## Overview

This runbook provides operational procedures for monitoring, troubleshooting, and maintaining the Smart Invoice AI Pipeline in production environments.

## System Architecture Quick Reference

```
User → API Gateway → Upload Lambda → S3 → Inference Lambda → DynamoDB
                                    ↓
                              AWS Textract + Amazon Bedrock
```

## Key Metrics to Monitor

### Performance Metrics
- **Lambda Duration**: Upload < 5s, Inference < 60s
- **API Gateway Latency**: < 2s for uploads
- **Error Rate**: < 1% overall
- **Textract Processing Time**: < 30s per document
- **Bedrock Response Time**: < 10s per request

### Cost Metrics
- **Daily Textract Costs**: Monitor for spikes
- **Daily Bedrock Costs**: Track token usage
- **Lambda Invocations**: Watch for unusual patterns
- **S3 Storage Costs**: Monitor growth rate

### Business Metrics
- **Documents Processed**: Daily/hourly volumes
- **Extraction Accuracy**: Confidence scores
- **Processing Success Rate**: End-to-end completion

## Incident Response Procedures

### High Error Rate (>5% in 15 minutes)

#### Immediate Actions
1. **Check CloudWatch Logs**
   ```bash
   aws logs tail /aws/lambda/smart-invoice-prod-inference --follow --region us-east-1
   aws logs tail /aws/lambda/smart-invoice-prod-upload --follow --region us-east-1
   ```

2. **Verify Service Health**
   ```bash
   # Check Textract service status
   aws textract describe-document-text-detection --job-id dummy-id --region us-east-1 2>&1 | grep -i "service"
   
   # Check Bedrock model access
   aws bedrock list-foundation-models --region us-east-1
   ```

3. **Review Recent Deployments**
   - Check if any recent deployments correlate with error spike
   - Review Terraform state changes

#### Investigation Steps
1. **Analyze Error Patterns**
   ```bash
   # Get error distribution
   aws logs filter-log-events \
     --log-group-name /aws/lambda/smart-invoice-prod-inference \
     --start-time $(date -d '1 hour ago' +%s)000 \
     --filter-pattern "ERROR" \
     --region us-east-1
   ```

2. **Check Dead Letter Queue**
   ```bash
   aws sqs get-queue-attributes \
     --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT/smart-invoice-prod-inference-dlq \
     --attribute-names ApproximateNumberOfMessages
   ```

3. **Verify IAM Permissions**
   - Ensure Lambda execution role has required permissions
   - Check for any recent IAM policy changes

#### Resolution Actions
- **If Textract Issues**: Check service limits and quotas
- **If Bedrock Issues**: Verify model access and quotas
- **If Lambda Issues**: Check memory/timeout settings
- **If DynamoDB Issues**: Verify table capacity and throttling

### Cost Spike Alert

#### Immediate Actions
1. **Identify Cost Source**
   ```bash
   # Check today's costs by service
   aws ce get-cost-and-usage \
     --time-period Start=$(date +%Y-%m-%d),End=$(date -d '+1 day' +%Y-%m-%d) \
     --granularity DAILY \
     --metrics BlendedCost \
     --group-by Type=DIMENSION,Key=SERVICE
   ```

2. **Check Processing Volume**
   ```bash
   # Count Lambda invocations in last hour
   aws logs filter-log-events \
     --log-group-name /aws/lambda/smart-invoice-prod-inference \
     --start-time $(date -d '1 hour ago' +%s)000 \
     --filter-pattern "Processing invoice" \
     --region us-east-1 | grep -c "Processing invoice"
   ```

#### Investigation Steps
1. **Analyze Usage Patterns**
   - Check for unusual document upload patterns
   - Verify if large documents are being processed
   - Look for retry loops or failed processing

2. **Review Cost Breakdown**
   - Textract: Check document size and page count
   - Bedrock: Monitor token usage and model calls
   - Lambda: Review execution duration and memory usage

#### Mitigation Actions
- **Implement Rate Limiting**: Temporarily reduce API Gateway throttling
- **Enable Cost Controls**: Activate budget alerts and spending limits
- **Optimize Processing**: Switch to rule-based extraction temporarily

### Service Degradation

#### Textract Service Issues
```bash
# Check Textract limits
aws service-quotas get-service-quota \
  --service-code textract \
  --quota-code L-D7D4C6F8 \
  --region us-east-1

# Monitor Textract errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/smart-invoice-prod-inference \
  --filter-pattern "TextractError" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Resolution Steps:**
1. Check AWS Service Health Dashboard
2. Implement exponential backoff in retry logic
3. Consider switching to synchronous processing for smaller documents
4. Contact AWS Support if service-wide issues

#### Bedrock Service Issues
```bash
# Check Bedrock model availability
aws bedrock list-foundation-models --region us-east-1 | grep claude

# Monitor Bedrock errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/smart-invoice-prod-inference \
  --filter-pattern "BedrockError" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Resolution Steps:**
1. Verify model access permissions
2. Check quota limits for Bedrock
3. Implement fallback to rule-based extraction
4. Consider using alternative models if available

### Performance Degradation

#### Lambda Timeout Issues
```bash
# Check for timeout errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/smart-invoice-prod-inference \
  --filter-pattern "Task timed out" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Resolution Steps:**
1. Increase Lambda timeout (current: 300s)
2. Optimize code for better performance
3. Consider increasing memory allocation
4. Implement document size limits

#### Cold Start Issues
```bash
# Monitor cold start frequency
aws logs filter-log-events \
  --log-group-name /aws/lambda/smart-invoice-prod-inference \
  --filter-pattern "INIT_START" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Resolution Steps:**
1. Enable provisioned concurrency
2. Optimize Lambda package size
3. Consider keeping connections warm

## Maintenance Procedures

### Daily Health Checks
```bash
#!/bin/bash
# Daily health check script

echo "=== Smart Invoice Pipeline Health Check ==="
echo "Date: $(date)"

# Check Lambda function health
echo "1. Lambda Functions:"
aws lambda get-function --function-name smart-invoice-prod-upload --region us-east-1 --query 'Configuration.State'
aws lambda get-function --function-name smart-invoice-prod-inference --region us-east-1 --query 'Configuration.State'

# Check DynamoDB table status
echo "2. DynamoDB Table:"
aws dynamodb describe-table --table-name smart-invoice-prod-invoices --region us-east-1 --query 'Table.TableStatus'

# Check S3 bucket
echo "3. S3 Bucket:"
aws s3api head-bucket --bucket smart-invoice-prod-invoices --region us-east-1 && echo "OK" || echo "ERROR"

# Check recent processing volume
echo "4. Processing Volume (last 24h):"
aws logs filter-log-events \
  --log-group-name /aws/lambda/smart-invoice-prod-inference \
  --start-time $(date -d '24 hours ago' +%s)000 \
  --filter-pattern "Successfully processed invoice" \
  --region us-east-1 | grep -c "Successfully processed"

echo "=== Health Check Complete ==="
```

### Weekly Maintenance Tasks

1. **Review Cost Reports**
   - Analyze weekly spending trends
   - Identify optimization opportunities
   - Update budget forecasts

2. **Performance Analysis**
   - Review average processing times
   - Analyze error patterns
   - Check extraction accuracy metrics

3. **Security Review**
   - Review CloudTrail logs for unusual activity
   - Check IAM policy compliance
   - Verify encryption settings

4. **Capacity Planning**
   - Monitor DynamoDB usage patterns
   - Review Lambda concurrency limits
   - Plan for traffic growth

### Monthly Tasks

1. **Disaster Recovery Testing**
   - Test backup and restore procedures
   - Verify cross-region replication
   - Update recovery documentation

2. **Security Updates**
   - Update Lambda runtime versions
   - Review and rotate API keys
   - Update security group rules

3. **Cost Optimization Review**
   - Analyze reserved capacity options
   - Review S3 lifecycle policies
   - Optimize Lambda memory settings

## Escalation Procedures

### Level 1: Automated Alerts
- CloudWatch alarms trigger SNS notifications
- PagerDuty integration for critical alerts
- Slack notifications for warnings

### Level 2: On-Call Engineer
- **Response Time**: 15 minutes for critical issues
- **Actions**: Follow runbook procedures
- **Escalation**: If not resolved in 1 hour

### Level 3: Senior Engineer/Architect
- **Response Time**: 30 minutes for escalated issues
- **Actions**: Deep technical investigation
- **Authority**: Make architectural changes

### Level 4: AWS Support
- **When**: Service-wide AWS issues
- **How**: Enterprise support case
- **SLA**: Based on support plan

## Contact Information

### Team Contacts
- **Primary On-Call**: +1-XXX-XXX-XXXX
- **Secondary On-Call**: +1-XXX-XXX-XXXX
- **Team Lead**: daniel@example.com
- **DevOps Team**: devops@example.com

### External Contacts
- **AWS Support**: Enterprise Support Portal
- **Security Team**: security@example.com
- **Business Stakeholders**: business@example.com

## Useful Commands Reference

### CloudWatch Logs
```bash
# Tail logs in real-time
aws logs tail /aws/lambda/smart-invoice-prod-inference --follow

# Search for specific errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/smart-invoice-prod-inference \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000

# Get processing statistics
aws logs filter-log-events \
  --log-group-name /aws/lambda/smart-invoice-prod-inference \
  --filter-pattern "Successfully processed" \
  --start-time $(date -d '24 hours ago' +%s)000 | grep -c "Successfully"
```

### DynamoDB Operations
```bash
# Check table status
aws dynamodb describe-table --table-name smart-invoice-prod-invoices

# Query recent invoices
aws dynamodb scan --table-name smart-invoice-prod-invoices \
  --filter-expression "processed_at > :timestamp" \
  --expression-attribute-values '{":timestamp":{"S":"2024-01-15T00:00:00Z"}}'

# Check table metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=smart-invoice-prod-invoices \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Sum
```

### S3 Operations
```bash
# Check bucket size
aws s3 ls s3://smart-invoice-prod-invoices --recursive --human-readable --summarize

# List recent uploads
aws s3 ls s3://smart-invoice-prod-invoices/ --recursive | tail -20

# Check bucket policy
aws s3api get-bucket-policy --bucket smart-invoice-prod-invoices
```

## Change Management

### Deployment Process
1. **Pre-deployment Checklist**
   - Run all tests in staging
   - Verify infrastructure changes
   - Notify stakeholders

2. **Deployment Steps**
   - Deploy to staging first
   - Run smoke tests
   - Deploy to production
   - Monitor for 30 minutes

3. **Rollback Procedure**
   - Revert Terraform changes
   - Restore previous Lambda versions
   - Verify system health

### Emergency Changes
- **Approval**: CTO or designated authority
- **Documentation**: Post-incident review required
- **Communication**: Immediate stakeholder notification

---

**Last Updated**: January 2024  
**Version**: 1.0  
**Next Review**: February 2024
