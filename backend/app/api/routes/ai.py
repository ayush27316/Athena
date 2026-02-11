from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from langchain_core.tools import tool
from langchain_xai import ChatXAI
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["ai"])


# ── Pydantic models (structured output + validation) ────────────────────────


class AIRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="The user prompt")


class AIResponse(BaseModel):
    answer: str = Field(..., min_length=1, description="The generated answer")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    sources: list[str] = Field(default_factory=list, description="Referenced sources if any")


# ── Tools ────────────────────────────────────────────────────────────────────


@tool
def get_word_count(text: str) -> int:
    """Count the number of words in a given text."""
    return len(text.split())


@tool
def get_current_datetime() -> str:
    """Return the current date and time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


TOOLS = [get_word_count, get_current_datetime]


# ── Route ────────────────────────────────────────────────────────────────────


@router.post("/generate", response_model=AIResponse)
async def generate_text(body: AIRequest) -> AIResponse:
    """Generate a structured AI response using xAI Grok with tool support."""

    if not settings.XAI_API_KEY:
        raise HTTPException(status_code=500, detail="XAI_API_KEY is not configured")

    llm = ChatXAI(
        model="grok-4-1-fast-non-reasoning",
        xai_api_key=settings.XAI_API_KEY,
    )

    # Bind tools so the model knows about them
    llm_with_tools = llm.bind_tools(TOOLS)

    # First pass: let the model decide whether to call tools
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. You have access to tools: "
                "get_word_count (counts words in text) and get_current_datetime "
                "(gets the current UTC time). Use them when relevant to the user's query. "
                "After gathering any tool results, provide your final answer."
            ),
        },
        {"role": "user", "content": body.prompt},
    ]

    response = llm_with_tools.invoke(messages)

    # Handle tool calls if the model requested any
    if response.tool_calls:
        messages.append(response)

        tool_map = {t.name: t for t in TOOLS}
        for tc in response.tool_calls:
            fn = tool_map.get(tc["name"])
            if fn:
                result = fn.invoke(tc["args"])
                messages.append(
                    {
                        "role": "tool",
                        "content": str(result),
                        "tool_call_id": tc["id"],
                    }
                )

        # Second pass with tool results
        response = llm_with_tools.invoke(messages)

    # Now get structured output
    structured_llm = llm.with_structured_output(AIResponse)

    structured_response = structured_llm.invoke(
        [
            {
                "role": "system",
                "content": (
                    "Convert the following assistant response into the required JSON format. "
                    "Set confidence between 0 and 1 based on how certain the answer is. "
                    "Include any sources if referenced."
                ),
            },
            {"role": "user", "content": response.content},
        ]
    )

    return structured_response
