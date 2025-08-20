# Smart Invoice AI Pipeline – Cloud-Native ML Infrastructure

This project is a **production-ready** cloud-native template for document AI processing, featuring real invoice uploads, OCR extraction using **AWS Textract**, and intelligent field extraction using **Amazon Bedrock AI** - all built on serverless infrastructure using AWS and Terraform.

The system implements a complete ML production pipeline where raw invoice files are uploaded, processed with real AI/ML services, and structured data is persisted into a NoSQL store. The design is optimized for scale, cost-efficiency, and modularity with **pay-per-use pricing**.

>  This project demonstrates real-world AI/ML patterns using AWS serverless services, created for educational, research, and demonstration purposes.

---

## Workflow Overview

1. **Invoice Upload**  
   Users upload invoices to an S3 bucket via a REST API (API Gateway → Lambda).

2. **Trigger Inference**  
   S3 triggers a second Lambda function when a new object is created.

3. **OCR + AI Inference**  
   This Lambda uses **AWS Textract** for OCR extraction and **Amazon Bedrock (Claude)** for intelligent field extraction (vendor, amount, date, etc.).

4. **Persistence**  
   Results are written into a DynamoDB table for storage and further downstream use.

---

## Infrastructure Stack (IaC)

All resources are deployed via [Terraform](https://www.terraform.io/), organized into reusable modules:

| Component         | Tech Used              | Description                                      |
|------------------|------------------------|--------------------------------------------------|
| Compute          | AWS Lambda             | Two functions: upload handler & inference logic |
| Storage          | Amazon S3              | Invoice file uploads                             |
| Inference Output | DynamoDB               | Stores extracted fields (vendor, amount, etc)    |
| Triggering       | S3 → Lambda            | Event-based invocation of inference              |
| API Access       | API Gateway (REST)     | Exposes upload endpoint                          |
| Packaging        | Python + Bash          | Bundled using a `zip_deploy.sh` script           |

---

## Project Structure

smart-invoice-infra/
├── terraform/
│ ├── main.tf, backend.tf, variables.tf, outputs.tf
│ └── modules/
│ ├── s3_invoice_bucket/
│ ├── dynamodb/
│ ├── iam/
│ ├── api_gateway/
│ ├── lambda_upload/
│ └── lambda_infer/
├── lambda/
│ ├── upload_handler/
│ │ ├── handler.py
│ │ └── requirements.txt
│ └── inference_handler/
│ ├── handler.py
│ ├── ocr_extract.py
│ ├── model_helpers.py
│ └── requirements.txt
├── zip_deploy.sh
└── README.md


---

## AI/ML Context

This project implements **real AI/ML services** for production-grade document processing:

### AWS Textract (OCR)
- Document text detection and extraction
- Form data extraction (key-value pairs)
- Table detection and structured data extraction
- Confidence scoring for quality assessment

### Amazon Bedrock (AI Inference)
- Claude 3 Haiku for intelligent field extraction
- Vendor name identification
- Amount and currency detection
- Date parsing and normalization
- Invoice number extraction

### Hybrid Extraction Strategy
- **Rule-based extraction**: Fast, reliable for common patterns
- **AI enhancement**: Handles complex/unusual invoice formats
- **Result validation**: Intelligent merging and confidence scoring

### Cost Structure (Pay-per-use)
- **Textract**: ~$0.0015 per page
- **Bedrock**: ~$0.0005 per invoice
- **Total processing cost**: ~$0.002 per invoice

### Extracted Data Structure
```json
{
  "vendor": "ACME Corporation Inc.",
  "amount": 2170.00,
  "date": "2024-03-15",
  "invoice_number": "INV-2024-001",
  "tax_amount": 170.00,
  "currency": "USD",
  "line_items": [...],
  "confidence": "high",
  "extraction_method": "hybrid_ai_rules"
}
```

---

## Deploying (Optional)

To deploy this project:

```bash
# 1. Configure Terraform backend (see backend.tf)
terraform init

# 2. Package your Lambda functions
./zip_deploy.sh

# 3. Deploy everything
terraform apply
```

**Prerequisites:**
- AWS CLI configured with appropriate permissions
- Access to AWS Textract and Amazon Bedrock services
- Bedrock model access enabled (Claude 3 Haiku)

You must set your AWS credentials beforehand using environment variables or ~/.aws/credentials.

**Note**: This deployment creates real AWS resources with usage-based costs. See `DEPLOYMENT_GUIDE.md` for detailed instructions and cost estimates.

 Author

Daniel Amanyi
Cloud/DevOps Engineer • AI Infrastructure Enthusiast
linkedin.com/in/amanyid

License

MIT License – for educational and personal use.
