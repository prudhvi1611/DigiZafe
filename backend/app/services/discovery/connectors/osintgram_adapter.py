import asyncio
import json
import logging
import os
import re
import signal
import tempfile
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.services.discovery.connectors.capability_registry import CapabilityRegistry, ConnectorCapability

logger = logging.getLogger(__name__)

def redact_secrets(text: str) -> str:
    """Redacts potential secrets like API keys or tokens from connector output."""
    if not text:
        return text
    # Simple regex to redact common secret patterns
    text = re.sub(r'(?i)(api_key|apikey|secret|token|password|key|sessionid)\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-\.\+]+)[\'"]?', r'\1=***REDACTED***', text)
    return text


class OSINTgramAdapter:
    """
    Adapter for running OSINTgram commands securely.
    Uses operator-managed session from environment.
    """
    
    CONNECTOR_NAME = "osintgram"
    CONNECTOR_VERSION = "1.1.0-mock" # Hardcoded pinned version for Sprint 19
    EXECUTABLE_PATH = "/usr/local/bin/osintgram" # Path to OSINTgram executable in container
    
    def __init__(self):
        self.settings = get_settings()

    def _validate_username(self, username: str) -> bool:
        """Validate Instagram username to prevent injection/options."""
        # Instagram usernames are 1-30 chars, letters, numbers, periods, underscores.
        if not re.match(r"^[a-zA-Z0-9._]{1,30}$", username):
            return False
        if username.startswith("-") or username.startswith("--"):
            return False
        return True
        
    def _get_operator_session_secret(self) -> str | None:
        """Retrieve the operator managed sessionid from environment."""
        return os.environ.get("OSINTGRAM_SESSION_ID")

    async def check_availability(self) -> str:
        """Return the connector status."""
        if not self.settings.feature_osintgram_discovery:
            return "disabled"
        if not self._get_operator_session_secret():
            return "not_configured"
        # Mock actual binary check for now
        return "available"

    async def execute(self, username: str, capability: ConnectorCapability) -> dict[str, Any]:
        """
        Execute OSINTgram safely with a bounded subprocess.
        """
        status = await self.check_availability()
        if status != "available":
            return {"status": "failed", "error": status, "error_category": "missing_dependency"}
            
        policy = CapabilityRegistry.get_policy(self.CONNECTOR_NAME, capability)
        if not policy or not policy.enabled:
            return {"status": "failed", "error": "capability_disabled", "error_category": "validation_failed"}
            
        if not self._validate_username(username):
            return {"status": "failed", "error": "invalid_input", "error_category": "validation_failed"}
            
        # Map capability to OSINTgram commands
        command_map = {
            ConnectorCapability.PROFILE_LOOKUP: "info",
            ConnectorCapability.PUBLIC_PROFILE_METADATA: "info",
            ConnectorCapability.EXTERNAL_LINKS: "info",
            ConnectorCapability.AVATAR_OBSERVATION: "info",
            ConnectorCapability.RELATIONSHIP_OBSERVATION: "fwer", # Mock command for followers
        }
        
        target_command = command_map.get(capability)
        if not target_command:
            return {"status": "failed", "error": "unsupported_capability", "error_category": "validation_failed"}

        # Construct safe explicit arguments
        # osintgram <username> -c <command> -j
        args = [
            self.EXECUTABLE_PATH,
            username,
            "-c", target_command,
            "-j" # request JSON output
        ]
        
        session_id = self._get_operator_session_secret()
        
        started_at = datetime.now(timezone.utc)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Minimal environment
            env = {
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "OSINTGRAM_SESSION_ID": session_id,
            }
            
            try:
                # Use asyncio.create_subprocess_exec to run shell=False
                process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=temp_dir,
                    env=env,
                    preexec_fn=os.setsid # Create a new process group
                )
                
                try:
                    # Hard timeout bound
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=policy.timeout
                    )
                except asyncio.TimeoutError:
                    # Process tree termination
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    return {"status": "failed", "error": "timeout", "error_category": "timeout", "started_at": started_at.isoformat()}

                # Enforce output limit on raw bytes
                if len(stdout) > policy.output_limit or len(stderr) > policy.output_limit:
                    return {"status": "failed", "error": "oversized_output", "error_category": "unexpected_output", "started_at": started_at.isoformat()}
                    
                if process.returncode != 0:
                    safe_stderr = redact_secrets(stderr.decode("utf-8", errors="ignore"))
                    logger.error(f"OSINTgram failed: {safe_stderr}")
                    return {"status": "failed", "error": "connector_error", "error_category": "execution_failed", "started_at": started_at.isoformat()}
                    
                raw_stdout = stdout.decode("utf-8", errors="ignore")
                
                # Parse JSON output robustly
                try:
                    parsed_output = json.loads(raw_stdout)
                except json.JSONDecodeError:
                    return {"status": "failed", "error": "malformed_output", "error_category": "unexpected_output", "started_at": started_at.isoformat()}

                    
                return {
                    "status": "completed",
                    "connector": self.CONNECTOR_NAME,
                    "connector_version": self.CONNECTOR_VERSION,
                    "capability": capability.value,
                    "observations": [parsed_output],
                    "started_at": started_at.isoformat(),
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }

            except Exception as e:
                logger.error("osintgram_execution_failed")
                return {"status": "failed", "error": "tool_unavailable", "error_category": "execution_failed", "started_at": started_at.isoformat()}
