import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

import psutil

from ..config import Settings
from .validator import CodeRejected, validate_code

log = logging.getLogger(__name__)


async def execute_python(code: str, snapshot: Path, settings: Settings) -> dict:
    try:
        validate_code(code)
    except CodeRejected as exc:
        return {"ok": False, "error": f"Code rejected: {exc}"}
    with tempfile.TemporaryDirectory(prefix="investigator-worker-") as directory:
        # -I ignores user PYTHONPATH/site packages. The installed project is importable via uv.
        environment = {
            "PATH": os.defpath,
            "HOME": directory,
            "TMPDIR": directory,
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-m",
            "dataset_investigator.execution.worker",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=directory,
            env=environment,
            start_new_session=True,
        )
        payload = json.dumps(
            {
                "code": code,
                "snapshot": str(snapshot.resolve()),
                "timeout": settings.agent_code_timeout_seconds,
                "memory_mb": settings.worker_memory_mb,
            }
        ).encode()
        communication = asyncio.create_task(process.communicate(payload))
        start = time.monotonic()
        monitor = psutil.Process(process.pid)
        failure = None
        try:
            while not communication.done():
                elapsed = time.monotonic() - start
                if elapsed >= settings.agent_code_timeout_seconds:
                    failure = f"Python execution timed out after {settings.agent_code_timeout_seconds:g} seconds. Reduce the analysis size."
                    break
                try:
                    if monitor.memory_info().rss > settings.worker_memory_mb * 1024 * 1024:
                        failure = "Python execution exceeded the worker memory limit. Use a smaller analysis."
                        break
                except psutil.NoSuchProcess:
                    pass
                await asyncio.wait(
                    {communication},
                    timeout=min(0.05, max(0.001, settings.agent_code_timeout_seconds - elapsed)),
                )
            if failure:
                process.kill()
            stdout, stderr = await communication
            if failure:
                return {"ok": False, "error": failure}
            if process.returncode != 0:
                log.warning("Worker exited code=%s", process.returncode)
                return {
                    "ok": False,
                    "error": "The analysis worker stopped unexpectedly or exceeded a resource limit. Try a smaller analysis.",
                }
            try:
                output = json.loads(stdout)
                if not isinstance(output, dict) or "ok" not in output:
                    raise ValueError("Invalid output")
                return output
            except (ValueError, UnicodeDecodeError):
                return {"ok": False, "error": "The analysis worker returned an invalid result."}
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
            if not communication.done():
                communication.cancel()
                try:
                    await communication
                except asyncio.CancelledError:
                    pass
