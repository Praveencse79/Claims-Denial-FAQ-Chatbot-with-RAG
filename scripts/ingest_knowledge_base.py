"""
Knowledge base ingestion script.

Loads denial scenarios from Snowflake or local JSON and upserts
embedded vectors into Pinecone.

Usage:
    python scripts/ingest_knowledge_base.py --source snowflake
    python scripts/ingest_knowledge_base.py --source json --file data/denial_scenarios.json
    python scripts/ingest_knowledge_base.py --source snowflake --force-reindex
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claims_denial_chatbot.core.logging import configure_structured_logging, get_logger
from claims_denial_chatbot.models.schemas import DenialScenario, IngestionRequest
from claims_denial_chatbot.services import ClaimsDenialChatbotService

logger = get_logger(__name__)


def load_scenarios_from_json(file_path: str) -> list[DenialScenario]:
    """
    Load denial scenarios from a local JSON file.

    Args:
        file_path: Path to JSON file with scenario array.

    Returns:
        list[DenialScenario]: Parsed and validated scenarios.
    """
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    scenarios = data.get("scenarios", data)
    return [DenialScenario(**scenario) for scenario in scenarios]


def ingest_from_json_file(
    service: ClaimsDenialChatbotService,
    file_path: str,
    force_reindex: bool,
    batch_size: int,
) -> None:
    """
    Ingest scenarios from JSON file directly to Pinecone.

    Bypasses Snowflake connector for local development and testing.

    Args:
        service: Chatbot service with vector store access.
        file_path: Path to JSON scenarios file.
        force_reindex: Whether to clear index before ingestion.
        batch_size: Batch size for embedding and upsert.
    """
    from claims_denial_chatbot.embeddings import TextEmbeddingService
    from claims_denial_chatbot.rag import DenialScenarioDocumentProcessor
    from claims_denial_chatbot.vector_store import PineconeVectorStoreManager

    scenarios = load_scenarios_from_json(file_path)
    processor = DenialScenarioDocumentProcessor()
    embedding_service = TextEmbeddingService()
    vector_store = PineconeVectorStoreManager()

    if force_reindex:
        vector_store.delete_all_vectors()

    chunks = processor.process_scenarios_batch(scenarios)
    texts = [c["text"] for c in chunks]
    embeddings = embedding_service.generate_embeddings_for_batch(texts, batch_size=batch_size)

    vectors = []
    for chunk, embedding in zip(chunks, embeddings):
        scenario_id = chunk["metadata"]["scenario_id"]
        chunk_index = chunk["metadata"]["chunk_index"]
        vector_id = f"{scenario_id}_chunk_{chunk_index}"
        vectors.append((vector_id, embedding, chunk["metadata"]))

    total = 0
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        total += vector_store.upsert_document_vectors(batch)

    logger.info(
        "json_ingestion_completed",
        scenarios=len(scenarios),
        chunks=total,
    )
    print(f"Ingested {len(scenarios)} scenarios ({total} chunks) from {file_path}")


def main() -> None:
    """Parse CLI arguments and run ingestion."""
    parser = argparse.ArgumentParser(description="Ingest denial scenarios into Pinecone")
    parser.add_argument(
        "--source",
        choices=["snowflake", "json"],
        default="json",
        help="Data source for scenarios",
    )
    parser.add_argument(
        "--file",
        default="data/denial_scenarios.json",
        help="JSON file path when source=json",
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help="Delete existing vectors before ingestion",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for embedding and upsert",
    )
    args = parser.parse_args()

    configure_structured_logging()
    service = ClaimsDenialChatbotService()

    if args.source == "json":
        ingest_from_json_file(
            service=service,
            file_path=args.file,
            force_reindex=args.force_reindex,
            batch_size=args.batch_size,
        )
    else:
        request = IngestionRequest(
            source="snowflake",
            force_reindex=args.force_reindex,
            batch_size=args.batch_size,
        )
        response = service.ingest_knowledge_base(request)
        print(
            f"Ingested {response.total_scenarios_processed} scenarios "
            f"({response.total_chunks_created} chunks) in {response.duration_seconds}s"
        )


if __name__ == "__main__":
    main()
