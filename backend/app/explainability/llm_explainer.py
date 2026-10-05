"""
LLM Explainer — Evidence-Grounded Mechanism Explanation
========================================================
Uses an LLM to generate human-readable investigation summaries
ONLY after the analytical pipeline has produced structured evidence.

IMPORTANT:
  - The LLM NEVER invents evidence
  - Every generated statement must be grounded in actual data items
  - Evidence IDs, timestamps, and source tables are included in the prompt
  - The prompt explicitly instructs the LLM to stay within provided facts

Supported providers: openai | google | ollama | none
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from app.core.config import settings
from app.mechanisms.discovery import CandidateMechanismHypothesis


EVIDENCE_GROUNDED_SYSTEM_PROMPT = """You are an industrial failure analysis assistant.
You will receive structured evidence about a manufacturing failure investigation.
Your role is to write a clear, professional investigation summary.

CRITICAL RULES:
1. Only reference evidence that is explicitly provided to you in the structured data.
2. Do NOT invent, assume, or extrapolate beyond what the data shows.
3. Clearly distinguish between 'supported by evidence' and 'hypothesis'.
4. Use precise technical language appropriate for engineering reports.
5. Include confidence levels as stated in the data.
6. Note any contradicting or missing evidence explicitly.
7. End with a clear recommendation that acknowledges uncertainty.
"""


class LLMExplainer:
    """Generates evidence-grounded LLM explanations for investigation results."""

    def __init__(self):
        self.provider = settings.llm_provider
        self._client = None

    async def _get_client(self):
        """Lazily initialize the LLM client."""
        if self._client:
            return self._client

        if self.provider == "openai":
            import openai
            self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        elif self.provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=settings.google_api_key)
            self._client = genai.GenerativeModel("gemini-pro")
        elif self.provider == "ollama":
            import httpx
            self._client = httpx.AsyncClient(base_url=settings.ollama_base_url)
        else:
            self._client = None

        return self._client

    def _build_evidence_prompt(
        self,
        investigation_name: str,
        failure_event: Dict[str, Any],
        top_mechanisms: List[CandidateMechanismHypothesis],
    ) -> str:
        """Build a structured, evidence-grounded prompt."""

        lines = [
            f"INVESTIGATION: {investigation_name}",
            f"FAILURE EVENT: {failure_event.get('event_type', 'Unknown')} at {failure_event.get('event_time', 'Unknown')}",
            f"SEVERITY: {failure_event.get('severity', 'Unknown')}",
            "",
            "RANKED CANDIDATE MECHANISMS (from algorithmic analysis — NOT confirmed causal facts):",
            "",
        ]

        for i, mech in enumerate(top_mechanisms, 1):
            lines.append(f"RANK {i}: {mech.name} (type: {mech.mechanism_type})")
            lines.append(f"  Overall Score: {mech.overall_score:.3f}")
            lines.append(f"  Confidence: {mech.confidence:.3f}")
            if mech.cause:
                lines.append(f"  Postulated Cause: {mech.cause}")
            if mech.observable_failure:
                lines.append(f"  Observable Effect: {mech.observable_failure}")

            lines.append(f"  Supporting Evidence ({len(mech.supporting_evidence)} items):")
            for ev in mech.supporting_evidence[:5]:  # limit for token budget
                lines.append(
                    f"    [SUPPORT] [{ev.evidence_type}] strength={ev.strength:.2f}: {ev.description}"
                )
                if ev.source_timestamp:
                    lines.append(f"           Source timestamp: {ev.source_timestamp}")
                if ev.lag_hours is not None:
                    lines.append(f"           Lag before failure: {ev.lag_hours:.1f} hours")

            if mech.contradicting_evidence:
                lines.append(f"  Contradicting Evidence ({len(mech.contradicting_evidence)} items):")
                for ev in mech.contradicting_evidence[:3]:
                    lines.append(
                        f"    [CONTRA] [{ev.evidence_type}] strength={ev.strength:.2f}: {ev.description}"
                    )

            if mech.missing_evidence:
                lines.append(f"  Missing Evidence:")
                for me in mech.missing_evidence[:3]:
                    lines.append(f"    [MISSING] {me}")

            lines.append(f"  Scoring breakdown:")
            lines.append(f"    temporal_consistency={mech.temporal_consistency_score:.3f}")
            lines.append(f"    evidence_strength={mech.evidence_strength_score:.3f}")
            lines.append(f"    evidence_coverage={mech.evidence_coverage_score:.3f}")
            lines.append(f"    contradiction_penalty={mech.contradiction_penalty:.3f}")
            lines.append("")

        lines += [
            "TASK:",
            "Based ONLY on the above structured evidence, write a professional investigation summary that:",
            "1. Identifies the most likely failure mechanism(s) with confidence levels",
            "2. Describes the evidence chain (temporal sequence if applicable)",
            "3. Notes key contradicting or missing evidence",
            "4. Provides a recommended next step for verification",
            "5. Explicitly states that these are algorithmic hypotheses, not confirmed root causes",
            "",
            "Write approximately 300-500 words. Use formal engineering report style.",
        ]

        return "\n".join(lines)

    async def generate_investigation_summary(
        self,
        investigation: Any,
        top_mechanisms: List[CandidateMechanismHypothesis],
        failure_event: Dict[str, Any],
    ) -> Optional[str]:
        """Generate a human-readable summary grounded in structured evidence."""

        if self.provider == "none":
            return None

        prompt = self._build_evidence_prompt(
            investigation_name=investigation.name,
            failure_event=failure_event,
            top_mechanisms=top_mechanisms,
        )

        try:
            client = await self._get_client()

            if self.provider == "openai":
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": EVIDENCE_GROUNDED_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=settings.llm_max_tokens,
                    temperature=settings.llm_temperature,
                )
                return response.choices[0].message.content

            elif self.provider == "google":
                response = await client.generate_content_async(
                    f"{EVIDENCE_GROUNDED_SYSTEM_PROMPT}\n\n{prompt}"
                )
                return response.text

            elif self.provider == "ollama":
                response = await client.post(
                    "/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": f"{EVIDENCE_GROUNDED_SYSTEM_PROMPT}\n\n{prompt}",
                        "stream": False,
                        "options": {
                            "num_predict": settings.llm_max_tokens,
                            "temperature": settings.llm_temperature,
                        },
                    },
                    timeout=120.0,
                )
                return response.json().get("response")

        except Exception as e:
            logger.warning(f"LLM explanation generation failed: {e}")
            return None
