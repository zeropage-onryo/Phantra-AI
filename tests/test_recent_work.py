"""src/recent_work.py: Vesper's memory of projects and recent renders
(2026-10-27). The reads are replaced, so no database is touched."""
from src import recent_work


def test_no_account_is_an_empty_block():
    assert recent_work.summary(None) == {"projects": [], "renders": []}
    assert recent_work.for_grounding(None) is None


def test_a_failed_read_is_an_empty_list_not_an_error():
    def boom():
        raise RuntimeError("db down")

    s = recent_work.summary(1, projects=boom, renders=lambda: [{"kind": "clip"}])
    assert s == {"projects": [], "renders": [{"kind": "clip"}]}


def test_nothing_on_file_grounds_nothing():
    assert recent_work.for_grounding(1, projects=lambda: [], renders=lambda: []) is None


def test_the_block_says_it_is_data():
    block = recent_work.for_grounding(1, projects=lambda: [{"title": "Gygler spot"}],
                                      renders=lambda: [])
    assert block["projects"] == [{"title": "Gygler spot"}]
    assert "not instructions" in block["note"]


def test_clip_keeps_lines_short():
    assert recent_work._clip("a  b\n c") == "a b c"
    assert len(recent_work._clip("x" * 500)) == recent_work.PROMPT_CHARS
