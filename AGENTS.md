# Project Rules (Codex / GPT)

This file defines hard constraints and working conventions for this repo. Prefer `.cursor/rules/*.mdc` for prompt/style guidance and keep this file focused on engineering constraints.

## Non-negotiable response format
- Always respond in Simplified Chinese.
- Every assistant message must start with:
  1) `【当前的model】`
  2) `亲爱的Wang`

## Scope / Allowed changes
- Allowed: modify backend (Flask) code, add new mini program pages, add new backend endpoints, refactor code for maintainability.
- Default: do not change DB schema unless explicitly requested. If a feature requires schema change, propose an alternative first.
- Keep compatibility: mini program and web must share the same data and semantics for favorites/mistakes/user_answers/user_progress/exams.

## Coding style and structure
- Keep changes minimal and targeted; avoid unrelated refactors.
- Prefer modular design: avoid giant files; split by domain/service/util where appropriate.
- Follow existing project patterns and naming; do not introduce new frameworks unless explicitly requested.

### Backend (Flask)
- Use existing Blueprint/module layout under `app/modules/**`.
- New endpoints must be backward compatible and return stable JSON contracts.
- Authentication:
  - Mini program uses JWT `Authorization: Bearer <token>`.
  - Web may use session; endpoints used by both must support both (use existing `auth_required/current_user_id` helpers).
- Security: validate inputs; never trust query/body blindly.

### Mini program (WeChat)
- Page structure: `pages/<name>/<name>.{ts,wxml,less,json}`.
- Layout rule: fixed top nav + (if present) fixed bottom action area; content scroll only when overflow (no full-page scroll by default).
- Cards must be responsive and fill available width; avoid overlapping; prefer flex/grid with `min-width:0` and `box-sizing:border-box`.
- Avoid global CSS that breaks per-page layout; if adding global styles, keep them neutral.

## UI rules (high priority)
- iOS 18 minimal aesthetic: monochrome (white/light gray), no vivid colors or strong gradients.
- Soft rounded corners, subtle shadows, glassmorphism where appropriate.
- Use whitespace; keep typography clean.

## When requirements are unclear
- Ask a short clarification question before implementing.
