"""Internal subprocess entrypoint. Parent supplies only a snapshot path and validated code."""

import builtins
import json
import math
import os
import resource
import sys

import numpy as np
import pandas as pd
from scipy import stats

from dataset_investigator.data.serialization import serialize_result
from dataset_investigator.execution.validator import SAFE_BUILTINS, validate_code


def main():
    # Validated code is at most 8,000 characters; UTF-8 needs up to four bytes each.
    payload = json.loads(sys.stdin.buffer.read(64_000).decode("utf-8"))
    timeout = max(1, math.ceil(payload["timeout"]))
    resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    # Linux supports address-space limits; macOS uses parent RSS monitoring instead.
    if sys.platform.startswith("linux"):
        memory = payload["memory_mb"] * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    # Prime the public reshape path before closing imports; crosstab imports it lazily.
    pd.crosstab(pd.Series(["a"]), pd.Series(["b"]))
    pd.DataFrame({"value": [1]}).to_dict()
    source = pd.read_parquet(payload["snapshot"])
    df = source.copy(deep=True)
    del source
    tree = validate_code(payload["code"])

    def deny_external_events(event, args):
        if event in {
            "open",
            "os.system",
            "os.posix_spawn",
            "os.fork",
            "os.forkpty",
            "subprocess.Popen",
            "ctypes.dlopen",
            "import",
            "os.remove",
            "os.rename",
            "os.mkdir",
            "os.rmdir",
            "os.chmod",
            "os.truncate",
        } or event.startswith(("socket.", "shutil.", "winreg.")):
            raise PermissionError(
                f"Restricted runtime event: {event}"
                + (f" ({args[0]})" if event == "import" else "")
            )

    # Compile trusted AST before the hook; it also checks allowed code inside the child.
    compiled = compile(tree, "<analysis>", "exec")
    sys.addaudithook(deny_external_events)
    env = {
        "__builtins__": {name: getattr(builtins, name) for name in SAFE_BUILTINS},
        "df": df,
        "pd": pd,
        "np": np,
        "stats": stats,
    }
    try:
        exec(compiled, env, env)
        if "result" not in env:
            raise ValueError("The analysis did not assign result.")
        result = {"ok": True, "summary": serialize_result(env["result"])}
    except BaseException as exc:
        result = {
            "ok": False,
            "error": f"{type(exc).__name__}: {str(exc)[:1000]}. Available columns: {', '.join(map(str, df.columns[:40]))[:1800]}",
        }
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_bytes = peak_rss if sys.platform == "darwin" else peak_rss * 1024
    if peak_bytes > payload["memory_mb"] * 1024 * 1024:
        result = {"ok": False, "error": "Python execution exceeded the worker memory limit."}
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.flush()
    # Avoid library atexit callbacks after the audit gate has closed.
    os._exit(0)


if __name__ == "__main__":
    main()
