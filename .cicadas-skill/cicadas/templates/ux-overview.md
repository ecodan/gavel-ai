
# UX Overview

> Canon document. Updated by the Synthesis agent at the close of each initiative.

## Design Direction

**Style:** {e.g., Minimal / Terminal / Conversational / Data-dense / Bold}
**Voice & tone:** {How the product speaks — e.g., "Direct and technical, never patronizing"}
**Primary platform:** {Web / CLI / Mobile / Desktop / API}
**Existing design system:** {Name of system followed, or "None — product-specific"}

---

## Navigation Model

**Top-level structure:**

```
{Top Level}
├── {Section A}
│   ├── {Sub-section 1}
│   └── {Sub-section 2}
├── {Section B}
└── {Section C}
```

**Navigation pattern:** {Tab bar / Sidebar / Command palette / Top nav / None}
**Key entry points:** {Landing / Onboarding / Dashboard / Direct deep link}
**Active state:** {How users know where they are in the nav}

---

## UX Consistency Patterns

{Shared interaction patterns across the product. New work must follow or explicitly evolve these.}

### Feedback

| Event | Pattern |
|-------|---------|
| **Success** | {e.g., Toast notification, top-right, 3s auto-dismiss} |
| **Error** | {e.g., Inline below affected field + toast for system errors} |
| **Warning** | {e.g., Banner above affected content} |
| **Loading** | {e.g., Skeleton for content areas, spinner for inline actions} |

### Actions & Buttons

- **Primary action:** {e.g., One filled button per screen, brand color}
- **Secondary action:** {e.g., Outlined, multiple allowed}
- **Destructive action:** {e.g., Red variant, always requires confirmation dialog}

### Forms

- **Validation timing:** {On blur / On submit / Real-time}
- **Error placement:** {Below each field / Summary at top}
- **Required fields:** {Marked with * / All optional explicit}

### Empty States

{e.g., "Always provide an illustration + headline + CTA — never just 'No data'"}

### Modals & Overlays

- **When used:** {e.g., Confirmation dialogs, short forms — not for browsing content}
- **Dismissal:** {Click outside / ESC key / Explicit close button}

---

## Accessibility

**Standard:** {WCAG 2.1 AA / AA+ / N/A}
**Keyboard navigation:** {Full / Partial / N/A}
**Screen reader support:** {Required / Optional / N/A}
**Color contrast:** {AA minimum / AAA}
**Touch targets:** {44×44px minimum on mobile / N/A}
**Reduced motion:** {Respected via `prefers-reduced-motion` / N/A}

---

## Responsive Breakpoints

| Breakpoint | Width | Layout |
|-----------|-------|--------|
| Mobile | {< Xpx} | {Single col / stacked nav} |
| Tablet | {X–Ypx} | {…} |
| Desktop | {> Ypx} | {…} |

---

## Copy & Tone

**Voice:** {e.g., "Direct, confident, never condescending — explain what happened, not what the user did wrong"}

**Key copy patterns:**

| Context | Approach |
|---------|---------|
| CTAs | {e.g., Active verbs: "Create plan", not "Submit"} |
| Error messages | {e.g., Say what failed + how to fix it, never blame the user} |
| Empty states | {e.g., Inviting, not neutral — prompt the user toward action} |
| Success confirmations | {e.g., Brief confirmation + next logical action} |

---

## Open Questions

{Unresolved UX decisions that affect future initiatives.}

- {Question} — {Owner / urgency}

