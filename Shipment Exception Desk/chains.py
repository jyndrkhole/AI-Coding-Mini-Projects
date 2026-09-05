"""Three ready-made LangChain chains: classify / escalate / draft email.

Same Class 2 pattern: prompt | model | parser.
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from llm import get_chat_model

classify_prompt = ChatPromptTemplate.from_template(
    """You are a shipment-exception classifier for Northwind Logistics.

Read the exception report and reply with EXACTLY one word, lowercase:
delayed
damaged
lost
unknown

Rules:
- delayed: late arrival, missed ETA, stuck in transit. The goods themselves are fine.
- damaged: broken, crushed, wet, leaking, dented, spoiled, or otherwise harmed.
- lost: never arrived, missing, stolen, no useful tracking, cannot be found.
- unknown: garbled, contradictory, unrelated, or you cannot tell which of the three it is.

If the text is nonsense, incomplete, or not about a shipment problem, choose unknown.

Report:
{report}

Reply with only that one word. No punctuation and no explanation."""
)

escalate_prompt = ChatPromptTemplate.from_template(
    """Draft a short internal note to a Northwind Logistics manager.

Shipment exception report:
{report}

Category: {category}
Customer tier: {customer_tier}
Shipment value: ${shipment_value}
Calculated compensation: ${compensation_amount}
Why this was escalated: {escalation_reason}

Write 4-8 sentences. Be concise and operational: what happened, the dollar exposure,
and what the manager should decide. Do not write a customer-facing email."""
)

draft_email_prompt = ChatPromptTemplate.from_template(
    """Draft a short customer-facing email from Northwind Logistics.

Shipment exception report:
{report}

Category: {category}
Customer tier: {customer_tier}
Shipment value: ${shipment_value}
Approved compensation: ${compensation_amount}

Tone: empathetic, clear, professional. Acknowledge the issue, state the
compensation we will issue, and say no further action is needed from them.
Do not mention internal escalation or manager review. Sign as Northwind Logistics."""
)

parser = StrOutputParser()


class _LazyChain:
    """Compose prompt | model | parser on first invoke so imports stay cheap."""

    def __init__(self, prompt: ChatPromptTemplate) -> None:
        self._prompt = prompt
        self._chain = None

    def _unwrap(self):
        if self._chain is None:
            self._chain = self._prompt | get_chat_model() | parser
        return self._chain

    def invoke(self, inputs):
        return self._unwrap().invoke(inputs)


classify_chain = _LazyChain(classify_prompt)
escalate_chain = _LazyChain(escalate_prompt)
draft_email_chain = _LazyChain(draft_email_prompt)
