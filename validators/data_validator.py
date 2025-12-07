from typing import Dict, List, Tuple, Any
from datetime import datetime
from models.accord_schema import Accord140Data


class DataValidator:
    """
    Production-grade validator for ACORD 140 structured data.
    Splits issues into:
    - Errors   → strict failures
    - Warnings → suspicious or incomplete but acceptable data
    """

    @staticmethod
    def validate_date(date_str: str, field_name: str) -> Tuple[bool, str]:
        if not date_str or str(date_str).strip() == "":
            return False, f"{field_name} is empty"

        formats = ["%m/%d/%Y", "%m/%d/%y"]

        for fmt in formats:
            try:
                datetime.strptime(date_str, fmt)
                return True, ""
            except ValueError:
                continue

        return False, f"{field_name} has invalid date format: {date_str}"

    @staticmethod
    def validate_required_fields(data: Accord140Data) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        gi = data.generalInformation

        required_fields = {
            "agencyCustomerId": gi.agencyCustomerId,
            "agencyName": gi.agencyName,
            "applicant": gi.applicant,
            "policyNumber": gi.policyNumber,
            "carrier": gi.carrier,
            "naicCode": gi.naicCode,
            "effectiveDate": gi.effectiveDate,
            "expirationDate": gi.expirationDate,
            "paymentPlan": gi.paymentPlan,
            "audit": gi.audit,
        }

        for field, value in required_fields.items():
            if value is None or str(value).strip() == "":
                errors.append(f"Required field '{field}' is missing")

        # Validate dates
        for field in ("effectiveDate", "expirationDate"):
            valid, err = DataValidator.validate_date(getattr(gi, field), field)
            if not valid:
                errors.append(err)

        return len(errors) == 0, errors

    @staticmethod
    def validate_data_consistency(data: Accord140Data) -> Tuple[bool, List[str]]:
        warnings: List[str] = []
        gi = data.generalInformation

        if gi.directBill and gi.agencyBill:
            warnings.append("Both directBill and agencyBill are selected – only one is expected.")

        if not gi.directBill and not gi.agencyBill:
            warnings.append("Neither directBill nor agencyBill is selected – one should be selected.")

        try:
            eff = datetime.strptime(gi.effectiveDate, "%m/%d/%Y")
            exp = datetime.strptime(gi.expirationDate, "%m/%d/%Y")
            if exp <= eff:
                warnings.append("expirationDate should be after effectiveDate.")
        except Exception:
            pass

        if gi.naicCode and not str(gi.naicCode).isdigit():
            warnings.append(f"naicCode '{gi.naicCode}' is not numeric.")

        if gi.policyNumber and len(str(gi.policyNumber)) < 4:
            warnings.append("policyNumber appears too short.")

        for idx, spoil in enumerate(data.spoilageCoverage or []):
            if spoil.spoilageCoverageYN not in (True, False, None):
                warnings.append(f"Spoilage coverage entry {idx} has invalid Y/N flag.")

        return len(warnings) == 0, warnings

    @staticmethod
    def validate_construction(data: Accord140Data) -> Tuple[bool, List[str]]:
        warnings = []

        construction = data.construction or {}
        if not construction.get("propertySection"):
            warnings.append("construction.propertySection is empty.")

        for cr_idx, cr in enumerate(construction.get("constructionRatings", [])):
            bi = cr.get("buildingImprovements", {})
            if bi.get("wiring") and not bi.get("wiringYear"):
                warnings.append(f"constructionRatings[{cr_idx}]: wiringYear missing despite wiring=True")

        return len(warnings) == 0, warnings

    @staticmethod
    def full_validation(data: Accord140Data) -> Dict[str, Any]:
        errors_all: List[str] = []
        warnings_all: List[str] = []

        is_req_ok, req_errors = DataValidator.validate_required_fields(data)
        errors_all.extend(req_errors)

        is_consistent, consistency_warnings = DataValidator.validate_data_consistency(data)
        warnings_all.extend(consistency_warnings)

        _, construction_warnings = DataValidator.validate_construction(data)
        warnings_all.extend(construction_warnings)

        if errors_all:
            status = "FAIL"
        elif warnings_all:
            status = "PASS_WITH_WARNINGS"
        else:
            status = "PASS"

        return {
            "valid": len(errors_all) == 0,
            "errors": errors_all,
            "warnings": warnings_all,
            "overall_status": status,
        }
