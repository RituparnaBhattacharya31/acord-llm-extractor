import os
import json
import tempfile
import boto3
from datetime import datetime

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
        acord_data: Accord140Data = extractor.extract_from_text(text)
        extracted = acord_data.to_dict()

        validator = DataValidator()
        validation = validator.full_validation(acord_data)

        output_obj = {
            'source': f's3://{bucket}/{key}',
            'extracted': extracted,
            'validation': validation
        }

        # -------------------------------------------------------------------
        # MODIFICATION 1: Store output JSON under results/ folder
        # -------------------------------------------------------------------
        if OUTPUT_BUCKET:
            file_name = key.split('/')[-1].replace('.pdf', '.json')
            out_key = f"results/{file_name}"  # <--- modified path
            s3.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=out_key,
                Body=json.dumps(output_obj, indent=2),
                ContentType='application/json'
            )
            print(f"[INFO] Saved output to s3://{OUTPUT_BUCKET}/{out_key}")

        # Save to DynamoDB
        table = dynamodb.Table(DDB_TABLE)

        document_id = extracted.get('generalInformation', {}).get('policyNumber') or key

        # -------------------------------------------------------------------
        # MODIFICATION 2: Add createdAt field (ISO-8601)
        # -------------------------------------------------------------------
        created_at = datetime.utcnow().isoformat()

        item = {
            'documentId': document_id,
            's3Key': key,
            's3Bucket': bucket,
            'extracted': extracted,
            'validation': validation,
            'createdAt': created_at
        }

        table.put_item(Item=item)
        print(f"[INFO] Saved item to DynamoDB table {DDB_TABLE} with documentId={document_id}")

        return {'status': 'success', 'documentId': document_id}

    except Exception as e:
        print("[ERROR]", e)
        raise
