"""Identity-neutral, credential-neutral profile adapter interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Mapping


class ProfileAdapter(Protocol):
    def issue_reference(self, actor: str, profile: str, claims: Mapping[str, Any] | None = None) -> str: ...
    def verify_reference(self, reference: str, profile: str) -> bool: ...
    def resolve_identity(self, reference: str) -> str: ...
    def validate_authority(self, reference: str, authority_scope: Mapping[str, Any]) -> bool: ...


@dataclass
class MockProfileAdapter:
    """Reference profile adapter for OAuth/OIDC, X509, DID/VC, and Local IAM labels.

    It performs deterministic reference checks only; it is not a production
    credential verifier and intentionally hardcodes no identity provider.
    """

    supported_profiles: tuple[str, ...] = ("mock", "oauth-oidc", "x509", "did-vc", "local-iam")

    def issue_reference(self, actor: str, profile: str = "mock", claims: Mapping[str, Any] | None = None) -> str:
        if profile not in self.supported_profiles:
            raise ValueError(f"unsupported profile: {profile}")
        return f"jep-ref:{profile}:{actor}"

    def verify_reference(self, reference: str | None, profile: str) -> bool:
        return bool(reference and profile in self.supported_profiles and reference.startswith(f"jep-ref:{profile}:"))

    def resolve_identity(self, reference: str) -> str:
        return reference.split(":", 2)[-1]

    def validate_authority(self, reference: str, authority_scope: Mapping[str, Any]) -> bool:
        return bool(reference and isinstance(authority_scope, Mapping))
