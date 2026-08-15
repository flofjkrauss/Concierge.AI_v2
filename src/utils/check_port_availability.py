"""Check if the ports configuret in ApplicationSettings are available on this system"""
import errno
import socket
import sys

from configuration.application import ApplicationSettings


def _reserve_port(host: str, port: int) -> socket.socket:
    """Temporarily reserve one configured server address."""

    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    reservation = socket.socket(family, socket.SOCK_STREAM)

    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            reservation.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_EXCLUSIVEADDRUSE,
                1,
            )
        reservation.bind((host, port))
    except BaseException:
        reservation.close()
        raise

    return reservation


def require_configured_ports_available(
    settings: ApplicationSettings,
) -> None:
    """Exit immediately when an API or client address cannot be bound."""

    endpoints = (
        ("API", settings.host, settings.port),
        ("client", settings.streamlit_host, settings.streamlit_port),
    )
    reservations: list[socket.socket] = []
    failures: list[tuple[str, str, int, OSError]] = []

    try:
        for service, host, port in endpoints:
            try:
                reservations.append(_reserve_port(host, port))
            except OSError as error:
                failures.append((service, host, port, error))
    finally:
        for reservation in reservations:
            reservation.close()

    if not failures:
        return

    print("ConciergeAI cannot start because a configured port is unavailable.", file=sys.stderr)
    for service, host, port, bind_error in failures:
        address = f"{host}:{port}"
        if (
            bind_error.errno == errno.EADDRINUSE
            or getattr(bind_error, "winerror", None) == 10048
        ):
            reason = "is already in use"
        else:
            reason = f"cannot be bound ({bind_error})"
        print(f"- {service} port {address} {reason}.", file=sys.stderr)
    print(
        "Stop the process using the port or configure a different port.",
        file=sys.stderr,
    )
    raise SystemExit(1)