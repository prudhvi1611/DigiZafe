import hashlib
import json

class RuntimeFingerprintService:
    @staticmethod
    def generate_fingerprint(
        connector_type: str,
        adapter_version: str,
        runtime_version: str | None,
        runtime_revision: str | None,
        parser_version: str | None,
        conformance_policy_version: int | None
    ) -> str:
        """
        Generates a deterministic SHA256 fingerprint for a connector's runtime configuration.
        """
        data = {
            "connector_type": connector_type,
            "adapter_version": adapter_version,
            "runtime_version": runtime_version,
            "runtime_revision": runtime_revision,
            "parser_version": parser_version,
            "conformance_policy_version": conformance_policy_version
        }
        
        # Ensure all None values are converted to explicitly clear strings for hashing,
        # and sort keys to maintain determinism.
        clean_data = {k: (v if v is not None else "") for k, v in data.items()}
        
        payload = json.dumps(clean_data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
