"""What each attached reference is FOR (item 8 of docs/tasks/task-studio-agent.md).

A frame attached for its light used to be read like a frame attached for
its subject. A role is one word on a reference; code turns it into the
caption the model reads before that picture, and keeps a picture that
only lends its look out of the slot a keyframe and a clip anchor on.
"""
import json

from src import ref_roles, shootgen


def test_a_role_is_a_caption_that_says_what_to_take_and_what_to_leave():
    for role in ref_roles.ROLES:
        said = ref_roles.caption(role)
        assert said.startswith("Reference photo — ") and said.endswith(":")
    # what is only borrowed says ONLY, and names what not to copy
    for role in ref_roles.LOOK_ONLY:
        said = ref_roles.caption(role)
        assert "ONLY" in said and "Do not copy its subject" in said
    # what the picture is OF says exact
    for role in ref_roles.IDENTITY:
        assert "EXACT" in ref_roles.caption(role)
    assert ref_roles.caption("nonsense") == "" and ref_roles.caption("") == ""
    assert set(ref_roles.IDENTITY) | set(ref_roles.LOOK_ONLY) < set(ref_roles.ROLES)


def test_a_reference_with_no_role_reads_exactly_as_it_always_did():
    upload, face = "/refs/abc.jpg", "/characters/mara/photo/1.jpg"
    assert ref_roles.label(upload, None) == shootgen.reference_label(upload)
    assert ref_roles.label(face, {}) == shootgen.reference_label(face)
    assert ref_roles.label(face, {upload: "light"}) == shootgen.reference_label(face)
    # with one, the role outranks what the address says the picture is
    assert ref_roles.label(face, {face: "light"}) == ref_roles.caption("light")
    assert ref_roles.label(upload + "?thumb=1", {upload: "palette"}) == ref_roles.caption("palette")


def test_what_arrives_is_held_to_the_roles_there_are():
    raw = {"/refs/a.jpg": "Light", " /refs/b.jpg?thumb=1 ": "palette", "/refs/c.jpg": "vibes",
           "": "light", "/refs/d.jpg": 7, 3: "light"}
    assert ref_roles.clean(raw) == {"/refs/a.jpg": "light", "/refs/b.jpg": "palette"}
    # a form field is JSON text; nonsense is no roles, never an error
    assert ref_roles.clean(json.dumps({"/refs/a.jpg": "subject"})) == {"/refs/a.jpg": "subject"}
    for junk in ("", "not json", "[1, 2]", None, 5, ["light"]):
        assert ref_roles.clean(junk) == {}
    many = {f"/refs/{i}.jpg": "light" for i in range(40)}
    assert len(ref_roles.clean(many)) == ref_roles.MAX_ROLES


def test_a_picture_that_only_lends_its_look_is_never_first():
    refs = ["/refs/light.jpg", "/characters/mara/photo/1.jpg", "/refs/pal.jpg", "/props/can/photo/1.jpg"]
    roles = {"/refs/light.jpg": "light", "/refs/pal.jpg": "palette",
             "/props/can/photo/1.jpg": "product"}
    assert ref_roles.order(refs, roles) == [
        "/characters/mara/photo/1.jpg", "/props/can/photo/1.jpg", "/refs/light.jpg", "/refs/pal.jpg"]
    # with no look-only role the order is untouched (it is load-bearing)
    assert ref_roles.order(refs, {"/props/can/photo/1.jpg": "product"}) == refs
    assert ref_roles.order(refs, None) == refs
    # all look-only: still a stable list (there is no identity to promote)
    only = ["/refs/light.jpg", "/refs/pal.jpg"]
    assert ref_roles.order(only, roles) == only


def test_roles_are_stored_under_the_names_the_shot_keeps_its_refs_by():
    roles = {"https://pub.example/m/1/refs/a.jpg": "light", "/refs/b.jpg": "product"}
    rename = lambda ref: "/refs/a.jpg" if "a.jpg" in ref else ref     # noqa: E731
    named = ref_roles.rekey(roles, rename)
    assert named["/refs/a.jpg"] == "light" and named["/refs/b.jpg"] == "product"
    # and only for the references the shot actually carries
    assert ref_roles.for_refs(named, ["/refs/a.jpg"]) == {"/refs/a.jpg": "light"}
    assert ref_roles.for_refs(named, []) == {}
    # a renamer that fails keeps the role under the name it came with
    boom = lambda ref: (_ for _ in ()).throw(ValueError("no"))        # noqa: E731
    assert ref_roles.rekey({"/refs/b.jpg": "product"}, boom) == {"/refs/b.jpg": "product"}


def test_a_model_with_no_caption_slot_is_told_in_the_prompt_by_position():
    refs = ["/props/can/photo/1.jpg", "/refs/plain.jpg", "/refs/light.jpg"]
    said = ref_roles.prompt_note(refs, {"/props/can/photo/1.jpg": "product", "/refs/light.jpg": "light"})
    assert said.startswith("Reference image 1: the EXACT product")
    assert "Reference image 3: use ONLY its lighting" in said
    assert "Reference image 2" not in said          # no role, nothing claimed about it
    assert ref_roles.prompt_note(refs, {}) == "" and ref_roles.prompt_note([], None) == ""


def test_the_menu_is_the_table():
    menu = ref_roles.options()
    assert [m["id"] for m in menu] == list(ref_roles.ROLES)
    assert {m["id"] for m in menu if m["look_only"]} == set(ref_roles.LOOK_ONLY)
    assert all(m["label"] for m in menu)
