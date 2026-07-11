# scoring (stub — Phase 5)

Owns: deterministic score computation. Every score row stores the observation
IDs and formula version used; missing inputs produce `null` plus a reason.

Never: calls LLMs or invents numbers.
