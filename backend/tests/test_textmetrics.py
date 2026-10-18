import pytest

from app.textmetrics import forbidden_hits, mention_score, normalize, text_cer


def test_normalize_strips_accents_case_punctuation():
    assert normalize("  Caf\u00e9, TV! ") == "cafe tv"


def test_normalize_keeps_arabic_letters():
    text = "\u0627\u0644\u0628\u0627\u0628 \u0645\u0641\u062a\u0648\u062d"
    assert normalize(text) == text
    assert mention_score(text, "\u0645\u0641\u062a\u0648\u062d") == (1, 1)


def test_mention_score_groups_and_alternatives():
    assert mention_score("A sofa and a TV.", "sofa/couch|tv/television") == (2, 2)
    assert mention_score("A couch.", "sofa/couch|tv/television") == (1, 2)


def test_mention_score_allows_simple_plurals():
    assert mention_score("Two sofas.", "sofa") == (1, 1)


def test_mention_score_whole_words_only():
    assert mention_score("A carpet.", "car") == (0, 1)


def test_mention_score_empty_spec():
    assert mention_score("anything", "") == (0, 0)


def test_forbidden_hits():
    assert forbidden_hits("I see a dog and a cat.", "dog|bird/cat") == ["dog", "cat"]
    assert forbidden_hits("A quiet room.", "dog|bird") == []


def test_cer_exact_text_inside_longer_answer():
    assert text_cer("HELLO WORLD", "The sign says hello world.") == 0.0


def test_cer_one_substitution():
    assert text_cer("hello world", "it says hello wurld") == pytest.approx(1 / 11)


def test_cer_empty_reference():
    assert text_cer("", "anything") is None
