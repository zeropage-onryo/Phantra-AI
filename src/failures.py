"""A render that did not happen, said in words a person can act on (2026-10-10).

Seen on the live composer that day: a still's tile reading

    image render skipped: HTTP Error 403: Forbidden -- {"detail":"User is
    locked. Reason: Exhausted balance. Top up your balance at
    fal.ai/dashboard/billing."}

under a step card that said Done. Every word of that is the PROVIDER
talking to the OPERATOR: it names a vendor the customer never chose, and
tells them to top up an account that is not theirs -- while the thing they
want to know (was I charged? what do I do?) goes unsaid.

`plain` is the one place a provider's error becomes a customer's sentence.
It is deliberately small: a handful of causes a person can act on
differently, and one honest fallback. The raw error is never lost -- the
adapters write it on the generations row, and the caller logs it -- it is
only kept off the page.

"Nothing was charged" is a statement of fact here, not reassurance: every
adapter holds credits before it submits and RELEASES the hold when the
submit or the job fails (src/charge.py), and a refusal for an empty balance
or a daily cap happens before any hold at all.
"""
from __future__ import annotations

import re

NOT_CHARGED = "Nothing was charged."

# Sentences this studio wrote itself (charge.refusal, generative.cap_error,
# the adapters' "no key" notes): already plain, already about the person's
# own account, passed through untouched.
_OURS = re.compile(r"(?i)^out of credits\b|top up to continue|\btoday\b.*\b(cap|limit)\b|"
                   r"\b(cap|limit)\b.*\btoday\b|subscribe or top up|"
                   # the trial whose included writing is used up
                   # (charge.TRIAL_THINKING_REFUSAL)
                   r"subscribe to keep going|"
                   # a message that already says what was charged (effects.run
                   # after its settle, run_voice's "made and paid for") is never
                   # told "Nothing was charged" (QA 2026-11-02 E5)
                   r"\bwas charged\b|\bpaid for\b")

_CAUSES = (
    # the provider turned the STUDIO away: its key, its balance, its account
    (re.compile(r"(?i)exhausted balance|user is locked|insufficient[_ ]quota|billing|"
                r"payment required|\b40[123]\b|unauthori[sz]ed|forbidden|invalid api key|"
                r"no \w+ key|key\b.*\b(not set|unset)|not configured"),
     "{service} turned the studio away. That is ours to fix, not yours"),
    (re.compile(r"(?i)\b429\b|rate.?limit|too many requests|resource_exhausted|overloaded"),
     "{service} is busy. Try again in a minute"),
    # Seedance refusing a real person's photo as a reference (2026-11-02,
    # src/people_refs.py): rewording the prompt cannot help, a model can
    (re.compile(r"(?i)likeness(es)? of real people|partner_validation"),
     "{model} won't take a photo of a real person as a reference. Render this shot on "
     "Kling 4.0 or Veo 3.1 instead"),
    (re.compile(r"(?i)content.?policy|safety|nsfw|moderat|prohibited|blocked by|"
                r"flagged as sensitive"),
     "{model} declined this prompt. Reword it and try again"),
    (re.compile(r"(?i)timed? ?out|\b50[0234]\b|unavailable|connection|temporar"),
     "{service} did not answer. Try again"),
)

# what is said for each thing that can fail to be made
_NOUNS = {"The clip": ("the video service", "the video model"),
          "The effect": ("the effects service", "the model"),
          "The talking photo": ("the video service", "the video model"),
          "The voice": ("the voice service", "the voice model"),
          "The voiceover": ("the voice service", "the voice model"),
          "The music": ("the music service", "the music model")}
_DEFAULT_NOUNS = ("the image service", "the image model")


def plain(raw, what: str = "The still") -> str:
    """`raw` (an adapter's error text) as one sentence for the page.

    `what` names the thing that was not made ("The still", "The clip").
    A message this studio wrote itself comes back as it is.
    """
    text = " ".join(str(raw or "").split())
    if not text:
        return f"{what} was not made. {NOT_CHARGED}"
    if _OURS.search(text):
        return text
    service, model = _NOUNS.get(what, _DEFAULT_NOUNS)
    for pattern, cause in _CAUSES:
        if pattern.search(text):
            said = cause.format(service=service, model=model)
            return f"{what} was not made: {said}. {NOT_CHARGED}"
    return f"{what} was not made: {service} reported an error. {NOT_CHARGED}"


class Refusal(ValueError):
    """A caller error with a code a client can branch on (QA 2026-11-02 K9).

    Still a ValueError with the same sentence, so every `except ValueError`
    and every message a test matches is unchanged; the connector puts
    `code` on the tool's error result (`mcp_server.refusal_code`), so a
    client tells `needs_reference` from `not_found` from an outage without
    reading the words."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
