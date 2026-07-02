# Project Sentinel website — design QA

## Reference comparison

- Source captured at `https://ponytail.dev/` in desktop and mobile states.
- Preserved the reference's terminal framing, monospace hierarchy, hard-edged controls, restrained accent palette, and compressed mobile layout.
- Replaced all source identity and content with Sentinel-specific evidence, controls, and case storytelling.

## Functional checks

- Production build completes successfully with Vite.
- Detection-layer tabs update score, threshold, explanation, selection state, and progress.
- Light/dark theme toggle updates the full token system and its accessible label.
- CASE_001 graph opens in a modal and closes by button, backdrop, or Escape.
- Anchor navigation and external repository/document links are populated.
- Copy command has a native clipboard action.

## Responsive and accessibility checks

- Mobile hero, proof strip, layer console, graph, control cards, and footer collapse without horizontal page overflow.
- Semantic headings, tab roles, dialog role, live region, focus-visible states, and descriptive image alternative text are present.
- Animation is disabled under `prefers-reduced-motion`.
- Text and controls retain high contrast in both themes.

## Content checks

- Uses repository-backed CASE_001 values only.
- Demo scale is explicitly labeled synthetic.
- No production efficacy, savings, or ROI claims are presented.
- Footer states that this is not a Walmart system.

final result: passed
