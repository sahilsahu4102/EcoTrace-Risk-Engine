---
version: 1
slug: "frontend-src-app-page-tsx"
primary_target: "frontend/src/app/page.tsx"
related_targets: ["frontend/src/app/results/[company]/page.tsx","frontend/src/app/history/page.tsx"]
---

# EcoTrace: home, results, history

Mode: Read (with an Operate search step). Visitor: a recruiter or engineer deciding in ten seconds whether the work is real; second, an analyst checking where a score comes from. Task: look up a company or commodity, understand the score and its evidence, judge how far to trust it. Constraints: nothing printed that was not verified; Trase and Forest 500 are static datasets; slow and sleeping-server states shown honestly; PDF export, retry, history, loading screen stay.

## Direction contract

THESIS: The result is a pre-printed form, not a dashboard. Numbered boxes hold one answer each, and the evidence sits in the box next to the verdict. It refuses the glass-card metric grid with a glowing gauge.

OWN-WORLD: Paper ground (#F2F2EE), ink (#14181F), one form-print vermilion (#B73A18) used only for box numbers and the single live answer, stamp blue (#26407A) for links and static-source marks, hairline rules (#BDB8A8). Barlow Condensed for box labels, Barlow Semi Condensed for entries, tabular numerals. Square corners, 1px ink rules between boxes, no shadows, no glass, no gradients. State is a drawn mark plus a word: filled, double, single, dashed and dotted stamp borders for the five risk levels; solid, hollow and dashed squares for evidence classes.

STORY: The visitor sees what the score is made of before they scroll: the number, its confidence, the evidence table and the data's age. They believe it because every row names its source and the gaps are stated. They then search another company, open history, or export the PDF.

FIRST VIEWPORT: Home: masthead rule (EcoTrace, History) over a two-column form. Left, Box 1 "Company or commodity" as a large ruled entry line with a Run assessment button, examples beneath in two ruled lists (companies, commodities) and recent searches. Right, "How the score is built": the four sources with a plain static/live label each, and a server status line. Results: title and data-as-of line, then one ruled sheet: Box 2 score at 5 columns, confidence, commodities and regions boxes beside it, then the summary, then the Basis table with Evidence as its third column.

FORM: Bill of Lading (assigned, index 7 of the grounded list), seed key bbdf40fd.

SIGNATURE: When a result loads, the risk-level stamp is pressed onto the form once (a 200 ms settle, skipped under reduced motion). Nothing else animates on entry.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
