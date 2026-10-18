"""Scoring helpers for the benchmark (no network, no model calls).

Ground-truth format in manifest.csv:
  must_mention / must_not_mention: groups separated by |, alternatives inside a group by /
  exact_text: the text that is really on the sign or product

Matching rules (documented because the report must state them):
  - answers and terms are lower-cased, accents and punctuation removed
  - a term matches a whole word, optionally followed by s or es (sofa matches sofas, car does not match carpet)
  - coverage = groups with at least one alternative found / total groups
  - CER = edit distance between exact_text and the best-matching part of the answer / length of exact_text,
    so extra spoken words around the text are not counted as errors (case and spacing ignored, accents kept)
"""
import re
import unicodedata


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_groups(spec: str) -> list[list[str]]:
    groups = []
    for group in (spec or "").split("|"):
        alternatives = [normalize(a) for a in group.split("/")]
        alternatives = [a for a in alternatives if a]
        if alternatives:
            groups.append(alternatives)
    return groups


def _found(term: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?:s|es)?(?!\w)", text) is not None


def mention_score(answer: str, spec: str) -> tuple[int, int]:
    """Return (groups found, total groups). Total 0 means no ground truth was written."""
    text = normalize(answer)
    groups = parse_groups(spec)
    hits = sum(1 for g in groups if any(_found(a, text) for a in g))
    return hits, len(groups)


def forbidden_hits(answer: str, spec: str) -> list[str]:
    text = normalize(answer)
    found = []
    for group in parse_groups(spec):
        for alt in group:
            if _found(alt, text) and alt not in found:
                found.append(alt)
    return found


def _ocr_norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").casefold()).strip()


def _best_substring_distance(ref: str, hyp: str) -> int:
    prev = [0] * (len(hyp) + 1)
    for i in range(1, len(ref) + 1):
        cur = [i] + [0] * len(hyp)
        for j in range(1, len(hyp) + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            cur[j] = min(prev[j - 1] + cost, prev[j] + 1, cur[j - 1] + 1)
        prev = cur
    return min(prev)


def text_cer(reference: str, answer: str) -> float | None:
    ref = _ocr_norm(reference)
    if not ref:
        return None
    return _best_substring_distance(ref, _ocr_norm(answer)) / len(ref)
