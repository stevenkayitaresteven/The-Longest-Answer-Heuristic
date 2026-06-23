"""Unit tests for defensive MCQ parsing."""
from parsing import parse_items


def test_clean_json_array():
    text = '[{"stem":"s","options":["a","b","c","d"],"answer_index":2}]'
    r = parse_items(text, k=4)
    assert r.n_valid == 1 and r.n_rejected == 0
    assert r.items[0]["answer_index"] == 2


def test_code_fenced_and_prefixed():
    text = ('Sure! Here you go:\n```json\n'
            '[{"stem":"s","options":["a","b","c","d"],"answer_index":0}]\n```')
    r = parse_items(text, k=4)
    assert r.n_valid == 1


def test_wrong_option_count_rejected():
    text = '[{"stem":"s","options":["a","b","c"],"answer_index":0}]'
    r = parse_items(text, k=4)
    assert r.n_valid == 0 and r.n_rejected == 1


def test_out_of_range_index_rejected():
    text = '[{"stem":"s","options":["a","b","c","d"],"answer_index":9}]'
    r = parse_items(text, k=4)
    assert r.n_valid == 0 and r.n_rejected == 1


def test_boolean_index_rejected():
    # bools are ints in Python; the parser must not accept True as an index
    text = '[{"stem":"s","options":["a","b","c","d"],"answer_index":true}]'
    r = parse_items(text, k=4)
    assert r.n_valid == 0


def test_empty_option_rejected():
    text = '[{"stem":"s","options":["a","","c","d"],"answer_index":0}]'
    r = parse_items(text, k=4)
    assert r.n_valid == 0


def test_no_json_returns_note():
    r = parse_items("I cannot do that.", k=4)
    assert r.n_valid == 0 and "no JSON array" in r.note
