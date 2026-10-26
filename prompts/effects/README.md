# Recipe effects (src/effect_recipes.py)

One file per recipe: the prompt a recipe effect sends to its video model with the person's photo.
A file is the prompt, then optionally two sections:

    ---detail---   one line with {note}: what the person typed into the optional box, worked in
    ---default---  what stands in {detail} when they typed nothing

`{detail}` in the prompt is replaced by the detail line (or the default, or nothing). These are
our own words: never paste another product's prompt.
