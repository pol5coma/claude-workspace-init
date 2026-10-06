---
name: testing
description: Run the smallest relevant test scope first, then widen only when needed. Use when writing, changing, or verifying tests, when a change needs verification, or when tests fail.
---

# Testing

Verify changes with the narrowest test scope that proves them, then widen deliberately.

## Workflow

1. **Find the relevant tests.** List candidate tests for the files you changed:

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/relevant-tests.py"            # uses git diff
   python3 "${CLAUDE_SKILL_DIR}/scripts/relevant-tests.py" src/api/users.py
   ```

   It prints matching test files and the command to run them. It never runs tests itself.

2. **Run the narrow scope first.** One file, one test, or one keyword:
   - pytest: `pytest path/to/test_file.py::test_name -x -q`
   - Vitest: `npx vitest run path/to/file.test.ts -t "name"`
   - Jest: `npx jest path/to/file.test.ts -t "name"`
   - Go: `go test ./pkg/... -run TestName`

   Prefer the project's own commands from CLAUDE.md (for example `uv run pytest`) over bare tool names.

3. **Widen only when the narrow scope passes** and the change touches shared code (models, utilities, config, public interfaces). Run the module's suite, then the full suite before declaring a cross-cutting change done.

4. **Report honestly.** State which scope you ran and its result. Never claim the suite passes if you ran a subset.

## Writing tests

- Test behaviour through public interfaces, not private helpers.
- One reason to fail per test. Name tests after the behaviour they protect.
- Add a regression test for every bug fix: it must fail before the fix and pass after.
- Prefer real objects and in-memory fakes over deep mocking. Mock only process boundaries (network, clock, randomness, external services).
- Keep fixtures small and local to the test unless they are reused widely.
- Never weaken an assertion, add a skip, or delete a test to make a failure disappear. If a test is genuinely wrong, say why before changing it.

## When tests fail

- Read the first failure fully before changing code. Later failures are often consequences.
- Reproduce with the narrowest command, then fix the cause, not the symptom.
- Flaky test? Re-run it once in isolation. If it flips, report it as flaky rather than retrying until green.
