"""Code Executor Executor for running generated code in conda environment."""

import os
import subprocess
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class ResourceUsage:
    """Resource usage statistics."""

    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0

    def update(self):
        """Update resource usage stats."""
        if not PSUTIL_AVAILABLE:
            return

        try:
            process = psutil.Process()
            self.cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            self.memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            self.memory_percent = process.memory_percent()
            self.peak_memory_mb = max(self.peak_memory_mb, self.memory_mb)
            self.peak_cpu_percent = max(self.peak_cpu_percent, self.cpu_percent)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "memory_percent": self.memory_percent,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_cpu_percent": self.peak_cpu_percent,
        }


@dataclass
class ExecutorConfig:
    """Configuration for code executor."""

    conda_env_name: str = "py12pt"
    timeout: int = 300  # seconds
    max_retries: int = 3
    capture_output: bool = True
    monitor_resources: bool = PSUTIL_AVAILABLE
    resource_check_interval: float = 1.0  # seconds


class CodeExecutor:
    """Executor for running Python code in specified conda environment."""

    def __init__(self, config: Optional[ExecutorConfig] = None):
        """Initialize code executor.

        Args:
            config: Optional executor configuration
        """
        self.config = config or ExecutorConfig()
        self._check_conda_availability()

    def _check_conda_availability(self):
        """Check if conda is available."""
        try:
            result = subprocess.run(
                ["conda", "--version"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError("Conda not found. Please ensure conda is installed and available.")
        except FileNotFoundError:
            raise RuntimeError("Conda command not found. Please ensure conda is installed in PATH.")

    def _check_env_exists(self) -> bool:
        """Check if specified conda environment exists."""
        try:
            result = subprocess.run(
                ["conda", "env", "list", "--json"],
                capture_output=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False

            envs = json.loads(result.stdout.decode())
            env_names = [Path(env).name for env in envs["envs"]]

            return self.config.conda_env_name in env_names
        except Exception:
            return False

    def run_command(
        self,
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, str, Dict[str, Any]]:
        """Run a command in conda environment.

        Args:
            command: Command to execute (list of strings)
            cwd: Working directory
            env: Additional environment variables

        Returns:
            Tuple of (return_code, stdout, stderr, resource_stats)
        """
        # Prefix with conda environment activation
        full_command = self._build_conda_command(command)

        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        # Initialize resource monitoring
        resource_usage = ResourceUsage() if self.config.monitor_resources else None

        try:
            process = subprocess.Popen(
                full_command,
                cwd=cwd,
                env=process_env,
                stdout=subprocess.PIPE if self.config.capture_output else None,
                stderr=subprocess.PIPE if self.config.capture_output else None,
                text=True,
            )

            # Monitor resources while running
            start_time = time.time()
            while process.poll() is None:
                if resource_usage:
                    resource_usage.update()
                if time.time() - start_time > self.config.timeout:
                    process.kill()
                    return (
                        -1,
                        "",
                        f"Command timed out after {self.config.timeout} seconds",
                        resource_usage.to_dict() if resource_usage else {}
                    )
                time.sleep(self.config.resource_check_interval)

            stdout = process.stdout.read() if process.stdout else ""
            stderr = process.stderr.read() if process.stderr else ""

            return (
                process.returncode,
                stdout,
                stderr,
                resource_usage.to_dict() if resource_usage else {}
            )

        except subprocess.TimeoutExpired:
            return (
                -1,
                "",
                f"Command timed out after {self.config.timeout} seconds",
                resource_usage.to_dict() if resource_usage else {}
            )
        except Exception as e:
            return (
                -1,
                "",
                f"Command execution failed: {str(e)}",
                resource_usage.to_dict() if resource_usage else {}
            )

    def _build_conda_command(self, command: List[str]) -> List[str]:
        """Build command with conda environment activation.

        Args:
            command: Original command

        Returns:
            Command list with conda activation
        """
        # Check if environment exists
        if not self._check_env_exists():
            raise RuntimeError(
                f"Conda environment '{self.config.conda_env_name}' not found. "
                f"Please create it first with: conda create -n {self.config.conda_env_name} python=3.12"
            )

        # Different activation command for different shells
        shell = os.getenv("SHELL", "")
        if "bash" in shell or "zsh" in shell:
            return [
                "bash", "-c",
                f"source $(conda info --base)/etc/profile.d/conda.sh && "
                f"conda activate {self.config.conda_env_name} && "
                f"{' '.join(command)}"
            ]
        elif "fish" in shell:
            return [
                "fish", "-c",
                f"source (conda info --base)/etc/fish/conf.d/conda.fish && "
                f"conda activate {self.config.conda_env_name} && "
                f"{' '.join(command)}"
            ]
        else:
            # Fallback: use conda run
            return ["conda", "run", "-n", self.config.conda_env_name] + command

    def run_python_script(
        self,
        script_path: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run a Python script in conda environment.

        Args:
            script_path: Path to Python script
            args: Additional command line arguments
            cwd: Working directory (default: script's directory)

        Returns:
            Dictionary with execution results:
            - success: bool
            - return_code: int
            - stdout: str
            - stderr: str
            - execution_time: float
            - resource_stats: dict
        """
        if not os.path.exists(script_path):
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": f"Script not found: {script_path}",
                "execution_time": 0.0,
                "resource_stats": {},
            }

        # Default to script's directory if no cwd provided
        if cwd is None:
            cwd = os.path.dirname(script_path)

        command = ["python", os.path.basename(script_path)]
        if args:
            command.extend(args)

        start_time = time.time()
        return_code, stdout, stderr, resource_stats = self.run_command(command, cwd=cwd)
        execution_time = time.time() - start_time

        return {
            "success": return_code == 0,
            "return_code": return_code,
            "stdout": stdout,
            "stderr": stderr,
            "execution_time": execution_time,
            "resource_stats": resource_stats,
        }

    def install_dependencies(
        self,
        requirements: List[str],
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Install Python packages in conda environment.

        Args:
            requirements: List of package names or requirements file path
            cwd: Working directory

        Returns:
            Execution result dictionary
        """
        if not requirements:
            return {
                "success": True,
                "message": "No dependencies to install",
            }

        # Check if it's a requirements file
        if len(requirements) == 1 and requirements[0].endswith(".txt"):
            req_file = requirements[0]
            if not os.path.exists(req_file):
                return {
                    "success": False,
                    "message": f"Requirements file not found: {req_file}",
                }
            command = ["pip", "install", "-r", req_file]
        else:
            command = ["pip", "install"] + requirements

        return_code, stdout, stderr, resource_stats = self.run_command(command, cwd=cwd)

        return {
            "success": return_code == 0,
            "stdout": stdout,
            "stderr": stderr,
            "resource_stats": resource_stats,
        }

    def execute_generated_code(
        self,
        code_dir: str,
        entry_point: str = "main.py",
        args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute generated code in specified directory.

        Args:
            code_dir: Directory containing generated code
            entry_point: Entry point script name
            args: Additional arguments

        Returns:
            Detailed execution report
        """
        if not os.path.exists(code_dir):
            return {
                "success": False,
                "status": "failed",
                "error": f"Code directory not found: {code_dir}",
                "execution_time": 0.0,
                "resource_stats": {},
            }

        # Look for requirements.txt and install dependencies
        req_file = os.path.join(code_dir, "requirements.txt")
        if os.path.exists(req_file):
            install_result = self.install_dependencies([req_file], cwd=code_dir)
            if not install_result["success"]:
                return {
                    "success": False,
                    "status": "failed",
                    "error": f"Failed to install dependencies: {install_result['stderr']}",
                    "execution_time": 0.0,
                    "resource_stats": install_result.get("resource_stats", {}),
                }

        # Run entry point
        entry_path = os.path.join(code_dir, entry_point)
        if not os.path.exists(entry_path):
            return {
                "success": False,
                "status": "failed",
                "error": f"Entry point not found: {entry_path}",
                "execution_time": 0.0,
                "resource_stats": {},
            }

        result = self.run_python_script(entry_path, args=args, cwd=code_dir)

        status = "success" if result["success"] else "failed"

        return {
            "success": result["success"],
            "status": status,
            "return_code": result["return_code"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "execution_time": result["execution_time"],
            "resource_stats": result.get("resource_stats", {}),
        }
