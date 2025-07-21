# Smart Invoice AI Pipeline – Cloud-Native ML Infrastructure

This project is a cloud-native template for document AI processing, specifically invoice uploads, OCR extraction, and structured inference built entirely on serverless infrastructure using AWS and Terraform.

It simulates an ML production pipeline where raw invoice files are uploaded, processed for text and metadata, and persisted into a NoSQL store with the design optimized for scale, cost-efficiency, and modularity.

>  While inspired by real-world patterns, this project is fully independent and created for educational, research, and demonstration purposes.

---

## Workflow Overview

1. **Invoice Upload**  
   Users upload invoices to an S3 bucket via a REST API (API Gateway → Lambda).

2. **Trigger Inference**  
   S3 triggers a second Lambda function when a new object is created.

3. **OCR + ML Simulation**  
   This Lambda performs basic OCR and simulates inference logic (e.g., vendor detection, amount parsing).

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

While this demo uses mocked ML logic, it mirrors typical cloud AI pipelines:

- OCR + Metadata Extraction (Tesseract, Textract, or fine-tuned models)
- Serverless batch inference
- Scalable Lambda-based inference orchestration
- Ideal for extensions like SageMaker, Bedrock, or HuggingFace endpoints

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
You must set your AWS credentials beforehand using environment variables or ~/.aws/credentials.

 Author

Daniel Amanyi
Cloud/DevOps Engineer • AI Infrastructure Enthusiast
linkedin.com/in/amanyid

License

MIT License – for educational and personal use.
