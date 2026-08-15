from typing import Any


class CanonicalFactService:
    """
    Service responsible for defining canonical fact keys, detecting fact equivalence,
    and resolving material changes.
    """

    @classmethod
    def generate_profile_existence_key(cls, platform: str, canonical_url: str) -> str:
        return f"profile_existence:{platform}:{canonical_url}"

    @classmethod
    def generate_username_key(cls, platform: str, canonical_username: str) -> str:
        return f"username:{platform}:{canonical_username}"

    @classmethod
    def generate_external_link_key(cls, source_profile_url: str, canonical_target_url: str) -> str:
        return f"external_link:{source_profile_url}:{canonical_target_url}"

    @classmethod
    def generate_avatar_key(cls, candidate_id: str, fingerprint: str) -> str:
        return f"avatar_fingerprint:{candidate_id}:{fingerprint}"

    @classmethod
    def generate_cross_link_key(cls, source_canonical_url: str, target_canonical_url: str) -> str:
        return f"cross_link:{source_canonical_url}:{target_canonical_url}"

    @classmethod
    def is_materially_changed(
        cls, old_payload: dict[str, Any] | None, new_payload: dict[str, Any] | None
    ) -> bool:
        """
        Determine if the new observation payload represents a material change 
        from the old observation payload.
        """
        # In a more complex system, this would compare specific keys.
        # For now, strict dictionary equality is sufficient.
        return old_payload != new_payload
