---
name: EcoTrace
description: A deforestation-risk score you can trace to its sources, set as a pre-printed bill of lading.
colors:
  paper: "#f2f2ee"
  paper-sunk: "#e8e8e1"
  ink: "#14181f"
  ink-secondary: "#434a55"
  ink-muted: "#5a616d"
  hairline: "#bdb8a8"
  form-vermilion: "#b73a18"
  stamp-blue: "#26407a"
  entry-white: "#ffffff"
typography:
  display:
    fontFamily: "Barlow Condensed, Arial Narrow, system-ui, sans-serif"
    fontSize: "clamp(2.5rem, 5.2vw, 4.25rem)"
    fontWeight: 600
    lineHeight: 0.95
    letterSpacing: "normal"
  score:
    fontFamily: "Barlow Condensed, Arial Narrow, system-ui, sans-serif"
    fontSize: "clamp(5.5rem, 11vw, 8.5rem)"
    fontWeight: 600
    lineHeight: 0.85
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Barlow, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: "Barlow, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Barlow Condensed, Arial Narrow, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0.1em"
rounded:
  none: "0px"
spacing:
  box-x: "18px"
  box-top: "14px"
  box-bottom: "18px"
  page-gutter: "24px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0 24px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.form-vermilion}"
  button-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 24px"
    height: "48px"
  entry-field:
    backgroundColor: "{colors.entry-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "14px 16px"
  stamp:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "3px 10px"
  chip:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "3px 10px"
---

# Design System: EcoTrace

## Overview

**Creative North Star: "The Bill of Lading"**

EcoTrace presents an assessment the way customs and shipping paperwork presents a consignment: one pre-printed sheet, numbered boxes, one answer per box, every entry traceable to its source. The score is the loudest entry on the sheet, and the evidence that earns it sits directly beneath. The world was chosen by the project owner from a rolled hand of directions and replaces the earlier dark glass-and-glow dashboard entirely.

The page is dense and quiet. Paper ground, one ink, and a single form-print vermilion that is reserved for box numbers and the one live answer. State is never carried by colour: it is a drawn mark plus a word, in the way a form uses a ticked box or a rubber stamp. Nothing floats, glows, blurs or casts a shadow.

**Key Characteristics:**
- One sheet of numbered boxes ruled in 1px ink, outer rule 1.5px.
- Vermilion appears only on box numbers, the score figure, and the scale pin.
- Risk level is a stamp whose border style (filled, double, single, dashed, dotted) and word both say the level.
- Evidence class is a square mark (filled, hollow, dashed) beside a word, never a colour.
- Square corners everywhere. No gradients, glass, glow or decorative motion.

## Colors

A single warm-neutral paper, near-black ink, and one vermilion. Everything else is a tint of the ink.

### Primary
- **Form Vermilion** (#b73a18): box numbers, the score figure, the scale pin, text selection, the hover fill of the primary button. 5.2:1 on paper.

### Secondary
- **Stamp Blue** (#26407a): links and the keyboard focus ring only.

### Neutral
- **Paper** (#f2f2ee): the page and every box.
- **Paper Sunk** (#e8e8e1): hover rows, disabled controls, region nodes in the graph.
- **Ink** (#14181f): text, rules, filled stamps, primary button.
- **Ink Secondary** (#434a55): lede and supporting text (7.8:1).
- **Ink Muted** (#5a616d): fine print and legends (5.6:1).
- **Hairline** (#bdb8a8): row separators inside a box, never a box edge.
- **Entry White** (#ffffff): the one place paper is overridden, the typing field.

### Named Rules
**The One Ink Rule.** Vermilion is for the entry a reader is meant to find first. If two things on a screen are vermilion, one is wrong.

**The No-Colour-Alone Rule.** Every state has a word and a drawn mark. Greyscale must lose nothing.

## Typography

**Display Font:** Barlow Condensed (with Arial Narrow, system-ui)
**Body Font:** Barlow (with system-ui)

**Character:** A condensed grotesque for labels and figures reads like pre-printed form type; the regular-width sibling carries running text at a comfortable measure. Numerals are tabular everywhere.

### Hierarchy
- **Display** (600, clamp(2.5rem, 5.2vw, 4.25rem), 0.95): home headline and the subject name.
- **Score** (600, clamp(5.5rem, 11vw, 8.5rem), 0.85): the one big figure.
- **Title** (600, 1.0625rem, 1.5): row and source names.
- **Body** (400, 1.0625rem, 1.6, max 68ch): summary and explanations.
- **Label** (600, 0.8125rem, 0.1em, uppercase): box labels, table heads, tags.

### Named Rules
**The Measure Rule.** Prose never runs wider than 68 to 76 characters, even inside a full-width box.

## Layout

A 12-column sheet inside a 1240px page with 24px gutters (16px under 720px). Boxes are grid cells separated by 1px ink rules; the sheet carries one 1.5px outer rule. Spans are 7+5 for text beside text, 5 for the score, 12 for tables. Below 900px every box is full width. Below 720px each table row becomes a small form: the first cell is the row heading, the others become label-and-value pairs.

Box numbers exist because text points at them ("Built from the pairs in Box 6"). Do not number a box nothing refers to on the same page.

## Elevation & Depth

Flat. Depth is expressed by rules, not shadows: a box is a ruled cell, a field is a white cell, the stamp is a bordered word. There are no shadows, blurs or layers anywhere.

### Named Rules
**The Ruled-Not-Raised Rule.** If something needs separating, rule it. Never lift it.

## Shapes

Square corners (0px). Borders are 1px ink for rules and chips, 1.5px for fields and outlined buttons, and the stamp varies its border to carry the risk level: filled (critical), 4px double (high), 1.5px solid (moderate), 1.5px dashed (low), 2px dotted (minimal).

## Components

### Buttons
- **Shape:** square (0px), 48px high, condensed uppercase label with 0.1em tracking.
- **Primary:** ink fill, paper text, 24px side padding. Hover fills vermilion. Disabled is paper-sunk with muted text.
- **Line:** transparent with a 1.5px ink border; hover inverts to ink.

### Chips
- **Style:** transparent, 1px ink border, 3px by 10px padding. The dashed variant marks "not scored".

### Inputs / Fields
- **Style:** white field, 1.5px ink border, 1.375rem text, 14px by 16px padding.
- **Focus:** 2px stamp-blue outline offset 2px, the same ring as every other control.

### Navigation
- **Style:** condensed uppercase links with a 2px underline; the current page's underline is vermilion. The export action is the one filled nav item.

### Stamp
The risk level as a bordered word. Sized up beside the score; the only entrance motion on the site is this stamp settling for 220ms (skipped under reduced motion).

### Evidence Mark
A 12px square: filled for trade records or confirmed sourcing, hollow for producer-country or estimated, dashed for inferred. Always followed by its word and explained in a legend under the table.

## Do's and Don'ts

### Do:
- **Do** put the evidence directly under the verdict and number every box that text refers to.
- **Do** say how old the data is and which sources are static (Trase, Forest 500) or live (Global Forest Watch).
- **Do** give every slow or failing request an honest message and a way out.
- **Do** keep a word beside every mark and every colour.

### Don't:
- **Don't** add gradients, glass, glow, blurred blobs, drop shadows or rounded cards.
- **Don't** use emoji or glyphs as icons; draw marks or use the icon library at one stroke weight.
- **Don't** print a number that was not checked against code or data, and never call static data live.
- **Don't** put a label above a heading as an eyebrow.
- **Don't** use vermilion for anything but box numbers, the score, and its pin.
