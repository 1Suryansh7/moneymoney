"""AI diagnostics kernel: deterministic classification and provenance."""

from analog_ic_design.ai.actions import HUMAN_DECISIONS, record_ai_action
from analog_ic_design.ai.explainer import (
    REFUSAL,
    SHIPPED_SYSTEM_PROMPT,
    Explanation,
    explain_failure,
    narrate_optimization,
)
from analog_ic_design.ai.provider import (
    GEMINI_API_HOST,
    UNCONFIGURED,
    GeminiProvider,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    MockProvider,
    Transport,
    resolve_alias,
)
from analog_ic_design.ai.residency import (
    DISABLED,
    HOSTED_ALLOWED,
    LOCAL_ONLY,
    REDACTED,
    HostedOptIn,
    ProviderGuard,
    redact_payload,
)
from analog_ic_design.ai.taxonomy import TAXONOMY, ClassifiedFailure, classify_failure

__all__ = [
    "DISABLED",
    "GEMINI_API_HOST",
    "HOSTED_ALLOWED",
    "HUMAN_DECISIONS",
    "LOCAL_ONLY",
    "REDACTED",
    "TAXONOMY",
    "ClassifiedFailure",
    "Explanation",
    "GeminiProvider",
    "HostedOptIn",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "MockProvider",
    "ProviderGuard",
    "REFUSAL",
    "SHIPPED_SYSTEM_PROMPT",
    "Transport",
    "UNCONFIGURED",
    "classify_failure",
    "explain_failure",
    "narrate_optimization",
    "record_ai_action",
    "redact_payload",
    "resolve_alias",
]
