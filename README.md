# JEP Reference Runtime

`jep-runtime` is a runnable reference implementation for the Judgment Event Protocol (JEP). It currently targets **JEP Internet-Draft v06** (the `jep-v06` repository baseline). It turns the v06 JEP primitives — Judgment (`J`), Delegation (`D`), Termination (`T`), and Verification (`V`) — into executable accountability semantics: create an event, canonicalize it, hash it, chain it, archive it, replay it, and verify it across neutral profile adapters.

This repository is intentionally **not** an agent framework, workflow orchestrator, blockchain, consensus layer, payment executor, or production security system. Mock signatures and mock credential references are provided so protocol semantics can be tested before deployment-specific cryptography is plugged in.

## Protocol version target

This reference runtime is pinned to **JEP Internet-Draft v06** / the `jep-v06` repository baseline. The runtime exposes this as package metadata via `jep_runtime.JEP_DRAFT_VERSION == "jep-v06"` and includes the same value in conformance reports.

The implementation intentionally preserves the v06 meanings of Judgment (`J`), Delegation (`D`), Termination (`T`), and Verification (`V`) events. Future draft revisions should be added as explicit schema/profile adapters or compatibility layers rather than silently changing the v06 runtime semantics.

## Architecture

```text
+-------------------+      +------------------------+      +------------------+
| Event Runtime     | ---> | Canonicalization       | ---> | SHA-256 Hashing  |
| J / D / T / V     |      | UTF-8 sorted JSON      |      | event_hash       |
+---------+---------+      +-----------+------------+      +---------+--------+
          |                            |                             |
          v                            v                             v
+-------------------+      +------------------------+      +------------------+
| Delegation        | ---> | Append-only Archive    | ---> | Verification     |
| scoped authority  |      | JSONL import/export    |      | chain/replay     |
+---------+---------+      +-----------+------------+      +---------+--------+
          |                            |                             |
          v                            v                             v
+-------------------+      +------------------------+      +------------------+
| Profile Adapters  | ---> | Replay Engine          | ---> | Conformance      |
| OAuth/X509/DID/IAM|      | lineage graph/state    |      | vectors/report   |
+-------------------+      +------------------------+      +------------------+
```

## Runtime data flow

1. A caller creates a `JEPEvent` with the required core fields.
2. The event is canonicalized as normalized UTF-8 JSON with stable field ordering and no insignificant whitespace.
3. `event_hash = SHA256(canonical_event_without_event_hash)` is assigned once; changing a hashed event requires creating a new event.
4. New events reference `previous_event_hash`, producing an append-only event chain.
5. Delegation events carry bounded `authority_scope` and `delegation_chain` entries so authority lineage can be replayed.
6. JSONL archives append one canonical event record per line.
7. Verification recomputes hashes, validates nonce uniqueness, checks hash continuity, validates delegation scope, and invokes the configured neutral profile adapter.

## Replay flow

```text
archive.jsonl
   |
   v
import events -> verify entire chain -> replay J/D/T/V semantics
   |                  |                    |
   |                  |                    +--> termination_state
   |                  +--> tamper/nonce/profile/delegation errors
   +--> lineage_graph: hash-chain edges + delegation edges
```

Run it with:

```bash
jep replay archive.jsonl
```

The replay output is a portable event lineage graph plus authority and termination state. It is evidence reconstruction, not workflow execution.

## CLI

```bash
jep create-event --type J --actor human:alice --subject agent:planner \
  --agent-id agent:planner \
  --scope-json '{"actions":["read"],"resources":["repo:jep"]}' \
  --intent-json '{"task":"summarize JEP"}' \
  --archive archive.jsonl

jep verify event.json
jep archive-verify archive.jsonl
jep replay archive.jsonl
jep conformance-test
```

## Conformance matrix

| Capability | Runtime check |
| --- | --- |
| Canonicalization | Stable UTF-8 JSON with sorted keys and normalized strings |
| Deterministic hashing | SHA-256 over canonical event without `event_hash` |
| Delegation semantics | Parent/child scope and expiration checks |
| Verification semantics | Hash, nonce, timestamp, profile, and chain integrity checks |
| Profile compatibility | Neutral `ProfileAdapter` contract with mock OAuth/OIDC, X509, DID/VC, Local IAM labels |
| Replay correctness | Archive replay must re-verify the full chain and emit lineage graph/state |

`jep conformance-test` emits test vectors, mock signed vectors, and a compatibility report.

## Correspondence with the JEP draft

| Draft primitive / concept | Runtime implementation |
| --- | --- |
| `J` Judgment | `EventType.JUDGMENT` and `create_event("J", ...)` |
| `D` Delegation | `delegate_authority()`, scoped delegation events, `verify_delegation_chain()` |
| `T` Termination | `EventType.TERMINATION`, replayed into `termination_state` |
| `V` Verification | `verify_event()`, `verify_chain()`, `verify_replay()`, verification events |
| Replay protection | Required `nonce` and duplicate nonce validation |
| Signed/verifiable event format | Immutable hashed event model plus mock profile references |
| Optional profiles | `ProfileAdapter` interface; provider-neutral mock adapter |
| Append-only receipts | JSONL archive with chain verification on replay |

## Repository structure

```text
jep_runtime/
  core/                 # immutable event model and JSON schema generation
  events/               # event factories
  canonicalization/     # deterministic JSON + SHA-256 hashing
  delegation/           # authority propagation and scope validation
  verification/         # event, chain, replay, tamper, profile verification
  profiles/             # provider-neutral profile adapter interface and mock adapter
  archive/              # append-only JSONL archive runtime
  replay/               # lineage graph and termination replay
  conformance/          # conformance vectors and matrix
  cli/                  # jep command line entry point
  schemas/              # generated JSON schema
examples/               # example event scenarios
tests/                  # executable conformance/runtime tests
```

## Limitations

- Signatures are mock/reference only.
- Profile adapters do not verify real OAuth/OIDC, X509, DID/VC, or IAM credentials.
- No blockchain, distributed consensus, real payment execution, or production key management is included.
- The runtime enforces executable protocol invariants, not legal liability, governance policy, or workflow lifecycle orchestration.

## Runtime governance extension points

- Replace `MockProfileAdapter` with production credential adapters.
- Add signature suites while preserving the canonicalization boundary.
- Add draft-version-specific schema adapters without changing the pinned v06 J/D/T/V primitive meaning.
- Publish conformance vectors for independent implementations.
- Add governance-specific validation modules outside the core minimal runtime.
