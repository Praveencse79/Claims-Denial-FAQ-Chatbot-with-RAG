"""
Prompt templates for the Claims Denial FAQ RAG chatbot.

Defines system prompts, user prompt formatting, and context assembly
templates optimized for Claude's instruction-following capabilities.
"""

CLAIMS_DENIAL_SYSTEM_PROMPT = """You are an expert Claims Denial Resolution Assistant for a healthcare revenue cycle management organization. Your role is to help billing specialists, coders, and claims analysts understand claim denials and provide actionable resolution guidance.

## Your Expertise
- CARC (Claim Adjustment Reason Codes) and RARC (Remittance Advice Remark Codes)
- Medicare, Medicaid, and commercial payer denial patterns
- Medical necessity, authorization, coding, and billing denial resolution
- Claim resubmission workflows and required documentation

## Response Guidelines
1. **Be Specific**: Reference exact denial codes, payer requirements, and documentation needs
2. **Be Actionable**: Provide numbered, step-by-step resolution instructions
3. **Be Accurate**: Only use information from the provided context. If context is insufficient, state what additional information is needed
4. **Be Professional**: Use healthcare revenue cycle terminology appropriately
5. **Include Success Tips**: Mention common pitfalls and tips that improve resubmission success rates

## Response Format
Structure your response as:
- **Denial Summary**: Brief explanation of why the claim was denied
- **Root Cause**: The underlying reason for the denial
- **Resolution Steps**: Numbered actionable steps to resolve
- **Required Documentation**: List of documents needed for resubmission
- **Timeline**: Expected resolution timeframe
- **Success Rate Tip**: One tip to improve resubmission success

## Constraints
- Do NOT fabricate denial codes or payer policies not present in the context
- Do NOT provide legal or medical advice beyond claims processing guidance
- If the query is outside claims denial scope, politely redirect to appropriate resources
"""

CLAIMS_DENIAL_USER_PROMPT_TEMPLATE = """## Retrieved Knowledge Base Context
The following denial scenario information was retrieved from our knowledge base based on semantic similarity to your question:

{context_documents}

## User Question
{user_query}

## Additional Context
- Denial Code (if specified): {denial_code}
- Payer Name (if specified): {payer_name}

Please provide a comprehensive, actionable response based on the retrieved context above. If the context does not fully address the question, clearly indicate what additional information would be needed."""

CONTEXT_DOCUMENT_TEMPLATE = """---
**Scenario ID**: {scenario_id}
**Denial Code**: {denial_code}
**Category**: {denial_category}
**Payer**: {payer_name}
**Description**: {denial_description}
**Resolution Steps**: {resolution_steps}
**Required Documentation**: {required_documentation}
**Severity**: {severity}
**Success Rate**: {success_rate}%
**Relevance Score**: {similarity_score}
---"""

NO_CONTEXT_FALLBACK_PROMPT = """The user asked: "{user_query}"

No relevant denial scenarios were found in the knowledge base matching this query. Please:
1. Acknowledge that no specific scenario was found
2. Provide general guidance based on common denial patterns if applicable
3. Suggest what specific information the user should provide (denial code, payer, service date, etc.)
4. Recommend escalating to a senior claims analyst if the denial is complex"""


def format_context_documents_for_prompt(
    retrieved_documents: list[dict],
) -> str:
    """
    Format retrieved documents into a structured context block for the LLM prompt.

    Args:
        retrieved_documents: List of dicts with document fields and metadata.

    Returns:
        str: Formatted multi-document context string for prompt injection.
    """
    if not retrieved_documents:
        return "No relevant denial scenarios found in the knowledge base."

    formatted_sections = []
    for doc in retrieved_documents:
        metadata = doc.get("metadata", {})
        resolution_steps = metadata.get("resolution_steps", [])
        if isinstance(resolution_steps, list):
            resolution_steps_str = "\n".join(
                f"  {i+1}. {step}" for i, step in enumerate(resolution_steps)
            )
        else:
            resolution_steps_str = str(resolution_steps)

        required_docs = metadata.get("required_documentation", [])
        if isinstance(required_docs, list):
            required_docs_str = ", ".join(required_docs)
        else:
            required_docs_str = str(required_docs)

        section = CONTEXT_DOCUMENT_TEMPLATE.format(
            scenario_id=metadata.get("scenario_id", "N/A"),
            denial_code=metadata.get("denial_code", "N/A"),
            denial_category=metadata.get("denial_category", "N/A"),
            payer_name=metadata.get("payer_name", "N/A"),
            denial_description=doc.get("content", metadata.get("text", "")),
            resolution_steps=resolution_steps_str,
            required_documentation=required_docs_str,
            severity=metadata.get("severity", "medium"),
            success_rate=metadata.get("success_rate_percent", "N/A"),
            similarity_score=f"{doc.get('similarity_score', 0):.2f}",
        )
        formatted_sections.append(section)

    return "\n".join(formatted_sections)


def build_rag_user_prompt(
    user_query: str,
    context_documents: list[dict],
    denial_code: str | None = None,
    payer_name: str | None = None,
) -> str:
    """
    Assemble the complete user prompt with context and query for RAG generation.

    Args:
        user_query: The user's natural language question.
        context_documents: Retrieved documents formatted as dicts.
        denial_code: Optional denial code filter context.
        payer_name: Optional payer name filter context.

    Returns:
        str: Fully formatted user prompt ready for Claude API.
    """
    context_text = format_context_documents_for_prompt(context_documents)

    return CLAIMS_DENIAL_USER_PROMPT_TEMPLATE.format(
        context_documents=context_text,
        user_query=user_query,
        denial_code=denial_code or "Not specified",
        payer_name=payer_name or "Not specified",
    )
