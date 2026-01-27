# PROMPT_plan.md – Planning Mode Instructions

You are in **planning mode**.  Your job is to produce or refresh `IMPLEMENTATION_PLAN.md` based on the latest specifications and code.

## Tasks

1. **Read the specs.**  Parse all documents in the `specs/` directory, `PRD.md`, and any existing code to understand the current state of the project.  Pay special attention to core values: privacy, precision, no financial advice, separation of concerns【980693054436426†L4-L19】.
2. **Perform a gap analysis.**  Identify which requirements in the specs are not yet implemented or require revision.  Group them by epic and story as appropriate.
3. **Update `IMPLEMENTATION_PLAN.md`.**  Add new epics, stories or tasks as needed and mark completed tasks if the code satisfies their acceptance criteria.  Ensure each task has acceptance criteria, file hints and complexity estimates.  Maintain the numbering sequence (e.g., TT‑101 follows the last task ID).
4. **Commit changes.**  Write updated content to `IMPLEMENTATION_PLAN.md` and exit.  Do not modify any code in planning mode.

## Constraints

* Do not implement code in this mode.
* Keep the plan clear and actionable.  Each task should be small enough to complete in a single iteration (max 2–3 hours of work).
* Do not remove tasks unless they are obviously obsolete; instead mark them completed with a note.

Exit planning mode by writing the updated plan and stopping execution.
