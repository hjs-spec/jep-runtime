# JEP Runtime — local companion experiment

Create, archive and replay a **local runtime envelope** with declared delegation and termination rules. This package uses J/D/T/V vocabulary, normalized sorted JSON and mock signatures. It does not implement the current signed Core wire format.

For signed Core 0.7 events, use [Quickstart](https://github.com/hjs-spec/jep-quickstart), the [HTTP SDK/API](https://github.com/hjs-spec/.github/blob/main/PROJECTS.md#integrate), or the [local Agent SDK](https://github.com/hjs-spec/jep-agent-sdk).

## Install

```sh
python -m pip install --upgrade jep-runtime
jep-runtime --help
```

Since software 0.2 the command is `jep-runtime`; `jep` belongs to `jep-cli`. If 0.1 shared an environment with that CLI, upgrade this package first, then reinstall `jep-cli` to restore its command. Python imports and existing local-runtime archives remain unchanged.

## Use

```sh
jep-runtime create-event --type J --actor human:alice --subject agent:planner \
  --agent-id agent:planner \
  --scope-json '{"actions":["read"],"resources":["repo:jep"]}' \
  --intent-json '{"task":"summarize JEP"}' \
  --archive archive.jsonl

jep-runtime archive-verify archive.jsonl
jep-runtime replay archive.jsonl
jep-runtime conformance-test
```

`verify event.json` checks one runtime envelope. `conformance-test` checks this runtime's own profile, not JEP Core conformance. Replay reconstructs recorded state; it does not re-execute tools.

## Data contract

| Step | Local behavior |
|---|---|
| Create | Build a runtime `JEPEvent`, not a Core wire object |
| Hash | SHA-256 of normalized/sorted JSON excluding `event_hash`; not Core JCS |
| Link | `previous_event_hash` links supplied records |
| Delegate | Record `authority_scope` and `delegation_chain` |
| Archive | Append JSONL records |
| Verify/replay | Check local hashes, nonce uniqueness, links, delegation rules and supplied profile identity |

Fields such as `nonce`, `previous_event_hash`, `delegation_chain`, `authority_scope` and `verification_state` are local state. They are not mandatory Core fields. Existing archives keep their serialization; a future Core adapter must explicitly map formats and preserve original evidence.

## Policy boundary

The local profile binds a supplied credential reference to `event.actor` through `ProfileAdapter.resolve_identity`; lookup failures fail closed. Delegation helpers take the delegating actor's credential reference rather than copying a parent's credential.

Within a session, this profile treats `T` as ending a subject's authority, including observed descendant delegations. Later use or re-grant is rejected; `V` evidence may still be recorded. A new session has independent state. These are local rules. Deployment policy must independently establish who may grant or terminate authority.

Signatures and OAuth/OIDC, X509, DID/VC and IAM adapters are mock/reference implementations. Hash consistency does not authenticate a signer or prove a complete history, and declared scope does not establish real-world authority.

## Source map

| Directory | Responsibility |
|---|---|
| `jep_runtime/core`, `events`, `schemas` | Local envelope and factories |
| `canonicalization`, `verification` under `jep_runtime` | Local encoding, hashing and checks |
| `delegation`, `profiles` under `jep_runtime` | Local policy and mock identity adapters |
| `archive`, `replay`, `conformance`, `cli` under `jep_runtime` | Storage, replay, profile checks and command |
| `examples`, `tests` | Scenarios and regression checks |

See [HARDENING.md](HARDENING.md) for implementation limits and [the ecosystem format matrix](https://github.com/hjs-spec/jep-core/blob/main/docs/architecture/architecture-notes.md#format-and-verification-matrix) before combining packages.
