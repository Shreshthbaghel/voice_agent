"""Medicine DB lookup helpers with spelled-name / fuzzy matching."""
from __future__ import annotations

import logging
import re
import unicodedata
from difflib import get_close_matches

from sqlalchemy.orm import Session

from orm_models import Medicine
from seed_data import SEED_MEDICINES

logger = logging.getLogger(__name__)

# Hindi "letter names" spoken when spelling (Devanagari → Latin)
_DEVANAGARI_LETTER = {
    "ए": "a", "अ": "a", "आ": "a",
    "बी": "b", "ब": "b",
    "सी": "c", "स": "s",
    "डी": "d", "द": "d",
    "ई": "e", "इ": "i",
    "एफ़": "f", "एफ": "f",
    "जी": "g", "ज": "j",
    "एच": "h", "ऐच": "h", "ह": "h",
    "जे": "j",
    "के": "k", "क": "k",
    "एल": "l", "ल": "l",
    "एम": "m", "म": "m",
    "एन": "n", "न": "n",
    "ओ": "o", "औ": "o",
    "पी": "p", "प": "p",
    "क्यू": "q",
    "आर": "r", "र": "r",
    "एस": "s",
    "टी": "t", "त": "t", "ट": "t",
    "यू": "u", "उ": "u", "ऊ": "u",
    "वी": "v", "व": "v",
    "डब्ल्यू": "w", "डब्लू": "w",
    "एक्स": "x",
    "वाई": "y", "य": "y",
    "जेड": "z", "ज़ेड": "z",
}

_ALIASES = {
    "dolo": "dolo 650",
    "dolo650": "dolo 650",
    "crocin": "crocin",
    "pcm": "paracetamol",
    "acetaminophen": "paracetamol",
    "peracetamol": "paracetamol",
    "parasetamol": "paracetamol",
    "parasitemol": "paracetamol",
}


def seed_medicines(db: Session) -> None:
    if db.query(Medicine).first():
        return
    for item in SEED_MEDICINES:
        db.add(Medicine(**item))
    db.commit()
    logger.info("Seeded %d medicines", len(SEED_MEDICINES))


def _latin_letters_only(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _clean_token(tok: str) -> str:
    return re.sub(r"[\s।.,!?;:/\\|'\"""]+", "", (tok or "").strip())


def unwrap_spelled_name(raw: str) -> str:
    """Join letter-by-letter spelling (Latin or Hindi letter names) into one word."""
    text = (raw or "").strip()
    if not text:
        return text

    tokens = [_clean_token(t) for t in re.split(r"[\s,.\-/|;:]+", text)]
    tokens = [t for t in tokens if t]
    if len(tokens) < 3:
        return text

    joined: list[str] = []
    for tok in tokens:
        mapped = _DEVANAGARI_LETTER.get(tok)
        if mapped:
            joined.append(mapped)
            continue
        if len(tok) == 1 and "a" <= tok.lower() <= "z":
            joined.append(tok.lower())
            continue
        latin = _latin_letters_only(tok)
        if len(latin) == 1:
            joined.append(latin)
            continue
        if len(latin) > 2:
            return text
        if latin:
            joined.append(latin)
            continue
        return text

    if len(joined) >= 3:
        word = "".join(joined)
        logger.info("Joined spelled medicine name → %s", word)
        return word
    return text


def normalize_medicine_query(name: str) -> str:
    unwrapped = unwrap_spelled_name(name)
    compact = _latin_letters_only(unicodedata.normalize("NFKC", unwrapped))
    if compact in _ALIASES:
        return _ALIASES[compact]
    original = _latin_letters_only(name)
    if original in _ALIASES:
        return _ALIASES[original]
    return unwrapped.strip()


def search_medicine_by_name(db: Session, name: str) -> Medicine | None:
    query = normalize_medicine_query(name)
    normalized = query.strip().lower()
    compact = _latin_letters_only(normalized)
    medicines = db.query(Medicine).all()
    if not medicines:
        return None

    for med in medicines:
        if med.name.lower() == normalized:
            return med
    for med in medicines:
        med_l = med.name.lower()
        if normalized in med_l or med_l in normalized:
            return med
        med_c = _latin_letters_only(med.name)
        if compact and (med_c in compact or compact in med_c):
            return med

    catalog = [med.name for med in medicines]
    catalog_lower = [n.lower() for n in catalog]
    catalog_compact = [_latin_letters_only(n) for n in catalog]
    needle = compact or normalized
    close = get_close_matches(needle, catalog_compact, n=1, cutoff=0.72)
    if close:
        idx = catalog_compact.index(close[0])
        logger.info("Fuzzy matched query → %s", catalog[idx])
        return medicines[idx]
    close = get_close_matches(normalized, catalog_lower, n=1, cutoff=0.72)
    if close:
        idx = catalog_lower.index(close[0])
        logger.info("Fuzzy matched query → %s", catalog[idx])
        return medicines[idx]

    return None


def format_medicine_response(medicine: Medicine) -> str:
    rx = "requires a prescription" if medicine.prescription_needed else "available over the counter"
    return (
        f"Found: {medicine.name}\n"
        f"Use: {medicine.use_case}\n"
        f"Common side effects: {medicine.side_effects}\n"
        f"This medicine {rx}."
    )
