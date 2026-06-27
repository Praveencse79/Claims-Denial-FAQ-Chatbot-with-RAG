"""
Snowflake database connector for the Claims Denial knowledge base.

Provides connection management and query execution for retrieving
denial scenario records from Snowflake tables.
"""

from contextlib import contextmanager
from typing import Any, Generator

import snowflake.connector
from snowflake.connector import DictCursor

from claims_denial_chatbot.config import get_application_settings
from claims_denial_chatbot.core.exceptions import SnowflakeConnectionError
from claims_denial_chatbot.core.logging import get_logger
from claims_denial_chatbot.models.schemas import DenialScenario

logger = get_logger(__name__)


class SnowflakeKnowledgeBaseConnector:
    """
    Manages Snowflake connections and queries for denial scenario data.

    Handles connection pooling via context managers and provides typed
    methods for fetching denial scenarios from the configured Snowflake table.
    """

    def __init__(self) -> None:
        """Initialize connector with settings from environment configuration."""
        self._settings = get_application_settings()
        self._connection: snowflake.connector.SnowflakeConnection | None = None

    def _build_connection_parameters(self) -> dict[str, Any]:
        """
        Build Snowflake connection parameter dictionary from settings.

        Returns:
            dict: Connection kwargs for snowflake.connector.connect().
        """
        return {
            "account": self._settings.snowflake_account,
            "user": self._settings.snowflake_user,
            "password": self._settings.snowflake_password.get_secret_value(),
            "warehouse": self._settings.snowflake_warehouse,
            "database": self._settings.snowflake_database,
            "schema": self._settings.snowflake_schema,
            "role": self._settings.snowflake_role,
        }

    @contextmanager
    def get_connection(self) -> Generator[snowflake.connector.SnowflakeConnection, None, None]:
        """
        Context manager yielding a Snowflake connection.

        Opens connection on enter, closes on exit. Use for single-query
        operations or when connection should not persist.

        Yields:
            SnowflakeConnection: Active database connection.

        Raises:
            SnowflakeConnectionError: If connection cannot be established.
        """
        connection = None
        try:
            connection = snowflake.connector.connect(
                **self._build_connection_parameters()
            )
            logger.info("snowflake_connection_established")
            yield connection
        except snowflake.connector.Error as exc:
            logger.error("snowflake_connection_failed", error=str(exc))
            raise SnowflakeConnectionError(
                f"Failed to connect to Snowflake: {exc}",
                details={"account": self._settings.snowflake_account},
            ) from exc
        finally:
            if connection is not None:
                connection.close()
                logger.info("snowflake_connection_closed")

    def fetch_all_denial_scenarios(self) -> list[DenialScenario]:
        """
        Retrieve all denial scenarios from the Snowflake knowledge base table.

        Executes a SELECT on the configured denial scenarios table and maps
        rows to DenialScenario Pydantic models.

        Returns:
            list[DenialScenario]: All denial scenario records.

        Raises:
            SnowflakeConnectionError: On query execution failure.
        """
        table_name = self._settings.snowflake_denial_table
        query = f"""
            SELECT
                SCENARIO_ID,
                DENIAL_CODE,
                DENIAL_CATEGORY,
                PAYER_NAME,
                DENIAL_DESCRIPTION,
                RESOLUTION_STEPS,
                REQUIRED_DOCUMENTATION,
                SEVERITY,
                AVERAGE_RESOLUTION_DAYS,
                SUCCESS_RATE_PERCENT,
                CREATED_AT,
                UPDATED_AT
            FROM {table_name}
            WHERE IS_ACTIVE = TRUE
            ORDER BY SCENARIO_ID
        """

        with self.get_connection() as conn:
            cursor = conn.cursor(DictCursor)
            try:
                cursor.execute(query)
                rows = cursor.fetchall()
                logger.info("denial_scenarios_fetched", count=len(rows))
                return [self._map_row_to_denial_scenario(row) for row in rows]
            except snowflake.connector.Error as exc:
                logger.error("denial_scenarios_fetch_failed", error=str(exc))
                raise SnowflakeConnectionError(
                    f"Failed to fetch denial scenarios: {exc}"
                ) from exc
            finally:
                cursor.close()

    def fetch_denial_scenario_by_code(self, denial_code: str) -> list[DenialScenario]:
        """
        Fetch denial scenarios matching a specific CARC/RARC denial code.

        Args:
            denial_code: Denial code to filter by (e.g., "CO-16").

        Returns:
            list[DenialScenario]: Matching denial scenarios, empty if none found.
        """
        table_name = self._settings.snowflake_denial_table
        query = f"""
            SELECT *
            FROM {table_name}
            WHERE DENIAL_CODE = %s AND IS_ACTIVE = TRUE
        """

        with self.get_connection() as conn:
            cursor = conn.cursor(DictCursor)
            try:
                cursor.execute(query, (denial_code,))
                rows = cursor.fetchall()
                return [self._map_row_to_denial_scenario(row) for row in rows]
            except snowflake.connector.Error as exc:
                raise SnowflakeConnectionError(
                    f"Failed to fetch scenario for code {denial_code}: {exc}"
                ) from exc
            finally:
                cursor.close()

    def _map_row_to_denial_scenario(self, row: dict[str, Any]) -> DenialScenario:
        """
        Map a Snowflake result row dict to a DenialScenario model.

        Handles column name normalization (uppercase Snowflake columns to
        lowercase Python field names) and type coercion for list fields.

        Args:
            row: Dictionary from DictCursor fetch.

        Returns:
            DenialScenario: Validated Pydantic model instance.
        """
        resolution_steps = row.get("RESOLUTION_STEPS") or []
        if isinstance(resolution_steps, str):
            resolution_steps = [
                step.strip() for step in resolution_steps.split("|") if step.strip()
            ]

        required_docs = row.get("REQUIRED_DOCUMENTATION") or []
        if isinstance(required_docs, str):
            required_docs = [
                doc.strip() for doc in required_docs.split("|") if doc.strip()
            ]

        return DenialScenario(
            scenario_id=str(row["SCENARIO_ID"]),
            denial_code=row["DENIAL_CODE"],
            denial_category=row["DENIAL_CATEGORY"],
            payer_name=row["PAYER_NAME"],
            denial_description=row["DENIAL_DESCRIPTION"],
            resolution_steps=resolution_steps,
            required_documentation=required_docs,
            severity=row.get("SEVERITY", "medium"),
            average_resolution_days=row.get("AVERAGE_RESOLUTION_DAYS", 14),
            success_rate_percent=float(row.get("SUCCESS_RATE_PERCENT", 0.0)),
            created_at=row.get("CREATED_AT"),
            updated_at=row.get("UPDATED_AT"),
        )
