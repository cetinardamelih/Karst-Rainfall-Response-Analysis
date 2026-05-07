from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import webbrowser


APP_NAME = "Karst Rainfall-Response Analysis"
DEFAULT_PORT = 8501


def appdata_dir() -> Path:
    """Return the writable app data directory for logs and runtime metadata."""
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / "AppData" / "Roaming" / APP_NAME


def documents_outputs_dir() -> Path:
    """Return the user-facing outputs directory."""
    return Path.home() / "Documents" / APP_NAME / "outputs"


def ensure_user_dirs() -> None:
    """Create writable runtime folders outside Program Files."""
    (appdata_dir() / "logs").mkdir(parents=True, exist_ok=True)
    (appdata_dir() / "matplotlib").mkdir(parents=True, exist_ok=True)
    documents_outputs_dir().mkdir(parents=True, exist_ok=True)


def setup_logging() -> Path:
    """Configure file logging and return the log path."""
    ensure_user_dirs()
    log_path = appdata_dir() / "logs" / "app.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )
    return log_path


def bundle_root() -> Path:
    """Return project root in source mode or PyInstaller bundle root in exe mode."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[2]


def streamlit_app() -> Path:
    """Return the Streamlit application file bundled with the executable."""
    path = bundle_root() / "app" / "streamlit_app.py"
    if not path.exists():
        raise FileNotFoundError(f"Streamlit app not found: {path}")
    return path


def is_port_free(port: int) -> bool:
    """Check whether a localhost port is free."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def find_free_port(preferred: int = DEFAULT_PORT) -> int:
    """Use the preferred port when possible, otherwise ask Windows for a free port."""
    if is_port_free(preferred):
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_until_ready(port: int, process: subprocess.Popen, timeout_seconds: int = 90) -> bool:
    """Wait until the Streamlit server is listening on localhost."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            logging.error("Streamlit child process exited early with code %s", process.returncode)
            return False
        if not is_port_free(port):
            time.sleep(0.75)
            return True
        time.sleep(0.5)
    return False


def show_error(message: str) -> None:
    """Show a simple Windows message box if startup fails."""
    logging.error(message)
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
            return
        except Exception:
            pass
    print(message, file=sys.stderr)


def subprocess_options(log_file) -> dict:
    """Return subprocess options that hide console windows on Windows."""
    options = {
        "stdout": log_file,
        "stderr": log_file,
        "cwd": str(bundle_root()),
        "env": os.environ.copy(),
    }
    options["env"]["KARST_RRA_OUTPUT_DIR"] = str(documents_outputs_dir())
    options["env"]["KARST_RRA_LOG_DIR"] = str(appdata_dir() / "logs")
    options["env"]["MPLCONFIGDIR"] = str(appdata_dir() / "matplotlib")
    options["env"]["PYTHONUTF8"] = "1"
    options["env"]["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        options["startupinfo"] = startupinfo
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    return options


def child_command(port: int) -> list[str]:
    """Build command that starts Streamlit inside this exe or source launcher."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--streamlit-child", "--port", str(port)]
    return [sys.executable, str(Path(__file__).resolve()), "--streamlit-child", "--port", str(port)]


def start_streamlit_process(port: int, log_path: Path) -> subprocess.Popen:
    """Start the hidden Streamlit child process."""
    log_file = open(log_path, "a", encoding="utf-8")
    command = child_command(port)
    logging.info("Starting Streamlit child process: %s", command)
    return subprocess.Popen(command, **subprocess_options(log_file))


def stop_process(process: subprocess.Popen | None) -> None:
    """Stop the Streamlit child process."""
    if process is None or process.poll() is not None:
        return
    logging.info("Stopping Streamlit child process")
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()


def open_default_browser(url: str) -> None:
    """Open the app URL in the user's default browser."""
    if os.name == "nt":
        os.startfile(url)  # type: ignore[attr-defined]
        return
    webbrowser.open(url, new=2)


def run_streamlit_child(port: int) -> None:
    """Run Streamlit server in the hidden child process."""
    setup_logging()
    ensure_user_dirs()

    os.environ.setdefault("KARST_RRA_OUTPUT_DIR", str(documents_outputs_dir()))
    os.environ.setdefault("KARST_RRA_LOG_DIR", str(appdata_dir() / "logs"))
    os.environ.setdefault("MPLCONFIGDIR", str(appdata_dir() / "matplotlib"))
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    from streamlit.web import cli as streamlit_cli

    sys.argv = [
        "streamlit",
        "run",
        str(streamlit_app()),
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    streamlit_cli.main()


def run_launcher() -> int:
    """Start Streamlit, open the default browser, and keep the child process alive."""
    log_path = setup_logging()
    process: subprocess.Popen | None = None
    try:
        port = find_free_port()
        url = f"http://127.0.0.1:{port}"
        logging.info("Launching %s at %s", APP_NAME, url)

        process = start_streamlit_process(port, log_path)
        if not wait_until_ready(port, process):
            if process.poll() is not None:
                raise RuntimeError(
                    "The background application process exited before startup completed. "
                    f"See the log file for details: {log_path}"
                )
            raise RuntimeError(f"The application was not ready in time. Log file: {log_path}")

        logging.info("Opening browser at %s", url)
        open_default_browser(url)
        logging.info("Opened browser at %s", url)

        while process.poll() is None:
            time.sleep(1)
        return int(process.returncode or 0)
    except KeyboardInterrupt:
        stop_process(process)
        return 0
    except Exception as exc:
        stop_process(process)
        show_error(f"The application could not be started.\n\n{exc}\n\nLog file:\n{log_path}")
        return 1


def parse_args() -> argparse.Namespace:
    """Parse launcher arguments."""
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--streamlit-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    """Application entry point."""
    args = parse_args()
    if args.streamlit_child:
        run_streamlit_child(args.port)
        return 0
    return run_launcher()


if __name__ == "__main__":
    raise SystemExit(main())
