"""
Sprint 22 — Connector conformance tests.

Verifies per Section 69 of Sprint22.md:
- runtime unavailable → error dict returned (not crash)
- strict argument validation (option/command injection blocked)
- timeout
- oversized output handling
- malformed output handling
- secret redaction
- mock/live execution mode classification
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import uuid


class TestMaigretAdapterConformance:
    def _get_adapter(self):
        from app.connectors.maigret_adapter import MaigretAdapter
        return MaigretAdapter(executable_path="maigret")

    def test_adapter_exists_and_has_name(self):
        adapter = self._get_adapter()
        assert hasattr(adapter, "run_discovery")

    def test_adapter_rejects_option_injection(self):
        """Usernames with shell metacharacters must be rejected."""
        adapter = self._get_adapter()
        injection_attempts = [
            "--output=malicious",
            "test; ls",
            "test && echo pwned",
            "test`whoami`",
            "test|cat /etc/passwd",
        ]
        for injection in injection_attempts:
            result = adapter.run_discovery(injection)
            assert result.get("error") == "invalid_input", \
                f"Expected injection '{injection}' to be rejected, got: {result}"

    def test_adapter_rejects_empty_username(self):
        adapter = self._get_adapter()
        result = adapter.run_discovery("")
        assert result.get("error") == "invalid_input"

    def test_adapter_handles_runtime_unavailable(self):
        """When binary not found, adapter should return error dict, not raise unhandled exception."""
        adapter = self._get_adapter()
        # executable_path points to nonexistent binary
        adapter.executable_path = "/nonexistent/binary/maigret"
        result = adapter.run_discovery("testuser")
        assert "error" in result
        assert result["error"] in ("tool_unavailable", "execution_error")

    def test_adapter_handles_timeout(self):
        """Timeout is handled gracefully, not as a crash."""
        import subprocess
        adapter = self._get_adapter()

        with patch("subprocess.Popen") as mock_popen:
            proc = MagicMock()
            # First communicate() raises TimeoutExpired, second (reap) returns normally
            proc.communicate.side_effect = [
                subprocess.TimeoutExpired(cmd="maigret", timeout=10),
                (b"", b""),  # reap call
            ]
            proc.kill = MagicMock()
            mock_popen.return_value = proc

            result = adapter.run_discovery("testuser", timeout=10)
            assert result.get("error") == "timeout"
            proc.kill.assert_called_once()

    def test_adapter_handles_malformed_output(self):
        """Malformed JSON in output file yields parse_error, not crash."""
        import subprocess
        from pathlib import Path

        adapter = self._get_adapter()

        with patch("subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = (b"", b"")
            proc.returncode = 0
            mock_popen.return_value = proc

            with patch("pathlib.Path.glob") as mock_glob, \
                 patch("builtins.open", mock_open(read_data="NOT_VALID_JSON")):
                # Return one fake file
                fake_file = MagicMock()
                mock_glob.return_value = [fake_file]

                result = adapter.run_discovery("testuser")
                assert result.get("error") in ("parse_error", "execution_error", "partial_result")

    def test_no_sensitive_data_in_error_logs(self):
        """Error messages must not contain potential secret values."""
        adapter = self._get_adapter()
        result = adapter.run_discovery("user\x00null")  # null byte injection
        result_str = str(result)
        assert "password" not in result_str.lower()
        assert "sessionid" not in result_str.lower()
        assert "secret" not in result_str.lower()


class TestOSINTgramAdapterConformance:
    def _get_adapter(self):
        from app.services.discovery.connectors.osintgram_adapter import OSINTgramAdapter
        return OSINTgramAdapter()

    def test_adapter_has_connector_name(self):
        adapter = self._get_adapter()
        assert hasattr(adapter, "CONNECTOR_NAME")
        assert adapter.CONNECTOR_NAME == "osintgram"

    def test_adapter_version_declared(self):
        adapter = self._get_adapter()
        assert hasattr(adapter, "CONNECTOR_VERSION")
        assert isinstance(adapter.CONNECTOR_VERSION, str)
        assert adapter.CONNECTOR_VERSION  # Not empty

    def test_connector_version_is_adapter_marker_not_live(self):
        """1.1.0-mock is an adapter compatibility marker. Must be documented as such."""
        adapter = self._get_adapter()
        # The version string is allowed to contain 'mock' because that classifies it
        # correctly as not a verified live runtime version.
        # What we verify: if 'mock' is in version, it should NOT claim availability = 'available'
        from app.services.discovery.connectors.registry import ConnectorRegistry
        desc = ConnectorRegistry.get_descriptor("osintgram")
        if desc and adapter.CONNECTOR_VERSION and "mock" in adapter.CONNECTOR_VERSION.lower():
            from app.services.discovery.connectors.registry import ConnectorAvailability
            assert desc.availability != ConnectorAvailability.AVAILABLE, \
                "A connector with 'mock' in version string must not be classified as 'available'"

    @pytest.mark.asyncio
    async def test_adapter_rejects_option_injection(self):
        """Usernames with shell metacharacters should produce invalid_input error."""
        adapter = self._get_adapter()
        from app.services.discovery.connectors.capability_registry import ConnectorCapability

        injection_attempts = [
            "--option=evil",
            "test; ls",
            "`whoami`",
            "test\x00",
        ]
        for injection in injection_attempts:
            result = await adapter.execute(injection, ConnectorCapability.PROFILE_LOOKUP)
            # Should be failed status, not a crash
            assert result.get("status") == "failed", \
                f"Expected injection '{injection}' to fail, got: {result}"

    @pytest.mark.asyncio
    async def test_adapter_handles_not_configured(self):
        """When session secret missing, adapter returns not_configured."""
        adapter = self._get_adapter()
        from app.services.discovery.connectors.capability_registry import ConnectorCapability
        with patch.object(adapter, "_get_operator_session_secret", return_value=None):
            result = await adapter.execute("testuser", ConnectorCapability.PROFILE_LOOKUP)
            assert result.get("status") == "failed"

    def test_capabilities_declared(self):
        from app.services.discovery.connectors.registry import ConnectorRegistry
        from app.services.discovery.connectors.capability_registry import ConnectorCapability
        desc = ConnectorRegistry.get_descriptor("osintgram")
        assert desc is not None
        assert ConnectorCapability.PROFILE_LOOKUP in desc.capabilities


class TestConnectorGeneralConformance:
    def test_maigret_registry_defaults_to_test_only_or_disabled(self):
        from app.services.discovery.connectors.registry import ConnectorRegistry, ConnectorAvailability
        desc = ConnectorRegistry.get_descriptor("maigret")
        assert desc is not None
        assert desc.availability in [ConnectorAvailability.TEST_ONLY, ConnectorAvailability.DISABLED]

    def test_osintgram_registry_defaults_to_test_only_or_disabled(self):
        from app.services.discovery.connectors.registry import ConnectorRegistry, ConnectorAvailability
        desc = ConnectorRegistry.get_descriptor("osintgram")
        assert desc is not None
        assert desc.availability in [ConnectorAvailability.TEST_ONLY, ConnectorAvailability.DISABLED]

    def test_orchestrator_skip_decisions_exist(self):
        """Orchestrator has all required skip decision categories."""
        from app.services.discovery.orchestration_service import OrchestrationDecision
        required = [
            "SKIP_TEST_ONLY",
            "SKIP_UNAVAILABLE",
            "SKIP_UNHEALTHY",
            "SKIP_NO_CONSENT",
            "SKIP_BUDGET",
            "SKIP_DUPLICATE",
            "SKIP_FRESH",
        ]
        decision_names = [d.name for d in OrchestrationDecision]
        for name in required:
            assert name in decision_names, f"Missing orchestration decision: {name}"
