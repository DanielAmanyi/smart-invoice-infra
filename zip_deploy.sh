#!/bin/bash

set -e

# Paths
HANDLERS=("upload_handler" "inference_handler")
BASE_DIR="lambda"

echo "🛠️  Zipping Lambda functions..."

for handler in "${HANDLERS[@]}"; do
  LAMBDA_DIR="${BASE_DIR}/${handler}"
  ZIP_FILE="${LAMBDA_DIR}/lambda.zip"

  echo "📦  Packaging ${handler}..."
  cd "$LAMBDA_DIR"
  rm -f lambda.zip

  # Include ALL .py files (handler + local helpers)
  zip -r lambda.zip *.py > /dev/null

  # Optional: include dependencies if requirements.txt exists
  if [ -f "requirements.txt" ]; then
    echo "📦  Installing dependencies for ${handler}..."
    pip install -r requirements.txt -t ./package > /dev/null
    cd package
    zip -r ../lambda.zip . > /dev/null
    cd ..
    rm -rf package
  fi

  cd - > /dev/null
done

echo "✅ Done. Lambda packages ready."
