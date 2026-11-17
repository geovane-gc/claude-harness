---
name: principle-encode-lessons-in-structure
description: "Apply when a correction or an instruction you write could be enforced by a check. Encode the rule as a lint, metadata flag, runtime check, or script instead of more text."
disable-model-invocation: true
---

# Encode Lessons in Structure

A lesson a check can enforce gets the check the first time it is corrected, not after it repeats.

**Corollary:** If the fix is structural, only use the structural fix. The instruction is the symptom.

If the lesson needs judgment and cannot be encoded, make the instruction more prominent.
