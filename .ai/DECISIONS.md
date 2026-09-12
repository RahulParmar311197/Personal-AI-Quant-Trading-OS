# Architecture Decisions

## ADR-0001 — Framework is canonical
Status: Accepted

The numbered project framework and `.ai` governance structure are the canonical organization for this project. Implementation must fit inside it rather than replacing it with a competing repository layout.

## ADR-0002 — Modular monolith first
Status: Accepted

Start as a modular monolith with explicit domain boundaries. Split services only when scale, reliability, deployment or ownership requirements justify it.

## ADR-0003 — Risk is independent
Status: Accepted

Strategy and AI components produce evidence/signals; an independent Risk Engine determines whether an order is permitted.

## ADR-0004 — Live trading disabled by default
Status: Accepted

Development, research and paper trading must not enable real-money execution. Production execution requires explicit acceptance gates.
