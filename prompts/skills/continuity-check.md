---
name: continuity-check
title: Continuity check
for: check a scene's shots against the elements it uses, before anything is rendered
output: video
order: 100
---
# Continuity check

Every shot in a scene is rendered by a model that has never seen the others. Anything not written into each shot drifts: a jacket changes colour, a product loses its label, a room changes shape. This check reads the scene before it is rendered, while fixing it is free.

## What to read

The scene's brief or prompt in this conversation, and the elements the grounding names -- their names, what they are, and what their photos and reference sheets show. Only check against what is actually there; never invent a detail an element does not have.

## Check every shot for

1. The subject. Each person, product or place in the shot is named and locked as the EXACT one from its reference photos -- not re-described in new words.
2. Wardrobe and props. The same clothes and the same objects from shot to shot, unless the story changes them on purpose.
3. Place and light. The same room, the same time of day, light from the same side.
4. Screen direction. Someone moving left to right keeps moving left to right across the cut.
5. Scale and count. The same number of people and objects; the product the same size in the hand.
6. The look line and the avoid list ride on every shot, not only the first.

## Say what you found

A short list, one line per problem: the shot, what drifts, and the fix in words. For example: "Shot 3 -- the prompt says a red scarf; Maya's photos show a grey one. Use EXACT clothing from her photos." When nothing drifts, say so in one line.

When a person or product has photos but no reference sheet, say once that a sheet would hold them steadier across shots, and offer make_element_sheet for a person -- it is the person's click that draws it.

## Hand it over

Offer to rewrite the scene with the fixes. Rewriting is free; rendering is not, and only happens on the scene's own Render card. When they say yes, write the corrected prompt into `brief` and, only if they asked for it to be made, call make_video with it.

## Check before you send

Every problem names a shot? Every fix is checkable against a photo? Nothing invented about an element?
