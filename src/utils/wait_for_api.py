import time
import urllib.request


def wait_for_api(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except OSError:
            time.sleep(0.2)

    raise RuntimeError("API did not become ready in time")