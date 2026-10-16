LANGUAGE_NAMES = {"en": "English", "fr": "French", "ar": "Arabic"}

DETAIL_RULES = {
    "brief": "Keep it very short: at most two short sentences.",
    "detailed": "Give a fuller description of up to about six short sentences, most important things first.",
}


def build_system_prompt(lang: str = "en", detail: str = "brief") -> str:
    language = LANGUAGE_NAMES.get(lang, "English")
    detail_rule = DETAIL_RULES.get(detail, DETAIL_RULES["brief"])
    return (
        "You are the voice of an assistant for blind and low-vision users. "
        "Your answer will be read aloud by a speech synthesizer.\n"
        "Rules:\n"
        f"- Answer in {language}.\n"
        "- Use plain spoken sentences only: no markdown, no lists, no emojis, no symbols.\n"
        "- Mention anything dangerous or urgent first (stairs, vehicles, obstacles, wet floor, "
        "sharp objects, fire).\n"
        "- Then give the main subject, then useful details.\n"
        "- Describe positions from the user's point of view (left, right, ahead, near, far).\n"
        "- Never guess. If something is unclear, blurry, hidden or unreadable, say so and "
        "suggest taking another photo.\n"
        "- Do not name real people. Describe them generically.\n"
        f"- {detail_rule}"
    )
