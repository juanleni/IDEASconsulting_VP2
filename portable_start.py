import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def find_free_port(start: int = 8501, end: int = 8599) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No se encontró un puerto libre entre 8501 y 8599.")


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    app_path = base_dir / "IDEASapp.py"
    if not app_path.exists():
        raise FileNotFoundError(f"No se encontró {app_path}")

    port = find_free_port()
    url = f"http://localhost:{port}"

    args = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.address",
        "localhost",
        "--server.headless",
        "false",
        "--browser.gatherUsageStats",
        "false",
        "--client.toolbarMode",
        "minimal",
    ]

    subprocess.Popen(args, cwd=base_dir)
    time.sleep(2.5)
    webbrowser.open(url)


if __name__ == "__main__":
    main()
