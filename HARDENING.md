# Scope attenuation and archive integrity

Delegated capabilities must be explicitly present in the parent. Child scopes cannot omit a parent's expiry or other constraints, and expiration is exclusive. Delegation checks resolve the declared parent hash, actor, session, and complete ancestry rather than assuming the preceding log entry is the authority parent.

Non-mock profiles require a concrete adapter and credential. Mock checks are reported with profile_checked=false. The profile-neutral core does not itself supply OAuth/X509/DID authority verification.

Archive appends use a file lock and reject corrupt hashes, stale tails, and duplicate identifiers before writing. This is the local runtime envelope, not the JEP-Core wire schema. Tests cover scope escalation, expiry omission, unrelated intervening events, and credential boundaries.
