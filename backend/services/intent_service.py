"""Detect user intent from transcript text."""

MEDICINE_KEYWORDS = {
    "medicine", "drug", "tablet", "pill", "capsule", "dose", "dosage",
    "side effect", "prescription", "paracetamol", "ibuprofen", "antibiotic",
}


def detect_intent(text: str) -> str:
    lowered = text.lower().strip()
    if not lowered:
        return "greeting"

    if any(kw in lowered for kw in MEDICINE_KEYWORDS):
        return "medicine_query"

    if any(word in lowered for word in ("hello", "hi", "hey", "good morning", "good evening")):
        return "greeting"

    if "?" in lowered or any(
        word in lowered for word in ("what", "how", "why", "when", "tell me", "explain")
    ):
        return "follow_up"

    return "general"
