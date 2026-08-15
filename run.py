"""Application entry point."""

import subprocess
import sys
import time

from fastapi import FastAPI

from configuration.application import ApplicationSettings
from configuration.fastapi import FastapiSettings
from utils.fastapi_lifespan import lifespan
from utils.import_router import import_router
from utils.wait_for_api import wait_for_api
from utils.check_port_availability import require_configured_ports_available


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    service_name = FastapiSettings.get_settings().service_name
    app_version = ApplicationSettings.get_settings().app_version

    app = FastAPI(
        title=service_name,
        version=app_version,
        lifespan=lifespan,
    )
    import_router(app)

    return app


def _uvicorn_command(settings: ApplicationSettings) -> list[str]:
    """Build the explicit Uvicorn API-server command."""

    uvicorn_startup = (
        "import uvicorn; "
        "uvicorn.run("
        "'run:app', "
        f"host={settings.host!r}, "
        f"port={settings.port!r}, "
        f"reload={settings.reload!r}, "
        "log_config=None"
        ")"
    )
    return [sys.executable, "-c", uvicorn_startup]


def _streamlit_command(settings: ApplicationSettings) -> list[str]:
    """Build the explicit Streamlit client-server command."""

    client_path = settings.project_root / "src" / "client" / "app.py"
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(client_path),
        "--global.developmentMode",
        str(settings.streamlit_development_mode).lower(),
        "--server.address",
        settings.streamlit_host,
        "--server.port",
        str(settings.streamlit_port),
        "--server.headless",
        str(settings.streamlit_headless).lower(),
        "--browser.gatherUsageStats",
        str(settings.streamlit_gather_usage_stats).lower(),
    ]





def _stop_processes(processes: tuple[subprocess.Popen[bytes], ...]) -> None:
    """Stop and reap every running child process."""

    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        process.wait()


def _start_processes(
    settings: ApplicationSettings,
) -> tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]]:
    """Start one API process and one Streamlit client process."""

    require_configured_ports_available(settings)

    uvicorn_process = subprocess.Popen(
        _uvicorn_command(settings)
        )
    try:
        wait_for_api(
            url=ApplicationSettings.get_settings().api_health_endpoint,
            timeout=ApplicationSettings.get_settings().health_check_timeout
        )
        print("ConciergeAI API ready")
        streamlit_process = subprocess.Popen(
            _streamlit_command(settings),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    except BaseException:
        _stop_processes((uvicorn_process,))
        raise
    return uvicorn_process, streamlit_process


def main() -> None:
    """Supervise the FastAPI application and Streamlit client together."""
    settings = ApplicationSettings.get_settings()
    processes: tuple[subprocess.Popen[bytes], ...] = ()

    try:
        while True:
            processes = _start_processes(settings)
            while all(process.poll() is None for process in processes):
                time.sleep(0.5)

            _stop_processes(processes)
            processes = ()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        _stop_processes(processes)


app = create_app()


if __name__ == "__main__":
    main()
