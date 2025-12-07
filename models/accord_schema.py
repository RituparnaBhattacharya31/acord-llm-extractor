from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# -------------------------
# General Information Model
# -------------------------
class GeneralInformation(BaseModel):
    date: Optional[str] = ""
    agencyCustomerId: Optional[str] = ""
    agencyName: Optional[str] = ""
    applicant: Optional[str] = ""
    policyNumber: Optional[str] = ""
    carrier: Optional[str] = ""
    naicCode: Optional[str] = ""
    effectiveDate: Optional[str] = ""
    expirationDate: Optional[str] = ""
    directBill: Optional[bool] = False
    agencyBill: Optional[bool] = False
    paymentPlan: Optional[str] = ""
    audit: Optional[str] = ""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow"
    )

    @field_validator("date", "effectiveDate", "expirationDate")
    def validate_date_format(cls, v):
        if not v:
            return v
        try:
            datetime.strptime(v, "%m/%d/%Y")
        except ValueError:
            pass
        return v


# -------------------------
# Spoilage Coverage Model
# -------------------------
class SpoilageCoverage(BaseModel):
    spoilageCoverageYN: Optional[bool] = None
    limit: Optional[Any] = None
    deductible: Optional[Any] = None
    options: Optional[str] = ""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow"
    )


# -------------------------
# Main ACORD 140 Schema
# -------------------------
class Accord140Data(BaseModel):
    acordForm: str = "ACORD 140 (Property)"
    generalInformation: GeneralInformation = Field(alias="generalInformation")

    construction: Dict[str, Any] = Field(default_factory=dict)
    premisesInformation: List[Dict[str, Any]] = Field(default_factory=list)
    additionalInterests: List[Dict[str, Any]] = Field(default_factory=list)
    fraudNoticeSection: Dict[str, Any] = Field(default_factory=dict)

    # Updated: Spoilage is normally a list — accept dict OR list
    spoilageCoverage: Optional[List[SpoilageCoverage]] = Field(
        default_factory=list,
        alias="spoilageCoverage"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow"
    )

    # Auto-normalize spoilageCoverage if backend sends list/dict incorrectly
    @field_validator("spoilageCoverage", mode="before")
    def normalize_spoilage(cls, v):
        if isinstance(v, dict):
            return [v]
        if isinstance(v, list):
            return v
        return []

    # Clean empty string → None in construction
    @field_validator("construction", mode="before")
    def clean_construction(cls, v):
        if isinstance(v, dict):
            return {k: (val if val not in ("", None) else None) for k, val in v.items()}
        return v

    # Same for fraud notice
    @field_validator("fraudNoticeSection", mode="before")
    def clean_fraud_notice(cls, v):
        if isinstance(v, dict):
            return {k: (val if val not in ("", None) else None) for k, val in v.items()}
        return v

    def to_dict(self):
        return self.model_dump(by_alias=True)
