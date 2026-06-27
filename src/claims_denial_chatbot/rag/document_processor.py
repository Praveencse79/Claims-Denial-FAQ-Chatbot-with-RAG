"""
Document processing for denial scenario ingestion pipeline.

Chunks denial scenario text, enriches metadata, and prepares
vectors for Pinecone upsert during knowledge base ingestion.
"""

from typing import Any

from langchain.text_splitter import RecursiveCharacterTextSplitter

from claims_denial_chatbot.config import get_application_settings
from claims_denial_chatbot.core.logging import get_logger
from claims_denial_chatbot.models.schemas import DenialScenario

logger = get_logger(__name__)


class DenialScenarioDocumentProcessor:
    """
    Processes DenialScenario records into embeddable document chunks.

    Splits long denial descriptions into overlapping chunks while
    preserving metadata for filtered retrieval.
    """

    def __init__(self) -> None:
        """Initialize text splitter with RAG chunk configuration."""
        settings = get_application_settings()
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

    def build_document_text_from_scenario(self, scenario: DenialScenario) -> str:
        """
        Compose a rich text document from a DenialScenario for embedding.

        Combines denial code, description, resolution steps, and documentation
        into a single searchable text block.

        Args:
            scenario: DenialScenario model instance.

        Returns:
            str: Concatenated text suitable for embedding and chunking.
        """
        resolution_text = "\n".join(
            f"Step {i+1}: {step}" for i, step in enumerate(scenario.resolution_steps)
        )
        docs_text = ", ".join(scenario.required_documentation)

        return (
            f"Denial Code: {scenario.denial_code}\n"
            f"Category: {scenario.denial_category}\n"
            f"Payer: {scenario.payer_name}\n"
            f"Description: {scenario.denial_description}\n"
            f"Resolution Steps:\n{resolution_text}\n"
            f"Required Documentation: {docs_text}\n"
            f"Severity: {scenario.severity}\n"
            f"Success Rate: {scenario.success_rate_percent}%"
        )

    def chunk_scenario_into_documents(
        self, scenario: DenialScenario
    ) -> list[dict[str, Any]]:
        """
        Split a denial scenario into chunks with attached metadata.

        Args:
            scenario: Source denial scenario to process.

        Returns:
            list[dict]: Chunk dicts with 'text' and 'metadata' keys.
        """
        full_text = self.build_document_text_from_scenario(scenario)
        text_chunks = self._text_splitter.split_text(full_text)

        base_metadata = {
            "scenario_id": scenario.scenario_id,
            "denial_code": scenario.denial_code,
            "denial_category": str(scenario.denial_category),
            "payer_name": scenario.payer_name,
            "severity": str(scenario.severity),
            "success_rate_percent": scenario.success_rate_percent,
            "resolution_steps": scenario.resolution_steps,
            "required_documentation": scenario.required_documentation,
            "source": "snowflake",
        }

        chunks = []
        for chunk_index, chunk_text in enumerate(text_chunks):
            chunk_metadata = {
                **base_metadata,
                "chunk_index": chunk_index,
                "total_chunks": len(text_chunks),
                "text": chunk_text,
            }
            chunks.append({"text": chunk_text, "metadata": chunk_metadata})

        logger.debug(
            "scenario_chunked",
            scenario_id=scenario.scenario_id,
            chunk_count=len(chunks),
        )
        return chunks

    def process_scenarios_batch(
        self, scenarios: list[DenialScenario]
    ) -> list[dict[str, Any]]:
        """
        Process multiple denial scenarios into a flat list of document chunks.

        Args:
            scenarios: List of DenialScenario records to process.

        Returns:
            list[dict]: All chunks from all scenarios, ready for embedding.
        """
        all_chunks: list[dict[str, Any]] = []
        for scenario in scenarios:
            chunks = self.chunk_scenario_into_documents(scenario)
            all_chunks.extend(chunks)

        logger.info(
            "batch_scenarios_processed",
            scenario_count=len(scenarios),
            total_chunks=len(all_chunks),
        )
        return all_chunks
