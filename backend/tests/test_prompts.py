import pytest

from app.prompts import (
    LANGUAGE_NAMES,
    VALID_DETAILS,
    VALID_MODES,
    build_system_prompt,
    default_question,
)


@pytest.mark.parametrize("mode", VALID_MODES)
@pytest.mark.parametrize("detail", VALID_DETAILS)
@pytest.mark.parametrize("lang", list(LANGUAGE_NAMES))
def test_every_combination_builds(mode, detail, lang):
    prompt = build_system_prompt(lang, detail, mode)
    assert LANGUAGE_NAMES[lang] in prompt
    assert "no markdown" in prompt
    assert default_question(mode)


def test_product_mode_has_medicine_safety_rule():
    prompt = build_system_prompt("en", "detailed", "product")
    assert "pharmacist" in prompt


def test_currency_mode_mentions_dirham():
    assert "dirham" in build_system_prompt("fr", "brief", "currency")


def test_unknown_values_fall_back_safely():
    prompt = build_system_prompt("xx", "weird", "nope")
    assert "English" in prompt
    assert "Mode: describe" in prompt
