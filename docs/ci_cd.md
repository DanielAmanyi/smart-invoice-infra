# CI/CD Pipeline Best Practices

## Recommended Workflow
- Use GitHub Actions for automated testing and deployment.
- Store secrets in GitHub or AWS Secrets Manager.
- Example workflow:

```yaml
name: Deploy Smart Invoice Infra
on:
  push:
    branches: [ main ]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r lambda/inference_handler/requirements.txt
          pip install -r lambda/upload_handler/requirements.txt
          pip install pytest
      - name: Run tests
        run: |
          pytest lambda/inference_handler/test_handler.py
          pytest lambda/upload_handler/test_handler.py
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Terraform Init & Apply
        run: |
          cd smart-invoice-infra/terraform
          terraform init
          terraform apply -auto-approve
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```
