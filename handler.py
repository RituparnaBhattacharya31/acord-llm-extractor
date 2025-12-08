import os
import json
import tempfile
import boto3
from datetime import datetime
from decimal import Decimal

from extractors.llm_extractor import LLMExtractor
from clients.gemini_client import GeminiClient
from validators.data_validator import DataValidator
from models.accord_schema import Accord140Data
from utils.pdf_processor import PDFProcessor

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

DDB_TABLE = os.environ.get('DDB_TABLE', 'ACORD140Records')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('MODEL_NAME', 'gemini-2.5-pro')

# ---------------------------------------------------------------------------
# Retry wrapper that handles 429 Quota Exceeded with a meaningful response
# ---------------------------------------------------------------------------
def with_quota_retries(func, max_retries=3, backoff=2):
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                msg = str(e)

                if "429" in msg or "quota" in msg.lower():
                    # Quota exceeded
                    if attempt < max_retries - 1:
                        time.sleep(backoff * (attempt + 1))
                    else:
                        # Final failure → return clean response
                        return {
                            "error": True,
                            "type": "QUOTA_EXCEEDED",
                            "message": "Gemini quota exceeded. Please try again later or upgrade your API plan.",
                            "details": msg
                        }
                else:
                    raise
    return wrapper

# ----------------------------------------------------------------------
# FIX: Convert all floats → Decimal (works recursively)
# ----------------------------------------------------------------------
def convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats(v) for v in obj]
    else:
        return obj


def lambda_handler(event, context):
    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        print(f"[INFO] Processing s3://{bucket}/{key}")

        tmp_dir = tempfile.gettempdir()
        local_path = os.path.join(tmp_dir, key.split('/')[-1])
        s3.download_file(bucket, key, local_path)

        pdf_processor = PDFProcessor()
        text = pdf_processor.extract_text(local_path)
        print(f"[INFO] Extracted text length: {len(text)}")

        llm_client = GeminiClient(api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
        extractor = LLMExtractor(llm_client)
        # -------------------------------------------------------------------
        # Run extraction with quota-safe wrapper
        # -------------------------------------------------------------------
        response = with_quota_retries(extractor.extract_from_text)(text)

        # Handle quota exceeded response
        if isinstance(response, dict) and response.get("type") == "QUOTA_EXCEEDED":
            print("[ERROR] Gemini quota exceeded")
            return response

        # Normal flow continues:

        acord_data: Accord140Data = response
        extracted = acord_data.to_dict()

        # Validate data

        validator = DataValidator()
        validation = validator.full_validation(acord_data)

        output_obj = {
            'source': f's3://{bucket}/{key}',
            'extracted': extracted,
            'validation': validation
        }

        # -------------------------------------------------------------
        # Save output JSON to S3 under results/
        # -------------------------------------------------------------
        if OUTPUT_BUCKET:
            file_name = key.split('/')[-1].replace('.pdf', '.json')
            out_key = f"results/{file_name}"
            s3.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=out_key,
                Body=json.dumps(output_obj, indent=2),
                ContentType='application/json'
            )
            print(f"[INFO] Saved output to s3://{OUTPUT_BUCKET}/{out_key}")

        # -------------------------------------------------------------
        # Save to DynamoDB
        # -------------------------------------------------------------
        table = dynamodb.Table(DDB_TABLE)

        document_id = extracted.get('generalInformation', {}).get('policyNumber') or key
        created_at = datetime.utcnow().isoformat()

        item = {
            'documentId': document_id,
            's3Key': key,
            's3Bucket': bucket,
            'extracted': extracted,
            'validation': validation,
            'createdAt': created_at,
            'isReviewed': False
        }

        item = convert_floats(item)

        table.put_item(Item=item)
        print(f"[INFO] Saved item to DynamoDB table {DDB_TABLE} with documentId={document_id}")

        return {'status': 'success', 'documentId': document_id, 'isReviewed': False}

    except Exception as e:
        print("[ERROR]", e)
        raise
