# Model logos

One-colour logos the studio's model pickers show beside each model
(`src/components/studio/model-pins.tsx`, `logoFor`). They are drawn with CSS
`mask`, so they take the tile's colour.

Source: LobeHub Icons, `@lobehub/icons-static-svg` 1.102.0 (MIT), copied
unchanged. The marks themselves belong to their companies; they are used here
only to name which model a person is picking.

To add one: copy the plain (not `-color`, not `-text`) SVG into this folder
and add a rule to `logoFor`.
