# Orchestrated Plan-or-Debug

**Task:** $ARGUMENTS

---

## 1. Classify Intent

Determine which path to take by reading the task description:

- **DEBUG** → Mentions regression, error, bug, failing test, unexpected behavior, or stack trace.
- **RESEARCH / NEW FEATURE** → Mentions net-new functionality, API schema changes, GraphQL additions, new UI/flows.
- **DEBUG + RESEARCH (Hybrid)** → Requires both tracing a defect AND researching/introducing patterns or designs outside the immediate bug area.
- **AMBIGUOUS** → Ask 1–2 clarifying questions before proceeding.

---

## 2. DEBUG Path

1. **Investigate**
   - Trace code paths, imports, types, logs, tests, and recent diffs.
   - Identify and isolate failure points.
2. **Summarize**
   - Current state of relevant code.
   - Most recent fix, if any, and its observed result.
   - The specific issue description, repro steps, and key evidence (logs, stack trace).
3. **Hypothesize**
   - Present best 2–3 working hypotheses.
4. **Recommend Next Steps**
   - List 3 prioritized debugging actions with file-level pointers.
5. **Restriction**
   - **Do not implement** in this step — plan only.

---

## 3. RESEARCH / NEW FEATURE Path

1. **Requirements**
   - Derive requirements from task.
2. **Plan**
   - Propose a plan that matches existing conventions.
   - Include:
     - API/GraphQL schema deltas (Pothos)
     - Prisma model deltas
     - Frontend impact outline
3. **Options**
   - Present 2–3 possible approaches with trade‑offs.
4. **Recommendation**
   - Choose and justify the best path.

---

## 4. DEBUG + RESEARCH (Hybrid) Path

1. **Investigate the Bug**  
   - Trace imports, functions, output if provided, and anything else mentioned.
   - Isolate root cause.
2. **Research for Fix**  
   - Identify if missing implementation of known pattern or feature.
   - Search codebase for correct patterns and solutions.
   - Web search/library docs for any unfamiliar APIs or best practices.
3. **Synthesize**
   - Merge debug findings and research into a single recommended fix plan that matches conventions.
4. **Deliver**
   - Provide:
     - Consolidated fix plan
     - File/method pointers
     - External references
     - Minimal step list to implement

---

## 5. Always

- Output should be:
  1. Intent classification decision
  2. Step‑by‑step plan (per chosen path)
  3. Next steps checklist
- **No code edits in this step** — planning and investigation only.
