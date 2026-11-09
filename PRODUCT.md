# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, in this order of who opens it first:

1. **A recruiter or engineer** who lands on the live demo from a CV or GitHub and decides within ten seconds whether the work is real. Their job: judge whether this is a credible, explainable system built by someone who measures things.
2. **A sustainability or procurement analyst** who looks up a company or a commodity and needs to see where a deforestation-risk score comes from, how much to trust it, and how old the data is.

## Product Purpose

EcoTrace turns a company name or a commodity (for example Cargill, or Palm Oil) into a 0-100 deforestation-risk score for its supply chain, and shows the evidence behind it. Success is a visitor who can say what the score is made of after one look, not one who only sees a number.

## Positioning

The score is **explainable**: it is built only from evidence-backed commodity-country pairs, each with an Evidence label (trade records, or producer country). A neighbouring dashboard that shows a bare risk number could not truthfully copy that. Honesty about data age and coverage is part of the product.

## Operating Context

- Search takes a company name or a commodity category.
- Cached lookups answer in under a second; a new company takes roughly 8 to 31 seconds while sources are read.
- The API runs on a free host that sleeps when idle, so the first request can take about a minute longer. The UI must say so honestly and never freeze.
- Four sources feed the score: the company's own sustainability page (direct fetch, plus Jina Reader), Trase trade records, the Forest 500 policy ranking, and the live Global Forest Watch API.
- Trase and Forest 500 are **static datasets**. Only Global Forest Watch is queried live.

## Capabilities and Constraints

Must keep working:
- Search by company or commodity, recent searches (browser storage), suggestion shortcuts.
- Results: score, confidence, commodities, sourcing regions, summary, commodity-by-region breakdown with Evidence column, disclosure flags, operational presence (not scored), methodology note, data sources (including GFW coverage and the scraped-page link), supply-chain graph, "data as of" date, PDF export.
- Loading screen for slow lookups, error screen with retry.
- History page: lists past lookups, cache times read as UTC, click to reopen.

Verified facts safe to print: 15 commodities in the scoring model, 40 countries in the regional risk table, 4 data sources.

Not allowed: calling Trase or Forest 500 "real-time" or "live"; invented users, metrics, accuracy figures or sample companies; any number that was not checked against code or data.

Naming: the UI says **EcoTrace**. "Risk Engine" may appear as a descriptor.

## Brand Commitments

- Name: EcoTrace.
- The home page has **no stats row** (the user removed it).
- Purpose decision (user, 2026-11-09): a credible analyst tool where evidence and honesty lead. Not a visual showpiece.

## Evidence on Hand

- Live demo: https://eco-trace-risk-engine.vercel.app (frontend), API on Render.
- Real captured API responses for Cargill and Unilever, and the history list, used as local fixtures. No testimonials, user counts or traffic figures exist, and none may be invented.
- Repository: github.com/sahilsahu4102/EcoTrace-Risk-Engine.

## Product Principles

1. **Evidence before verdict.** The reason for a score sits next to the score, not at the bottom of the page.
2. **State the age and limits of the data in plain view**: data-as-of date, static versus live sources, coverage gaps.
3. **Honest waiting.** Slow lookups and a sleeping server get a clear explanation and a visible way out, never a frozen control.
4. **Nothing decorative that a number could replace.**
5. **Say only what was checked.**

## Accessibility & Inclusion

Meet WCAG AA contrast and visible keyboard focus. Do not carry meaning by colour alone: the risk level always has a word beside the colour. Respect `prefers-reduced-motion`. No horizontal page scroll at 390 px.
