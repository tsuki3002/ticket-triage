import json
import os

from dotenv import load_dotenv
from groq import Groq

from ai.base import AIProvider
from schemas.ai_analysis import TicketAnalysis

load_dotenv()

SYSTEM_PROMPT = """You are an assistant that triages customer support tickets for an internal support team.

You will be given a ticket subject and description. Analyze ONLY the information provided -- do not invent details, timelines, root causes, or commitments that are not stated.

Return a single JSON object with EXACTLY these fields and nothing else (no markdown, no preamble, no explanation):

{
  "summary": string, 1-3 sentences describing the main problem and affected service/module,
  "category": one of ["Authentication","Billing","Performance","Data Issue","Integration","User Interface","Access Request","Feature Request","Security","General Support","Unknown"],
  "priority": one of ["Low","Medium","High","Critical"],
  "priority_reason": string, one short sentence justifying the priority,
  "recommended_team": string, e.g. "Platform Engineering","Application Engineering","Security","DevOps","Database Team","Billing Team","Customer Support","Product Team",
  "suggested_response": string, a short professional customer-facing reply
}

Priority guidance:
- Critical: production down, all users affected, security incident, or data-loss risk.
- High: major feature broken, multiple users affected, workaround may exist.
- Medium: small number of users affected, business continues.
- Low: minimal impact, workaround exists, informational.

Rules for suggested_response:
- Acknowledge the issue professionally.
- Do NOT promise a resolution time unless one was given.
- Do NOT claim the issue is already resolved.
- Do NOT expose internal technical detail.
- Do NOT blame the customer.

If there is not enough information to pick a category, use "Unknown". Never fabricate facts not present in the ticket."""


class GroqProvider(AIProvider):
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set in the environment")
        self.client = Groq(api_key=api_key)
        self.model = model

    async def analyze_ticket(
        self, subject: str, description: str, product_module: str | None = None
    ) -> TicketAnalysis:
        user_content = f"Subject: {subject}\n\nDescription: {description}"
        if product_module:
            user_content += f"\n\nProduct/Module: {product_module}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
        )

        raw_text = response.choices[0].message.content.strip()

        # DEBUG: uncomment while testing to see exactly what Groq returned
        print("---- RAW GROQ OUTPUT ----")
        print(raw_text)
        print("-------------------------")

        raw_text = self._extract_json(raw_text)

        # json.JSONDecodeError and pydantic.ValidationError both propagate up
        # to the caller (TicketService), which treats them as an AI failure.
        data = json.loads(raw_text)
        return TicketAnalysis(**data)

    @staticmethod
    def _extract_json(text: str) -> str:
        """
        Models sometimes add preamble text or markdown fences even when told
        not to. Strip fences first, then fall back to grabbing the substring
        between the first '{' and the last '}' so stray text around the JSON
        doesn't break parsing.
        """
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1] if text.count("```") >= 2 else text
            text = text.removeprefix("json").strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            return text  # let json.loads raise a clear error
        return text[start : end + 1]