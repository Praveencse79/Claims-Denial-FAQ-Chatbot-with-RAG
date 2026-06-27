"""
Application-wide constants for the Claims Denial FAQ Chatbot.

Defines denial codes, category mappings, and system-level constants
used across RAG pipeline, API, and Slack bot modules.
"""

from enum import Enum


class DenialCategory(str, Enum):
    """Enumeration of claim denial category types."""

    ELIGIBILITY = "eligibility"
    AUTHORIZATION = "authorization"
    MEDICAL_NECESSITY = "medical_necessity"
    CODING = "coding"
    BILLING = "billing"
    TIMELY_FILING = "timely_filing"
    DUPLICATE = "duplicate"
    COORDINATION_OF_BENEFITS = "coordination_of_benefits"
    PROVIDER = "provider"
    OTHER = "other"


class DenialSeverity(str, Enum):
    """Severity level indicating urgency of denial resolution."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Common CARC (Claim Adjustment Reason Code) denial codes
COMMON_DENIAL_CODES: dict[str, str] = {
    "CO-4": "Procedure code inconsistent with modifier",
    "CO-16": "Claim/service lacks information or has submission/billing error",
    "CO-18": "Duplicate claim/service",
    "CO-22": "Care may be covered by another payer",
    "CO-27": "Expenses incurred after coverage terminated",
    "CO-29": "Time limit for filing has expired",
    "CO-50": "Non-covered service",
    "CO-96": "Non-covered charge(s)",
    "CO-97": "Payment adjusted because benefit maximum reached",
    "CO-109": "Claim not covered by this payer",
    "CO-119": "Benefit maximum for this time period reached",
    "CO-151": "Payment adjusted because payer deems information insufficient",
    "CO-197": "Precertification/authorization/notification absent",
    "CO-204": "Service/equipment/drug not covered under current benefit plan",
    "PR-1": "Deductible amount",
    "PR-2": "Coinsurance amount",
    "PR-3": "Co-payment amount",
}

# Pinecone metadata field names
PINECONE_METADATA_FIELDS: list[str] = [
    "denial_code",
    "denial_category",
    "scenario_id",
    "payer_name",
    "resolution_steps",
    "severity",
    "source_table",
]

# API response status codes
API_STATUS_SUCCESS = "success"
API_STATUS_ERROR = "error"
API_STATUS_PARTIAL = "partial"

# RAG pipeline identifiers
RAG_SOURCE_PINECONE = "pinecone"
RAG_SOURCE_SNOWFLAKE = "snowflake"
RAG_SOURCE_HYBRID = "hybrid"

# Slack bot command prefixes
SLACK_COMMAND_PREFIX = "/denial"
SLACK_HELP_COMMAND = "/denial-help"

# Document chunk metadata keys
CHUNK_METADATA_SCENARIO_ID = "scenario_id"
CHUNK_METADATA_DENIAL_CODE = "denial_code"
CHUNK_METADATA_CATEGORY = "denial_category"
CHUNK_METADATA_SOURCE = "source"
