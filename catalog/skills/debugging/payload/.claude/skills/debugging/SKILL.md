---
name: debugging
description: Systematic debugging workflow (reproduce, isolate, hypothesize, fix, add a regression test). Use when investigating a bug, an error, a stack trace, a failing test or unexpected behaviour.
---

# Debugging

Find the cause before changing code. Guessing fixes wastes time and hides bugs.

## 1. Reproduce

- Get an exact, repeatable reproduction: the command, input, and observed output.
- Capture the full error and stack trace. Read it from the bottom frame that is project code.
- If you cannot reproduce it, say so and gather more information instead of patching blindly.

## 2. Isolate

- Shrink the reproduction: smallest input, single test, single request.
- Bisect when the cause is unclear: comment out halves, check `git log -p` on the touched area, or use `git bisect` for regressions.
- Check assumptions explicitly with logging or a debugger rather than reading code and guessing.

## 3. Hypothesize and verify

- State one hypothesis at a time: "X fails because Y is None when Z".
- Design a check that would prove it wrong. Run it.
- Only move on to a fix when the evidence supports the hypothesis.

## 4. Fix the cause

- Fix the root cause, not the symptom. Catching and ignoring an exception is not a fix.
- Keep the fix minimal and local. Separate unrelated cleanup into its own change.
- If the fix requires a destructive or irreversible step (data migration, reset), stop and ask first.

## 5. Prove it

- Add a regression test that fails without the fix and passes with it.
- Run the narrow test, then the relevant suite.
- Remove temporary logging and debug code before finishing.

## Report

Summarize: the cause, the evidence, the fix, and the test that now protects it. If anything stays uncertain, say what and why.
