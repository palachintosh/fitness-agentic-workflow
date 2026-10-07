---
name: fitness-html-theme-builder
description: Render an already approved fitness-plan candidate as consistent standalone, accessible, responsive, and printable HTML. Use only for presentation after approval; never change fitness content.
---

# Fitness HTML Theme Builder

Render the supplied approved candidate into one self-contained HTML5 document.
This skill controls presentation only. Preserve the candidate's meaning and
omit its hidden workflow metadata.

## Fixed Document Shell

Use this semantic structure, omitting a section only when its corresponding
approved content is absent:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><!-- descriptive plan title --></title>
  <style>/* all styles live here */</style>
</head>
<body>
  <header class="hero"><div class="container"><!-- title and overview --></div></header>
  <main id="main-content" class="container">
    <section class="callout safety" aria-labelledby="safety-heading"><!-- safety --></section>
    <section><!-- how to use --></section>
    <section><!-- weekly schedule --></section>
    <section><!-- complete session cards --></section>
    <section><!-- progression and missed training --></section>
    <section><!-- tracking template --></section>
    <section><!-- equipment and setup --></section>
    <section><!-- stop and guidance conditions --></section>
    <section><!-- sources --></section>
    <section><!-- approved assumptions and limitations --></section>
  </main>
  <footer class="container"><!-- concise general-information notice --></footer>
</body>
</html>
```

Keep exactly one visible `h1`, use correctly nested headings, and give sections
stable human-readable IDs when navigation links are useful. Never display run
IDs, artifact paths, agent names, gates, retries, approval mechanics, or hidden
metadata.

## Visual System

- Use a centered `.container` no wider than `72rem`, a system font stack,
  generous line height, and a restrained dark-green/neutral palette.
- Define repeated colors, spacing, borders, and radii as CSS custom properties.
- Present sessions as consistent cards. Keep safety information visually
  distinct with both a label and border or icon-like text, never color alone.
- Keep body text left-aligned and readable; avoid decorative gradients,
  animations, dense dashboards, remote fonts, images, and scripts.
- Preserve visible source URLs in print using `a[href]::after` inside the print
  stylesheet. Links must open normally; do not force a new tab.

## Tables and Small Screens

Use semantic `table`, `thead`, `tbody`, `th scope="col"`, and where appropriate
`th scope="row"`. Wrap wide tables in a focusable container with horizontal
overflow and an accessible label. At narrow widths, reduce spacing without
hiding columns or converting labeled values into ambiguous blocks.

Every interactive element needs a visible `:focus-visible` outline. Maintain
sufficient contrast and do not communicate status by color alone.

## Print Rules

Print with a white background and dark text. Remove decorative shadows, keep
URLs visible, and avoid page breaks inside session cards, table rows, headings,
and safety callouts when practical. Do not hide substantive content when
printing.

## Rendering Invariants

- Copy every approved exercise, set, repetition or duration, rest period,
  intensity, substitution, progression rule, safety statement, tracking field,
  and source URL without semantic change.
- Do not add advice, claims, exercises, sources, JavaScript, external
  stylesheets, remote assets, or analytics.
- Do not render empty placeholders or the workflow-metadata comment.
- Keep the document usable without a network connection except when a reader
  chooses to follow a cited source link.
- If the candidate cannot be rendered faithfully, stop instead of repairing its
  fitness content.

Before completion, read the saved HTML and verify the document shell, heading
hierarchy, session IDs, exercise names, source URLs, table headers, print rules,
absence of placeholders and internal filenames, and absence of scripts or
remote assets.
