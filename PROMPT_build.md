# PROMPT_build.md – Building Mode Instructions

You are in **building mode**.  Your job is to take the next actionable task from `IMPLEMENTATION_PLAN.md` and implement it.

## Tasks

1. **Select a task.**  Open `IMPLEMENTATION_PLAN.md` and choose the highest‑priority task that is not yet completed.  Read its acceptance criteria and estimated complexity.
2. **Implement the task.**  Modify or create the necessary files to satisfy the acceptance criteria.  Follow the specifications in the `specs/` directory and respect the core values (privacy, precision, no advice, separation of concerns)【980693054436426†L4-L19】.
3. **Validate your work.**  Run the commands listed in `AGENTS.md`:
   - Run unit tests (`pytest`), linting (`ruff check` or `flake8`), type checking (`mypy`) and any smoke tests relevant to the task.
   - If any command fails, fix the issue before proceeding.
4. **Update the plan.**  After finishing the task, update `IMPLEMENTATION_PLAN.md`:
   - Mark the task as completed (e.g., strike through or add a “Done” note).
   - Add any follow‑up tasks discovered during implementation.
5. **Commit and exit.**  Write a commit message referencing the task ID and describing the change.  Then exit build mode so the next iteration can begin.

## Constraints

* Implement **only one task per iteration**.  Do not scope creep.
* Do not modify unrelated files.
* Always run validation commands after coding.
* Ensure deterministic behaviour and adherence to data security principles.

Exit building mode after committing your changes and updating the plan.
