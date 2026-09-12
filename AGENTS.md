# AGENTS.md — Personal AI Quant Trading OS

Read `VIBE_CODING_MASTER.md` and the relevant `.ai/` files before making substantial changes.

Operating rules:
1. Inspect the existing repository before coding.
2. Do not duplicate existing functionality.
3. Plan changes before implementation.
4. Preserve backward compatibility unless a migration is intentional.
5. Never commit secrets or credentials.
6. Never use future market information in historical analysis.
7. Risk controls must remain independent from strategy/AI logic.
8. Do not remove or weaken tests to make CI pass.
9. Validate changes with appropriate tests.
10. Update project state and documentation after meaningful work.
11. Mark a task DONE only when its Definition of Done passes.
12. Never enable live trading merely because code exists; paper trading and explicit risk gates are prerequisites.
