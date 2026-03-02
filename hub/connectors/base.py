from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Abstract base class for all external service connectors."""

    @abstractmethod
    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch data from the external service.

        Args:
            params: Connector-specific query parameters.

        Returns:
            Connector-specific response dict.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Check whether the connector can reach its upstream service.

        Returns:
            True if healthy, False otherwise.
        """

    async def push(self, data: dict[str, Any]) -> bool:
        """Write data to the external service.

        Only connectors that support write operations need to implement this.

        Args:
            data: Connector-specific payload.

        Returns:
            True if the write succeeded.

        Raises:
            NotImplementedError: If the connector does not support writes.
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support push()")
