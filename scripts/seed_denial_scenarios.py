"""
Seed script to generate 200+ claim denial scenarios for the knowledge base.

Creates a comprehensive JSON dataset covering all major CARC denial codes,
payers, and categories for local development and Pinecone ingestion.

Usage:
    python scripts/seed_denial_scenarios.py
"""

import json
import random
from enum import Enum
from pathlib import Path

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


class DenialCategory(str, Enum):
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
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

PAYERS = [
    "Medicare", "Medicaid", "Blue Cross Blue Shield", "Aetna", "UnitedHealthcare",
    "Cigna", "Humana", "Anthem", "Kaiser Permanente", "Molina Healthcare",
    "Centene", "WellCare", "Tricare", "Workers Compensation", "Commercial Payer",
]

RESOLUTION_TEMPLATES: dict[str, list[str]] = {
    "CO-4": [
        "Review the procedure code and modifier combination on the claim",
        "Verify modifier usage against payer-specific coding guidelines",
        "Check NCCI edits for modifier requirements",
        "Correct the modifier or procedure code as needed",
        "Resubmit with corrected coding and supporting documentation",
    ],
    "CO-16": [
        "Review the denial remark codes for specific missing information",
        "Identify the specific data element missing from the claim",
        "Gather required documentation (medical records, authorization)",
        "Correct the claim with complete information",
        "Resubmit with all required fields populated",
    ],
    "CO-18": [
        "Search for the original claim in the payer system",
        "Verify if the original claim was paid, denied, or pending",
        "If original was denied, resolve the original denial first",
        "If duplicate submission, void the duplicate claim",
        "If resubmission needed, use appropriate claim frequency code",
    ],
    "CO-29": [
        "Verify the payer's timely filing limit (typically 90-365 days)",
        "Calculate days from date of service to original submission",
        "Gather proof of original timely submission if applicable",
        "Prepare timely filing appeal with supporting documentation",
        "Submit appeal within payer's appeal filing deadline",
    ],
    "CO-50": [
        "Review payer's medical policy for the denied service",
        "Obtain supporting clinical documentation from provider",
        "Check if prior authorization was required but not obtained",
        "Prepare medical necessity appeal with clinical evidence",
        "Submit appeal with peer-to-peer review request if available",
    ],
    "CO-197": [
        "Verify authorization requirements for the service/procedure",
        "Search for existing authorization in payer portal",
        "If no authorization exists, request retroactive authorization",
        "Obtain authorization number and effective dates",
        "Resubmit claim with authorization number in appropriate field",
    ],
}

DOCUMENTATION_TEMPLATES: dict[str, list[str]] = {
    "default": ["Claim form", "Medical records", "Provider notes"],
    "authorization": ["Prior authorization letter", "Authorization number confirmation", "Clinical notes"],
    "medical_necessity": ["Physician statement", "Clinical documentation", "Treatment plan", "Lab results"],
    "coding": ["Operative report", "Coding guidelines reference", "NCCI edit documentation"],
    "timely_filing": ["Proof of original submission", "Certified mail receipt", "Fax confirmation"],
}


def generate_scenario(
    scenario_id: int,
    denial_code: str,
    category: DenialCategory,
) -> dict:
    """Generate a single denial scenario dictionary."""
    payer = random.choice(PAYERS)
    code_description = COMMON_DENIAL_CODES.get(denial_code, "Claim adjustment")

    resolution_steps = RESOLUTION_TEMPLATES.get(
        denial_code,
        [
            f"Review denial reason for {denial_code}",
            "Gather supporting documentation",
            "Correct the identified issue",
            "Resubmit or appeal as appropriate",
        ],
    )

    doc_key = "default"
    if category == DenialCategory.AUTHORIZATION:
        doc_key = "authorization"
    elif category == DenialCategory.MEDICAL_NECESSITY:
        doc_key = "medical_necessity"
    elif category == DenialCategory.CODING:
        doc_key = "coding"
    elif category == DenialCategory.TIMELY_FILING:
        doc_key = "timely_filing"

    severity_weights = {
        DenialSeverity.CRITICAL: 0.1,
        DenialSeverity.HIGH: 0.25,
        DenialSeverity.MEDIUM: 0.45,
        DenialSeverity.LOW: 0.2,
    }
    severity = random.choices(
        list(severity_weights.keys()),
        weights=list(severity_weights.values()),
    )[0]

    success_rate = round(random.uniform(65.0, 98.0), 1)

    return {
        "scenario_id": f"SCN-{scenario_id:04d}",
        "denial_code": denial_code,
        "denial_category": category.value,
        "payer_name": payer,
        "denial_description": (
            f"{payer} denied the claim with {denial_code}: {code_description}. "
            f"This denial falls under the {category.value} category and requires "
            f"specific resolution steps to achieve successful resubmission."
        ),
        "resolution_steps": resolution_steps,
        "required_documentation": DOCUMENTATION_TEMPLATES[doc_key],
        "severity": severity.value,
        "average_resolution_days": random.randint(3, 45),
        "success_rate_percent": success_rate,
    }


def generate_all_scenarios() -> list[dict]:
    """Generate 200+ denial scenarios across all categories and codes."""
    scenarios: list[dict] = []
    scenario_id = 1

    category_code_map: dict[DenialCategory, list[str]] = {
        DenialCategory.CODING: ["CO-4", "CO-16"],
        DenialCategory.DUPLICATE: ["CO-18"],
        DenialCategory.COORDINATION_OF_BENEFITS: ["CO-22"],
        DenialCategory.ELIGIBILITY: ["CO-27", "CO-109"],
        DenialCategory.TIMELY_FILING: ["CO-29"],
        DenialCategory.MEDICAL_NECESSITY: ["CO-50", "CO-96", "CO-151"],
        DenialCategory.BILLING: ["CO-97", "CO-119", "CO-204"],
        DenialCategory.AUTHORIZATION: ["CO-197"],
        DenialCategory.OTHER: ["PR-1", "PR-2", "PR-3"],
    }

    for category, codes in category_code_map.items():
        for code in codes:
            for payer_variant in range(8):
                scenarios.append(generate_scenario(scenario_id, code, category))
                scenario_id += 1

    while len(scenarios) < 210:
        code = random.choice(list(COMMON_DENIAL_CODES.keys()))
        category = random.choice(list(DenialCategory))
        scenarios.append(generate_scenario(scenario_id, code, category))
        scenario_id += 1

    return scenarios


def main() -> None:
    """Generate scenarios and write to JSON file."""
    output_path = Path(__file__).parent.parent / "data" / "denial_scenarios.json"
    scenarios = generate_all_scenarios()

    output_data = {
        "metadata": {
            "total_scenarios": len(scenarios),
            "version": "1.0.0",
            "description": "Claims Denial FAQ Knowledge Base",
        },
        "scenarios": scenarios,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"Generated {len(scenarios)} denial scenarios at {output_path}")


if __name__ == "__main__":
    main()
