# Release 0.3.1

Align the reference runtime boundary with JEP Core 0.7.

- JEP Core target is 0.7 / Internet-Draft -07.
- The runtime event model is explicitly a companion runtime envelope, not the
  JEP Core wire object.
- Runtime nonce, previous-event hash, delegation chain, authority scope, and
  termination cascade remain runtime/profile mechanisms rather than Core
  requirements.
- Signed JEP Core 0.7 wire events should be produced and verified through the
  current SDK/API path.
- Historical runtime archive bytes and runtime-specific behavior remain
  readable; this release does not rewrite old archives.
