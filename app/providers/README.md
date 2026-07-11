# providers (stub — Phase 3)

Owns: the `SourceProvider` capability interfaces and one adapter per external
source, plus rate limiting, retries, and compliance flags.

Never: writes to the database (returns DTOs only).

No adapter may be implemented until its Provider Access Spike record in
`docs/providers/` concludes `usable` or an accepted `paid_option`
(FOUNDATION.md §8.1).
