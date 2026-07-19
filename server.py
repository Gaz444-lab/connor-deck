#!/usr/bin/env python3
"""
Connor's Deck — localhost control plane.
Serves the static UI and safe launch / stop / update APIs for registered apps.
Binds 127.0.0.1 only. Never runs arbitrary client-supplied commands.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
PORT = 8764
HOST = "127.0.0.1"
APPS_FILE = ROOT / "data" / "apps.json"
HOME = Path.home().resolve()

# Only allow installs under these roots (after expansion).
ALLOWED_ROOTS = (
    HOME,
    (HOME / "Documents").resolve(),
)


def log(msg: str) -> None:
    print(msg, flush=True)


def expand_path(raw: str) -> Path:
    return Path(os.path.expanduser(raw)).resolve()


def is_allowed_dir(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in ALLOWED_ROOTS:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def load_registry() -> dict[str, Any]:
    with open(APPS_FILE, encoding="utf-8") as f:
        return json.load(f)


def app_by_id(app_id: str) -> dict[str, Any] | None:
    reg = load_registry()
    for app in reg.get("apps", []):
        if app.get("id") == app_id:
            return app
    return None


def candidate_dirs(app: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    primary = app.get("installDir")
    if primary:
        paths.append(expand_path(primary))
    for alt in app.get("altInstallDirs") or []:
        paths.append(expand_path(alt))
    # de-dupe while preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def resolve_install_dir(app: dict[str, Any]) -> Path | None:
    for p in candidate_dirs(app):
        if not is_allowed_dir(p):
            continue
        if p.is_dir():
            return p
    return None


def read_version(path: Path) -> str | None:
    vf = path / "VERSION"
    if vf.is_file():
        try:
            return vf.read_text(encoding="utf-8").strip() or None
        except OSError:
            return None
    return None


def git_short_sha(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    try:
        r = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if r.returncode == 0:
            return r.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None
    return None


def port_in_use(port: int | None) -> bool:
    if not port:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        try:
            return s.connect_ex((HOST, int(port))) == 0
        except OSError:
            return False


def pid_alive(path: Path, pid_file: str | None) -> bool:
    if not pid_file:
        return False
    pf = path / pid_file
    if not pf.is_file():
        return False
    try:
        pid = int(pf.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def find_launch_script(path: Path, app: dict[str, Any]) -> Path | None:
    primary = app.get("launchScript") or "launch.sh"
    candidates = [path / primary]
    fb = app.get("fallbackLaunch")
    if fb:
        candidates.append(path / fb)
    # common Desktop-style names
    for name in (
        "Mystery Hollow.command",
        "Launch Mystery Hollow.command",
        f"{app.get('name', '')}.command",
    ):
        if name:
            candidates.append(path / name)
    seen: set[str] = set()
    for c in candidates:
        key = str(c)
        if key in seen:
            continue
        seen.add(key)
        if c.is_file() and is_allowed_dir(c.parent):
            return c
    return None


def status_for(app: dict[str, Any]) -> dict[str, Any]:
    state = app.get("state") or "active"
    install = resolve_install_dir(app)
    base: dict[str, Any] = {
        "id": app.get("id"),
        "name": app.get("name"),
        "tagline": app.get("tagline"),
        "emoji": app.get("emoji"),
        "accent": app.get("accent"),
        "vibe": app.get("vibe"),
        "port": app.get("port"),
        "url": app.get("url"),
        "order": app.get("order", 99),
        "state": state,
        "tease": app.get("tease"),
        "installPath": str(install) if install else None,
        "version": None,
        "gitSha": None,
        "status": "unknown",
        "canLaunch": False,
        "canStop": False,
        "canUpdate": False,
    }

    if state == "planned" and not install:
        base["status"] = "coming_soon"
        return base

    if not install:
        if state == "planned":
            base["status"] = "coming_soon"
        else:
            base["status"] = "not_installed"
        return base

    base["version"] = read_version(install)
    base["gitSha"] = git_short_sha(install)
    has_git = (install / ".git").exists()
    launch = find_launch_script(install, app)

    if state == "external":
        base["status"] = "installed" if launch else "not_installed"
        base["canLaunch"] = bool(launch)
        base["canUpdate"] = has_git
        base["canStop"] = False
        return base

    # planned but somehow installed → treat as active-capable
    online = port_in_use(app.get("port")) or pid_alive(install, app.get("pidFile"))
    if online:
        base["status"] = "online"
        base["canLaunch"] = True
        base["canStop"] = bool(app.get("port") or app.get("pidFile"))
    else:
        base["status"] = "offline" if launch else "not_installed"
        base["canLaunch"] = bool(launch)
        base["canStop"] = False
    base["canUpdate"] = has_git
    return base


def deck_version() -> dict[str, Any]:
    ver = read_version(ROOT) or "0.0.0"
    return {
        "version": ver,
        "gitSha": git_short_sha(ROOT),
        "port": PORT,
    }


def kill_port(port: int) -> None:
    try:
        r = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        pids = [p.strip() for p in r.stdout.split() if p.strip()]
        for pid_s in pids:
            try:
                os.kill(int(pid_s), signal.SIGTERM)
            except (OSError, ValueError):
                pass
    except (OSError, subprocess.TimeoutExpired):
        pass


def stop_app(app: dict[str, Any]) -> dict[str, Any]:
    if app.get("state") == "external":
        return {"ok": False, "error": "External apps cannot be stopped from the Deck"}
    install = resolve_install_dir(app)
    if not install:
        return {"ok": False, "error": "App not installed"}

    pid_file = app.get("pidFile")
    if pid_file:
        pf = install / pid_file
        if pf.is_file():
            try:
                pid = int(pf.read_text(encoding="utf-8").strip())
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
                try:
                    pf.unlink(missing_ok=True)  # type: ignore[call-arg]
                except TypeError:
                    if pf.exists():
                        pf.unlink()
            except (OSError, ValueError):
                pass

    port = app.get("port")
    if port:
        kill_port(int(port))

    return {"ok": True, "message": f"Stopped {app.get('name')}"}


def launch_app(app: dict[str, Any]) -> dict[str, Any]:
    if app.get("state") == "planned":
        install = resolve_install_dir(app)
        if not install:
            return {"ok": False, "error": "Coming soon — not installed yet"}

    install = resolve_install_dir(app)
    if not install:
        return {"ok": False, "error": "App not installed on this Mac"}
    if not is_allowed_dir(install):
        return {"ok": False, "error": "Install path not allowed"}

    script = find_launch_script(install, app)
    if not script:
        return {"ok": False, "error": "No launch script found"}

    try:
        # Detach so the Deck server is not blocked by interactive .command wait prompts.
        # Prefer launch.sh when present (non-blocking for web hubs).
        subprocess.Popen(
            ["/bin/zsh", str(script)],
            cwd=str(install),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        return {"ok": False, "error": f"Failed to launch: {e}"}

    # For web apps, also ensure browser opens even if launch.sh is slow
    url = app.get("url")
    if url and app.get("state") != "external":
        # launch.sh already opens browser; soft open as backup after a beat is handled client-side
        pass

    return {
        "ok": True,
        "message": f"Launching {app.get('name')}",
        "url": url if app.get("state") != "external" else None,
    }


def update_app(app: dict[str, Any]) -> dict[str, Any]:
    if app.get("state") == "planned" and not resolve_install_dir(app):
        return {"ok": False, "error": "Coming soon — nothing to update"}

    install = resolve_install_dir(app)
    if not install:
        return {"ok": False, "error": "App not installed"}
    if not is_allowed_dir(install):
        return {"ok": False, "error": "Install path not allowed"}
    if not (install / ".git").exists():
        return {"ok": False, "error": "Not a git repo — cannot update"}

    # Stop web servers before pull (same idea as Update *.command scripts)
    if app.get("state") != "external":
        stop_app(app)

    try:
        r = subprocess.run(
            ["git", "-C", str(install), "pull", "--ff-only"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "git pull timed out"}
    except OSError as e:
        return {"ok": False, "error": str(e)}

    if r.returncode != 0:
        err = (r.stderr or r.stdout or "git pull failed").strip()
        return {"ok": False, "error": err}

    # Best-effort executable bits
    for pattern in ("*.command", "launch.sh", "scripts/*.sh"):
        for f in install.glob(pattern):
            try:
                f.chmod(f.stat().st_mode | 0o111)
            except OSError:
                pass

    return {
        "ok": True,
        "message": f"Updated {app.get('name')}",
        "output": (r.stdout or "").strip(),
        "version": read_version(install),
        "gitSha": git_short_sha(install),
    }


def update_all() -> dict[str, Any]:
    reg = load_registry()
    results = []
    for app in sorted(reg.get("apps", []), key=lambda a: a.get("order", 99)):
        if app.get("state") == "planned" and not resolve_install_dir(app):
            results.append(
                {
                    "id": app.get("id"),
                    "name": app.get("name"),
                    "ok": True,
                    "skipped": True,
                    "message": "Skipped (coming soon)",
                }
            )
            continue
        install = resolve_install_dir(app)
        if not install or not (install / ".git").exists():
            results.append(
                {
                    "id": app.get("id"),
                    "name": app.get("name"),
                    "ok": True,
                    "skipped": True,
                    "message": "Skipped (not installed or no git)",
                }
            )
            continue
        res = update_app(app)
        results.append({"id": app.get("id"), "name": app.get("name"), **res})
    return {"ok": True, "results": results}


class DeckHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        log(f"[deck] {self.address_string()} {fmt % args}")

    def _json(self, code: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/health":
            self._json(200, {"ok": True, "service": "connor-deck"})
            return
        if path == "/api/deck/version":
            self._json(200, deck_version())
            return
        if path == "/api/apps":
            reg = load_registry()
            apps = [status_for(a) for a in reg.get("apps", [])]
            apps.sort(key=lambda a: a.get("order", 99))
            self._json(
                200,
                {
                    "ok": True,
                    "apps": apps,
                    "slots": reg.get("slots", 6),
                    "emptySlotTeases": reg.get("emptySlotTeases") or [],
                    "deck": deck_version(),
                },
            )
            return

        # Static files only from ROOT (SimpleHTTPRequestHandler + directory=ROOT)
        if path.startswith("/api/"):
            self._json(404, {"ok": False, "error": "Unknown API route"})
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        # body unused for now but consume to keep connection healthy
        _ = self._read_json()

        try:
            if path == "/api/update-all":
                self._json(200, update_all())
                return

            if path.startswith("/api/apps/") and path.endswith("/launch"):
                app_id = path[len("/api/apps/") : -len("/launch")]
                app = app_by_id(app_id)
                if not app:
                    self._json(404, {"ok": False, "error": "Unknown app"})
                    return
                self._json(200, launch_app(app))
                return

            if path.startswith("/api/apps/") and path.endswith("/stop"):
                app_id = path[len("/api/apps/") : -len("/stop")]
                app = app_by_id(app_id)
                if not app:
                    self._json(404, {"ok": False, "error": "Unknown app"})
                    return
                self._json(200, stop_app(app))
                return

            if path.startswith("/api/apps/") and path.endswith("/update"):
                app_id = path[len("/api/apps/") : -len("/update")]
                app = app_by_id(app_id)
                if not app:
                    self._json(404, {"ok": False, "error": "Unknown app"})
                    return
                self._json(200, update_app(app))
                return

            self._json(404, {"ok": False, "error": "Unknown API route"})
        except Exception as e:  # noqa: BLE001
            log(traceback.format_exc())
            self._json(500, {"ok": False, "error": str(e)})


def main() -> int:
    os.chdir(ROOT)
    if not APPS_FILE.is_file():
        log(f"Missing registry: {APPS_FILE}")
        return 1

    httpd = ThreadingHTTPServer((HOST, PORT), DeckHandler)
    log(f"Connor's Deck → http://{HOST}:{PORT}/  (PID {os.getpid()})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("\nDeck stopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
