import os
import json
from pathlib import Path
from typing import Union, Dict, Any
from dotenv import load_dotenv

from utils.pdf_processor import PDFProcessor
from extractors.llm_extractor import LLMExtractor
from validators.data_validator import DataValidator
from config import create_llm_client


class Accord140Extractor:

    def __init__(self):
        load_dotenv()  # Ensure env loaded for create_llm_client
        self.pdf_processor = PDFProcessor()
        llm_client = create_llm_client()
        self.llm_extractor = LLMExtractor(llm_client=llm_client)
        self.validator = DataValidator()

    def extract_from_pdf(
        self,
        pdf_path: Union[str, Path],
        validate: bool = True
    ) -> Dict[str, Any]:

        print(f"Processing PDF: {pdf_path}")

        # Text Extraction
        print("Extracting text from PDF...")
        text_content = self.pdf_processor.extract_text(pdf_path)
        print(f"Extracted {len(text_content)} characters of text")

        # Debug: Print first 500 chars
        print(f"DEBUG: First 500 chars:\n{text_content[:500]}\n...")

        # Heuristic: if text is small or missing obvious labels, use vision
        use_vision = False
        MIN_TEXT_LEN = 300  # tune as needed
        required_labels = ["ACORD", "Applicant", "Policy", "Carrier", "Agency"]
        if not text_content or len(text_content.strip()) < MIN_TEXT_LEN:
            print("Text extraction appears insufficient → switching to vision-based extraction.")
            use_vision = True
        else:
            text_lower = text_content.lower()
            label_found = any(lbl.lower() in text_lower for lbl in required_labels)
            if not label_found:
                print("Important labels not found in text layer → switching to vision-based extraction.")
                use_vision = True

        if use_vision:
            print("Converting PDF pages to base64 images for vision extraction...")
            base64_images = self.pdf_processor.pdf_to_base64_images(pdf_path)
            print(f"Converted {len(base64_images)} pages to images")
            extracted_data = self.llm_extractor.extract_with_validation(base64_images)
        else:
            print("Extracting data using LLM (text mode)...")
            extracted_data = self.llm_extractor.extract_from_text(text_content)

        print("Extraction complete")

        validation_result = None
        if validate:
            print("Validating extracted data...")
            validation_result = self.validator.full_validation(extracted_data)
            print(f"Validation status: {validation_result['overall_status']}")

            if validation_result['errors']:
                print(f"Errors found: {len(validation_result['errors'])}")
                for error in validation_result['errors']:
                    print(f"  - {error}")

            if validation_result['warnings']:
                print(f"Warnings found: {len(validation_result['warnings'])}")
                for warning in validation_result['warnings']:
                    print(f"  - {warning}")

        return {
            "extracted_data": extracted_data.to_dict(),
            "validation": validation_result,
            "success": validation_result['valid'] if validation_result else True
        }

    def extract_from_image(
        self,
        image_path: Union[str, Path],
        validate: bool = True
    ) -> Dict[str, Any]:

        print(f"Processing Image: {image_path}")
        base64_image = self.pdf_processor.load_image_as_base64(image_path)

        print("Extracting data using LLM...")
        extracted_data = self.llm_extractor.extract_with_validation([base64_image])
        print("Extraction complete")

        validation_result = None
        if validate:
            print("Validating extracted data...")
            validation_result = self.validator.full_validation(extracted_data)
            print(f"Validation status: {validation_result['overall_status']}")

        return {
            "extracted_data": extracted_data.to_dict(),
            "validation": validation_result,
            "success": validation_result['valid'] if validation_result else True
        }


def main():
    load_dotenv()

    try:
        extractor = Accord140Extractor()
    except ValueError as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return

    pdf_path = "140-Property-Acord.pdf"

    if not Path(pdf_path).exists():
        print(json.dumps({"error": f"File not found: {pdf_path}"}, indent=2))
        return

    try:
        result = extractor.extract_from_pdf(pdf_path, validate=True)
        output_json = json.dumps(result, indent=2)
        print(output_json)

        # Create output directory
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save with timestamp
        filename = output_dir / f"extraction_result_{Path(pdf_path).stem}.json"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(output_json)

        print(f"\nSaved result to {filename}")

    except Exception as e:
        error_output = json.dumps({"error": str(e)}, indent=2)
        print(error_output)

        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "error.json", "w", encoding="utf-8") as f:
            f.write(error_output)


if __name__ == "__main__":
    main()
