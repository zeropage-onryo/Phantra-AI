"""Seedance refuses a real person's photo as a reference on every host
(2026-11-02, src/people_refs.py): the card says so before the click, the
refusal reads as what to do, and Vesper's picks steer around it."""
from pathlib import Path

from src import failures, fal, people_refs

PERSON = "characters/michael/07-headshot-frontal-neutral.jpg"
PRODUCT = "props/mug/front.jpg"


def test_every_refusing_and_offered_model_is_a_real_row():
    for model in people_refs.REFUSE_REAL_PEOPLE + people_refs.FOR_PEOPLE:
        assert model in fal.VIDEO_MODELS or model in fal.SLOTS, model
    assert not set(people_refs.REFUSE_REAL_PEOPLE) & set(people_refs.FOR_PEOPLE)


def test_a_character_photo_or_a_subject_role_is_a_person_and_a_product_is_not():
    assert people_refs.holds_person([PERSON])
    assert people_refs.holds_person(["refs/abc.jpg"], {"refs/abc.jpg": "subject"})
    assert not people_refs.holds_person([PRODUCT])
    assert not people_refs.holds_person(["refs/abc.jpg"], {"refs/abc.jpg": "light"})
    assert not people_refs.holds_person([])


def test_the_note_is_for_seedance_with_a_person_only():
    shot = {"refs": [PERSON, PRODUCT]}
    assert people_refs.note_for("seedance2.5", shot) == people_refs.NOTE
    assert people_refs.note_for("kling4", shot) == ""
    assert people_refs.note_for("seedance2.5", {"refs": [PRODUCT]}) == ""
    assert people_refs.card_fields(shot)["people_refusers"] == list(people_refs.REFUSE_REAL_PEOPLE)
    assert people_refs.card_fields({"refs": [PRODUCT]}) == {
        "holds_person": False, "people_refusers": [], "people_note": ""}


def test_the_refusal_says_which_model_to_use_not_reword_it():
    raw = ('422 {"detail":[{"msg":"The images or videos provided may contain likenesses of '
           'real people or other private information that cannot be processed.",'
           '"type":"content_policy_violation","ctx":{"extra_info":{"reason":'
           '"partner_validation_failed"}}}]}')
    said = failures.plain(raw, "The clip")
    assert "Kling 4.0 or Veo 3.1" in said and "Reword" not in said
    assert said.endswith(failures.NOT_CHARGED)


def test_vesper_is_told_never_to_put_a_real_person_on_seedance():
    picks = (Path(__file__).resolve().parents[1] / "prompts" / "model_picks.txt").read_text()
    assert "A REAL PERSON from their own photos" in picks and "never a seedance model" in picks
