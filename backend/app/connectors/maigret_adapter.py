import json
import logging
import re
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Basic protections against shell metacharacters and control characters
def is_safe_username(username: str) -> bool:
    if not username or len(username) > 100:
        return False
    # Block leading dashes (flag injection)
    if username.startswith("-"):
        return False
    # Only allow typical username characters (alphanumeric, -, _, .)
    # Block anything that could be interpreted by a shell even if shell=False
    if re.search(r"[;|<>&$\n\r\t\"'`\x00]", username):
        return False
    return True

def redact_secrets(text: str) -> str:
    """Redacts potential secrets like API keys or tokens from connector output."""
    if not text:
        return text
    # Simple regex to redact common secret patterns
    text = re.sub(r'(?i)(api_key|apikey|secret|token|password|key)\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-\.\+]+)[\'"]?', r'\1=***REDACTED***', text)
    return text

class MaigretAdapter:
    """
    Adapter for Maigret OSINT execution.
    Enforces strict execution boundaries, timeouts, and structure parsing.
    """

    def __init__(self, executable_path: str = "maigret"):
        self.executable_path = executable_path

    def run_discovery(self, username: str, timeout: int = 180) -> dict[str, Any]:
        """
        Executes Maigret boundedly.
        Returns a dictionary of structured results or raises an exception/error payload.
        """
        if not is_safe_username(username):
            return {"error": "invalid_input", "error_category": "validation_failed", "message": "Username failed safety constraints."}

        # We use a temporary directory to store the JSON output so we don't parse unpredictable stdout
        with tempfile.TemporaryDirectory() as tmpdir:
            json_report_path = Path(tmpdir) / "report.json"
            
            args = [
                self.executable_path,
                username,
                "--json",
                str(json_report_path.parent), # maigret writes to the dir with specific filename or we can rename
                "-a", # all sites
                "--timeout", "10", # internal request timeout
                "--retries", "1"
            ]

            try:
                # We specifically avoid shell=True
                # We bind stdout and stderr so they don't pollute our main logs or consume unbounded memory
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=tmpdir,
                )

                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate() # Reap
                    return {"error": "timeout", "error_category": "timeout", "message": f"Execution exceeded {timeout} seconds."}

                # Find the generated json file since maigret names it like report_{username}.json
                # Actually --json DIR puts report_{username}.json inside DIR.
                generated_files = list(Path(tmpdir).glob("*.json"))
                if not generated_files:
                    if process.returncode != 0:
                        safe_stderr = redact_secrets(stderr.decode('utf-8', errors='ignore'))
                        logger.error(f"Maigret failed: {safe_stderr}")
                        return {"error": "execution_error", "error_category": "execution_failed", "message": "Maigret failed to produce output."}
                    return {"error": "partial_result", "error_category": "unexpected_output", "message": "No JSON report found."}
                
                report_file = generated_files[0]
                with open(report_file, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        return {"error": "parse_error", "error_category": "unexpected_output", "message": "Failed to parse Maigret JSON."}

                return {"status": "success", "data": data}

            except FileNotFoundError:
                return {"error": "tool_unavailable", "error_category": "missing_dependency", "message": "Maigret executable not found."}
            except Exception as e:
                logger.exception("Unexpected error in MaigretAdapter")
                return {"error": "execution_error", "error_category": "execution_failed", "message": "Unexpected error occurred."}
