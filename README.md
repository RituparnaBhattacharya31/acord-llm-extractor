# POC on ACORD Form Extraction Using AWS Lambda

![Python](https://img.shields.io/badge/python-3.12-blue)
![AWS Lambda](https://img.shields.io/badge/aws-lambda-orange)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Serverless](https://img.shields.io/badge/serverless-event--driven-lightgrey)

Event-driven ACORD 140 PDF extraction pipeline using AWS Lambda, Google Gemini, S3, and DynamoDB. Automatically converts ACORD forms into clean, structured JSON using serverless architecture and LLM intelligence.
Full Description
A fully serverless and automated pipeline for extracting structured JSON data from ACORD 140 insurance PDF forms using:
➡️AWS Lambda (Python)
➡️Google Gemini (LLM)
➡️Amazon S3 event triggers
➡️Lambda Layers (for 70MB Gemini dependencies)
➡️DynamoDB storage

This project demonstrates how to combine LLMs with AWS serverless architecture to process incoming PDF documents with zero manual effort. When a new ACORD form is uploaded to an S3 bucket, the system automatically:

➡️Downloads and processes the PDF
➡️Extracts structured fields using Gemini
➡️Validates the extracted data
➡️Stores the parsed JSON in S3
➡️Saves the full extraction record in DynamoDB

This README provides an end-to-end guide on implementing an **ACORD 140
PDF → JSON extraction workflow** using **AWS Lambda, S3, DynamoDB, and
Gemini LLM**.\
It consolidates all steps from local development, packaging, deployment,
and final testing.

------------------------------------------------------------------------

# 1. Creating a Lambda in Python

AWS Lambda supports Python runtimes and is ideal for event-driven PDF
processing.

### Steps

1.  AWS Console → Lambda → Create Function\
2.  Select **Author from scratch**\
3.  Runtime: **Python 3.12**\
4.  Architecture: **x86_64**\
5.  Recommended settings:
    -   Timeout: **30--90 sec**\
    -   Memory: **1024--4096 MB**

------------------------------------------------------------------------

# 2. Testing Lambda Locally

Before deploying, test everything locally.

### Local Project Structure

    acord_lambda_container/
    │
    ├── clients/
    │   ├── base_client.py
    │   ├── gemini_client.py
    │   ├── __init__.py
    │
    ├── extractors/
    │   ├── llm_extractor.py
    │   ├── pdf_extractor.py          # if you kept this, else remove
    │   ├── __init__.py
    │
    ├── models/
    │   ├── accord_schema.py
    │   ├── __init__.py
    │
    ├── utils/
    │   ├── pdf_processor.py
    │   ├── logger.py
    │   ├── __init__.py
    │
    ├── validators/
    │   ├── data_validator.py
    │   ├── __init__.py
    │
    ├── tools/
    │   ├── main.py                   # used for local execution
    │   ├── __init__.py
    │
    ├── output/                       # local output from running Gemini locally
    │   └── *.json
    │
    ├── results/                      # debug/run results (optional)
    │   └── *.json
    │
    ├── .env
    ├── handler.py                    # Lambda entry point
    ├── config.py                     # central config loader
    ├── Dockerfile                    # builds Linux-compatible dependencies
    └── requirements.txt

### Steps to run locally

    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt

Create a `.env` file:

    GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxx
    DDB_TABLE=ACORD140Records
    OUTPUT_BUCKET=acord-json-output
    LOG_LEVEL=INFO
    MODEL_NAME=gemini-3-pro-preview

Run the project:

    python -m main.py

------------------------------------------------------------------------

# 3. Creating S3 Bucket for Incoming ACORD Forms

This bucket stores ACORD PDFs coming from emails or UIs.

### Steps

1.  S3 → Create Bucket\
2.  Example structure:

```{=html}
<!-- -->
```
    attachments/
       ACORD140-form.pdf

------------------------------------------------------------------------

# 4. Creating S3 Bucket for Output JSON

The Lambda writes parsed JSON to this bucket.

Example:

    acord-json-output/
       results/
          acord140-output.json

------------------------------------------------------------------------

# 5. Creating DynamoDB Table

Stores extracted JSON + metadata + validation output.

### Table Name

`ACORD140Records`

### Key Schema

  Column       Type     Notes
  ------------ -------- ---------------
  documentId   String   Partition Key
  createdAt    String   Sort Key

### Additional Attributes

-   s3Key
-   s3Bucket
-   extracted
-   validation

### Example Item

``` json
{
  "documentId": "POL123",
  "s3Key": "attachments/ACORD140.pdf",
  "s3Bucket": "acord-input",
  "extracted": {},
  "validation": {},
  "createdAt": "2025-12-06T20:45:31Z"
}
```

------------------------------------------------------------------------

# 6. Deploying AWS Lambda (Tricky Part)

Gemini Python libraries are **\~70MB** so they cannot be uploaded
directly.\
We use **Lambda Layers** built in **Linux**.

You can do this in two ways:

Option A — Using Docker (Recommended)
    Build dependencies inside a container that matches the Lambda runtime:
    docker build -t acord-layer-builder .
    docker run --rm -v ${PWD}:/output acord-layer-builder
    cd python
    zip -r ../python_libs.zip .


Option B — Using Ubuntu (WSL 2)
    Install dependencies inside Ubuntu to match Lambda’s Linux OS:
    mkdir python
    pip install -r requirements.txt -t python/
    zip -r python_libs.zip python/

------------------------------------------------------------------------

## 6.1 Generating Linux-Compatible Packages

### Steps

1.  Install Ubuntu (WSL2)\
2.  Inside Ubuntu:

```{=html}
<!-- -->
```
    mkdir python
    pip install -r requirements.txt -t python/

Folder output:

    python/
       google/
       pydantic/
       ...

Create zip:

    zip -r python_libs.zip python/

Size \~71 MB.

------------------------------------------------------------------------

## 6.2 Uploading Layer ZIP to S3

Move `python_libs.zip` to Windows → Upload to S3.

------------------------------------------------------------------------

## 6.3 Creating Lambda Layer

1.  Lambda → Layers → Create Layer\
2.  Choose **Upload from S3**\
3.  Runtime: **Python 3.12**\
4.  Architecture: **x86_64**

------------------------------------------------------------------------

## 6.4 Creating the Lambda Function

Zip the Lambda code:

    Compress-Archive -Path .\utils\, .\clients\, .\extractors\, .\models\, .\tools\, .\validators\, .\handler.py, .\config.py -DestinationPath root.zip

Upload to Lambda.

------------------------------------------------------------------------

## 6.5 Environment Variables

    GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxx
    DDB_TABLE=ACORD140Records
    OUTPUT_BUCKET=acord-json-output
    LOG_LEVEL=INFO
    MODEL_NAME=gemini-3-pro-preview

------------------------------------------------------------------------

# 7. Adding Lambda Layer

Lambda → Layers → Add Layer → Custom Layer → Select version.

------------------------------------------------------------------------

# 8. Adding S3 Trigger

Steps: 1. Lambda → Triggers → Add Trigger\
2. Select S3 bucket\
3. Event: **ObjectCreated:Put**\
4. Prefix: `attachments/`

------------------------------------------------------------------------

# 9. IAM Permissions for Lambda

### S3 Read (input bucket)

``` json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject"],
  "Resource": "arn:aws:s3:::input-bucket-name/*"
}
```

### S3 Write (output bucket)

``` json
{
  "Effect": "Allow",
  "Action": ["s3:PutObject"],
  "Resource": "arn:aws:s3:::output-bucket-name/*"
}
```

### DynamoDB Permissions

``` json
{
  "Effect": "Allow",
  "Action": ["dynamodb:PutItem", "dynamodb:UpdateItem"],
  "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/dynamo-db-name"
}
```

------------------------------------------------------------------------

# 10. Testing End-to-End

### Steps

1.  Upload ACORD140 PDF to the input bucket\
2.  Lambda gets triggered\
3.  Output JSON appears in the output bucket\
4.  DynamoDB item is created\
5.  CloudWatch logs show execution details

------------------------------------------------------------------------

# ✔️ Summary

This pipeline enables: - Automated ACORD PDF → JSON extraction\
- LLM-powered parsing\
- Serverless processing\
- End-to-end cloud automation
