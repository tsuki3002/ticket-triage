from abc import ABC, abstractmethod

from schemas.ai_analysis import TicketAnalysis


class AIProvider(ABC):
    @abstractmethod
    async def analyze_ticket(
        self, subject: str, description: str, product_module: str | None = None
    ) -> TicketAnalysis:
        """
        Analyze a ticket and return structured suggestions.
        Implementations should raise on failure (network error, malformed
        response, schema validation failure) -- callers are responsible for
        catching and handling failures gracefully.
        """
        raise NotImplementedError