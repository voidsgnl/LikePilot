import atexit
import io
import os
import sys
import threading
from datetime import datetime


class _MultiLogWriter:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for stream in self._streams:
            stream.write(data)

    def flush(self):
        for stream in self._streams:
            stream.flush()

    def close(self):
        for stream in self._streams:
            try:
                stream.close()
            except Exception:
                pass


class _FilteredConsoleStream(io.TextIOBase):
    def __init__(self, original_stream, log_writer, console_predicate):
        self._original_stream = original_stream
        self._log_writer = log_writer
        self._console_predicate = console_predicate
        self._buffer = ""
        self._lock = threading.RLock()

    @property
    def encoding(self):
        return getattr(self._original_stream, "encoding", "utf-8")

    def writable(self):
        return True

    def isatty(self):
        return False

    def write(self, data):
        if data is None:
            return 0
        if not isinstance(data, str):
            data = str(data)
        if not data:
            return 0

        with self._lock:
            self._buffer += data
            while True:
                newline_index = self._buffer.find("\n")
                if newline_index == -1:
                    break
                line = self._buffer[: newline_index + 1]
                self._buffer = self._buffer[newline_index + 1 :]
                self._write_line(line)
        return len(data)

    def flush(self):
        with self._lock:
            if self._buffer:
                self._write_line(self._buffer)
                self._buffer = ""
            self._log_writer.flush()
            try:
                self._original_stream.flush()
            except Exception:
                pass

    def _write_line(self, line):
        self._log_writer.write(line)
        if self._console_predicate(line):
            try:
                self._original_stream.write(line)
            except Exception:
                pass


def install_console_log_router(project_root):
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_log_path = os.path.join(logs_dir, f"likepilot-{timestamp}.log")
    latest_log_path = os.path.join(logs_dir, "latest.log")

    session_log = open(session_log_path, "a", encoding="utf-8")
    latest_log = open(latest_log_path, "w", encoding="utf-8")
    writer = _MultiLogWriter(session_log, latest_log)

    def console_predicate(line):
        stripped = line.strip()
        return stripped.startswith("Open http") and "/login" in stripped

    stdout_router = _FilteredConsoleStream(sys.__stdout__, writer, console_predicate)
    stderr_router = _FilteredConsoleStream(sys.__stderr__, writer, console_predicate)

    sys.stdout = stdout_router
    sys.stderr = stderr_router

    writer.write(f"[{datetime.now().isoformat(timespec='seconds')}] LikePilot runtime log started.\n")
    writer.write(f"[{datetime.now().isoformat(timespec='seconds')}] Session log: {session_log_path}\n")
    writer.flush()

    def cleanup():
        try:
            stdout_router.flush()
            stderr_router.flush()
        finally:
            writer.close()

    atexit.register(cleanup)
    return session_log_path
