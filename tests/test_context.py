"""Every hand-written fact on the page carries its source (ADR 24)."""

import re

from src.dashboard import context


def test_every_fact_has_a_source_name_url_and_date():
    facts = context.facts()
    assert len(facts) >= 9
    for fact in facts:
        assert fact.text.strip() and fact.source.strip(), fact
        assert fact.url.startswith("https://"), fact
        assert re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", fact.date), fact


def test_every_fact_opens_with_a_word_and_ends_a_sentence():
    for fact in context.facts():
        assert re.match(r"[A-Z]", fact.text), fact.text
        assert fact.text.endswith("."), fact.text


def test_facts_state_no_policy_position():
    for fact in context.facts():
        assert not re.search(r"(should|must|ought)", fact.text, re.I), fact.text


def test_what_can_be_done_names_the_enforcers_and_where_to_report():
    assert [f.source for _, _, f in context.BEING_DONE] == [
        "Philippine Competition Act",
        "Philippine Competition Commission",
        "Anti-Agricultural Economic Sabotage Act",
        "Department of Agriculture",
    ]
    assert [f.source for f in context.REPORT] == [
        "Philippine Competition Commission",
        "Anti-Agricultural Economic Sabotage Act",
    ]
