import json
import os
from typing import List
from datetime import datetime

from models.accord_schema import Accord140Data
from clients.base_client import BaseLLMClient


class LLMExtractor:

    def __init__(self, llm_client: BaseLLMClient):
        self.client = llm_client

    # ----------------------------------------------------------------------
    # Prompt
    # ----------------------------------------------------------------------
    def _build_extraction_prompt(self) -> str:
        return """
You are an expert ACORD 140 form data extraction specialist.
Extract ALL fields from the ACORD 140 Property Section form.
You MUST extract every field even if empty.

IMPORTANT EXTRACTION RULES:
- Extract EXACT values
- Checkboxes → true/false
- Empty → ""
- Dates → MM/DD/YYYY
- Never hallucinate values
- Return ONLY JSON
- Every field shown below MUST be present in the output JSON

RETURN JSON IN THIS EXACT STRUCTURE:

{
  "acordForm": "ACORD 140 (Property)",
  "generalInformation": {
    "date": "",
    "agencyCustomerId": "",
    "agencyName": "",
    "applicant": "",
    "policyNumber": "",
    "carrier": "",
    "naicCode": "",
    "effectiveDate": "",
    "expirationDate": "",
    "directBill": false,
    "agencyBill": false,
    "paymentPlan": "",
    "audit": ""
  },
  "construction": {
    "propertySection": {},
    "constructionRatings": []
  },
  "spoilageCoverage": {},
  "premisesInformation": [],
  "additionalInterests": [],
  "fraudNoticeSection": {}
}
"""

    # ----------------------------------------------------------------------
    # Public extract methods
    # ----------------------------------------------------------------------
    def extract_from_images(self, base64_images: List[str]) -> Accord140Data:
        prompt = self._build_extraction_prompt()
        extracted_text = self.client.extract_from_images(base64_images, prompt)
        print(f"DEBUG: Raw LLM Response:\n{extracted_text}\n")

        extracted_data = self._parse_response(extracted_text)
        self._save_to_file(extracted_data)
        return extracted_data

    def extract_from_text(self, text: str) -> Accord140Data:
        prompt = self._build_extraction_prompt()
        extracted_text = self.client.extract_from_text(text, prompt)
        print(f"DEBUG: Raw LLM Response:\n{extracted_text}\n")

        extracted_data = self._parse_response(extracted_text)
        self._save_to_file(extracted_data)
        return extracted_data

    # ----------------------------------------------------------------------
    # Normalization Layer (MOST IMPORTANT FIXES ARE HERE)
    # ----------------------------------------------------------------------
    def _normalize_response(self, data: dict) -> dict:
        """Normalize and fill missing values so Pydantic never fails."""

        # Ensure top-level keys always exist
        data.setdefault("generalInformation", {})
        data.setdefault("construction", {})
        data.setdefault("spoilageCoverage", {})
        data.setdefault("premisesInformation", [])
        data.setdefault("additionalInterests", [])
        data.setdefault("fraudNoticeSection", {})

        # ------------------------------------------------------------------
        # GENERAL INFORMATION
        # ------------------------------------------------------------------
        gen = data["generalInformation"]

        general_defaults = {
            "date": "",
            "agencyCustomerId": "",
            "agencyName": "",
            "applicant": "",
            "policyNumber": "",
            "carrier": "",
            "naicCode": "",
            "effectiveDate": "",
            "expirationDate": "",
            "directBill": False,
            "agencyBill": False,
            "paymentPlan": "",
            "audit": ""
        }
        for k, v in general_defaults.items():
            gen.setdefault(k, v)

        # Normalize booleans coming as “yes”, “checked”, “true”
        for bf in ["directBill", "agencyBill"]:
            if isinstance(gen[bf], str):
                gen[bf] = gen[bf].lower() in ("true", "yes", "checked", "1")

        # Normalize audit field
        if isinstance(gen["audit"], bool):
            gen["audit"] = "yes" if gen["audit"] else "no"

        # ------------------------------------------------------------------
        # CONSTRUCTION SECTION
        # ------------------------------------------------------------------
        construction = data["construction"]
        construction.setdefault("propertySection", {})
        construction.setdefault("constructionRatings", [])

        # ---- Property Section ----
        prop = construction["propertySection"]

        prop_defaults = {
            "propertySectionDate": "",
            "clockHourly": False,
            "guardsWatchmenCount": "",
            "wiringYear": "",
            "roofingYear": "",
            "plumbingYear": "",
            "heatingYear": "",
            "sprinklerPercent": "",
            "heatingBoilerOnPremises": False,
            "insurancePlacedElsewhereIfBoiler": "",
            "premisesFireProtection": "",
            "burglarAlarm": {},
            "fireAlarm": {}
        }
        for k, v in prop_defaults.items():
            prop.setdefault(k, v)

        # Burglar Alarm
        ba = prop["burglarAlarm"]
        ba_defaults = {
            "installedAndServicedBy": "",
            "withKeys": False,
            "centralStation": False,
            "grade": "",
            "extent": "",
            "expirationDate": "",
            "certificateNumber": "",
            "type": ""
        }
        for k, v in ba_defaults.items():
            ba.setdefault(k, v)

        # Fire alarm
        fa = prop["fireAlarm"]
        fa_defaults = {
            "manufacturer": "",
            "centralStation": False,
            "localGong": False
        }
        for k, v in fa_defaults.items():
            fa.setdefault(k, v)

        # ---- Construction Ratings ----
        for cr in construction["constructionRatings"]:

            # building improvements
            cr.setdefault("buildingImprovements", {})
            bi = cr["buildingImprovements"]
            bi_defaults = {
                "wiring": False,
                "wiringYear": "",
                "roofing": False,
                "roofingYear": "",
                "plumbing": False,
                "plumbingYear": "",
                "heating": False,
                "heatingYear": "",
                "otherImprovements": False,
                "otherImprovementsDescription": "",
                "otherImprovementsYear": ""
            }
            for k, v in bi_defaults.items():
                bi.setdefault(k, v)

            # exposures
            cr.setdefault("exposures", {})
            exp = cr["exposures"]
            exp_defaults = {
                "rightExposureAndDistance": "",
                "leftExposureAndDistance": "",
                "frontExposureAndDistance": "",
                "rearExposureAndDistance": ""
            }
            for k, v in exp_defaults.items():
                exp.setdefault(k, v)

            # premisesConstructionDetails
            cr.setdefault("premisesConstructionDetails", {})
            pcd = cr["premisesConstructionDetails"]
            pcd_defaults = {
                "windClass": "",
                "resistive": False,
                "semiResistive": False,
                "buildingCode": "",
                "grade": "",
                "taxCode": "",
                "roofType": "",
                "otherOccupancies": "",
                "totalArea": "",
                "yearBuilt": "",
                "basementsCount": "",
                "storiesCount": "",
                "protectionClass": "",
                "fireDistrictCodeNumber": "",
                "milesToFireStation": "",
                "hydrantDistanceFeet": "",
                "constructionType": "",
                "fireStation": "",
                "hydrantDistanceTo": "",
                "blanket": "",
                "guardPercent": "",
                "inflation": "",
                "causesOfLoss": "",
                "coinsPercent": "",
                "additionalInformation": "",
                "frontExposureAndDistance": "",
                "rearExposureAndDistance": "",
                "leftExposureAndDistance": "",
                "rightExposureAndDistance": "",
                "premisesFireProtection": "",
                "heatingBoilerOnPremises": "",
                "insurancePlacedElsewhereIfBoiler": ""
            }
            for k, v in pcd_defaults.items():
                pcd.setdefault(k, v)

        return data

    # ----------------------------------------------------------------------
    # Parse Response
    # ----------------------------------------------------------------------
    def _parse_response(self, response_text: str) -> Accord140Data:
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in LLM response")

        json_str = response_text[json_start:json_end]
        data_dict = json.loads(json_str)

        normalized_dict = self._normalize_response(data_dict)

        return Accord140Data(**normalized_dict)

    # ----------------------------------------------------------------------
    # Save to file
    # ----------------------------------------------------------------------
    def _save_to_file(self, data: Accord140Data):
        output_dir = "/tmp/results"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/acord140_output_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data.to_dict(), f, indent=2)
        print(f"JSON saved to: {filename}")

    # ----------------------------------------------------------------------
    # Retry wrapper
    # ----------------------------------------------------------------------
    def extract_with_validation(
        self, base64_images: List[str], retry_count: int = 2
    ) -> Accord140Data:

        for attempt in range(retry_count):
            try:
                return self.extract_from_images(base64_images)
            except Exception as e:
                if attempt == retry_count - 1:
                    raise Exception(
                        f"Extraction failed after {retry_count} attempts: {str(e)}"
                    )

        raise Exception("Unexpected extraction failure")
