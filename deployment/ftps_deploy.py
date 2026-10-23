#!/usr/bin/env python3
"""FTPS-Deployer für die Hendrik-Website (nur Python-Standardbibliothek).

Modi:
  (Standard)  Plan: prüft den lokalen Build, verbindet sich per FTPS und liest
              den Zielordner ausschließlich lesend. Es wird nichts geschrieben.
  --offline   Nur lokale Prüfung des Builds und der Konfiguration, keine Verbindung.
  --deploy    Schreibmodus. Nur mit DEPLOY_ENABLED=true. Bestätigt zuerst per
              Zufallsprobe den Webroot, lädt dann hoch (Assets, HTML, .htaccess zuletzt)
              und prüft zum Schluss die Website per HTTPS.

Es wird nie etwas auf dem Server gelöscht, außer eigenen temporären Dateien und der
eigenen Probe dieses Laufs. Zusätzliche Serverdateien bleiben unverändert.

Konfiguration (Umgebungsvariablen): FTP_HOST, FTP_PORT (Standard 21), FTP_USER,
FTP_PASSWORD, FTP_REMOTE_DIR, SITE_URL. Zugangsdaten werden nie ausgegeben.
"""
from __future__ import annotations

import argparse
import dataclasses
import ftplib
import hashlib
import io
import os
import posixpath
import secrets
import ssl
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set

# Einziges zulässiges Ziel. Eine Änderung ist eine bewusste Codeänderung.
ALLOWED_REMOTE_DIR = "/hendrik.kreativdeck.dev"
ALLOWED_SITE_HOST = "hendrik.kreativdeck.dev"

DEFAULT_PORT = 21
FTP_TIMEOUT = 60
HTTP_TIMEOUT = 30
HTTP_MAX_BYTES = 8 * 1024 * 1024
PROBE_ATTEMPTS = 3
PROBE_RETRY_SECONDS = 2.0

# Nur diese Namen legt der Deployer selbst an; nur diese darf er löschen bzw. umbenennen.
TMP_PREFIX = ".kd-tmp-"
PROBE_PREFIX = "kd-deploy-probe-"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCE = os.path.join(REPO_ROOT, "frontend", "dist")


class DeployError(Exception):
    """Fehler mit lesbarer, credentialfreier Meldung (Exitcode 1)."""


class ConfigError(DeployError):
    """Fehlende oder unzulässige Konfiguration (Exitcode 2)."""


class BuildError(DeployError):
    """Der lokale Build ist nicht deploybar."""


# --------------------------------------------------------------------------- Ausgabe


class Log:
    """Gibt Text aus und ersetzt dabei bekannte Geheimnisse."""

    def __init__(self, secret_values: Iterable[str] = ()):
        self._secrets = sorted({s for s in secret_values if s}, key=len, reverse=True)

    def redact(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, "***")
        return text

    def info(self, message: str = "") -> None:
        print(self.redact(message), file=sys.stdout, flush=True)

    def error(self, message: str) -> None:
        print(self.redact(message), file=sys.stderr, flush=True)


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


# ----------------------------------------------------------------------- Konfiguration


@dataclasses.dataclass(frozen=True)
class Config:
    host: str
    port: int
    user: str = dataclasses.field(repr=False)
    password: str = dataclasses.field(repr=False)
    remote_dir: str
    site_url: str


def normalize_remote_dir(value: str) -> str:
    """Erlaubt exakt das konfigurierte Ziel (optional mit abschließendem Slash)."""
    cleaned = value.strip()
    if any(ord(c) < 32 or ord(c) == 127 for c in cleaned) or "\\" in cleaned:
        raise ConfigError("FTP_REMOTE_DIR enthält unzulässige Zeichen")
    if cleaned != "/" and cleaned.endswith("/"):
        cleaned = cleaned.rstrip("/")
    if cleaned != ALLOWED_REMOTE_DIR:
        raise ConfigError(
            f"FTP_REMOTE_DIR muss exakt {ALLOWED_REMOTE_DIR} sein (Wurzel, andere Ordner "
            "und Unterordner sind nicht zulässig)"
        )
    return cleaned


def normalize_site_url(value: str) -> str:
    cleaned = value.strip()
    parsed = urllib.parse.urlsplit(cleaned)
    if parsed.scheme != "https":
        raise ConfigError("SITE_URL muss mit https:// beginnen")
    try:
        port = parsed.port
    except ValueError:
        raise ConfigError("SITE_URL enthält einen ungültigen Port") from None
    if (
        parsed.hostname != ALLOWED_SITE_HOST
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ConfigError(f"SITE_URL muss exakt https://{ALLOWED_SITE_HOST} sein (ohne Pfad)")
    return f"https://{ALLOWED_SITE_HOST}"


def load_config(env: Mapping[str, str]) -> Config:
    """Liest und prüft die Konfiguration; Fehlermeldungen nennen nur Variablennamen."""
    required = ("FTP_HOST", "FTP_USER", "FTP_PASSWORD", "FTP_REMOTE_DIR", "SITE_URL")
    missing = [name for name in required if not env.get(name, "").strip()]
    if missing:
        raise ConfigError("Fehlende Konfiguration: " + ", ".join(missing))

    host = env["FTP_HOST"].strip()
    if any(c.isspace() or c in "/\\@:" or ord(c) < 32 for c in host):
        raise ConfigError("FTP_HOST muss ein reiner Hostname sein (ohne Schema, Port oder Pfad)")

    port_text = env.get("FTP_PORT", "").strip() or str(DEFAULT_PORT)
    if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
        raise ConfigError("FTP_PORT muss eine Zahl von 1 bis 65535 sein")

    user = env["FTP_USER"].strip()
    password = env["FTP_PASSWORD"]
    for value in (user, password):
        if any(c in "\r\n\x00" for c in value):
            raise ConfigError("FTP_USER/FTP_PASSWORD enthalten unzulässige Steuerzeichen")

    return Config(
        host=host,
        port=int(port_text),
        user=user,
        password=password,
        remote_dir=normalize_remote_dir(env["FTP_REMOTE_DIR"]),
        site_url=normalize_site_url(env["SITE_URL"]),
    )


# ------------------------------------------------------------------------ Lokaler Build


@dataclasses.dataclass(frozen=True)
class LocalFile:
    rel: str  # POSIX-Pfad relativ zum Build-Ordner
    path: str
    size: int


def _bad_name_reason(name: str) -> Optional[str]:
    if name in (".", "..") or "\\" in name or any(ord(c) < 32 or ord(c) == 127 for c in name):
        return "unzulässiger Name (Steuerzeichen, Backslash oder Punktsegment)"
    try:
        name.encode("utf-8")
    except UnicodeEncodeError:
        return "Name ist kein gültiges UTF-8"
    lower = name.lower()
    if name == ".DS_Store" or name.startswith("._"):
        return "macOS-Metadaten"
    if lower.startswith(".git") and lower != ".gitkeep":  # .gitkeep stammt aus public/ und ist harmlos
        return "Git-Metadaten"
    if lower.startswith(".env"):
        return "Umgebungs-/Zugangsdatei"
    if lower in ("node_modules", "thumbs.db", "desktop.ini"):
        return "nicht für die Veröffentlichung bestimmt"
    if name.startswith(TMP_PREFIX) or name.startswith(PROBE_PREFIX):
        return "reserviertes Präfix des Deployers"
    return None


def scan_build(source: str) -> List[LocalFile]:
    """Validiert den Build-Ordner und liefert alle Dateien (sortiert nach Pfad)."""
    if os.path.islink(source) or not os.path.isdir(source):
        raise BuildError(f"Build-Ordner nicht gefunden oder Symlink: {source}")

    files: List[LocalFile] = []
    problems: List[str] = []

    def walk(directory: str, rel_dir: str) -> None:
        for name in sorted(os.listdir(directory)):
            rel = f"{rel_dir}/{name}" if rel_dir else name
            reason = _bad_name_reason(name)
            if reason:
                problems.append(f"{rel}: {reason}")
                continue
            path = os.path.join(directory, name)
            mode = os.lstat(path).st_mode
            if stat.S_ISLNK(mode):
                problems.append(f"{rel}: Symlink")
            elif stat.S_ISDIR(mode):
                walk(path, rel)
            elif stat.S_ISREG(mode):
                files.append(LocalFile(rel, path, os.lstat(path).st_size))
            else:
                problems.append(f"{rel}: keine reguläre Datei")

    walk(source, "")

    names = {f.rel for f in files}
    for required in (".htaccess", "index.html"):
        if required not in names:
            problems.append(f"{required}: fehlt im Build")
    if problems:
        shown = "\n  ".join(problems[:30])
        more = f"\n  … und {len(problems) - 30} weitere" if len(problems) > 30 else ""
        raise BuildError("Build-Ordner ist nicht deploybar:\n  " + shown + more)
    return sorted(files, key=lambda f: f.rel)


def check_build_origin(files: Sequence[LocalFile], site_url: str) -> None:
    """Der Build muss für dieselbe SITE_URL erzeugt worden sein (robots.txt-Sitemap)."""
    robots = next((f for f in files if f.rel == "robots.txt"), None)
    if robots is None:
        return
    with open(robots.path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.lower().startswith("sitemap:"):
                url = line.split(":", 1)[1].strip()
                if not (url == site_url or url.startswith(site_url + "/")):
                    raise BuildError(
                        "Der Build wurde für eine andere SITE_URL erzeugt "
                        f"(robots.txt verweist auf {url}, erwartet {site_url}/…)"
                    )


def _rank(rel: str) -> int:
    name = posixpath.basename(rel)
    if name == ".htaccess":
        return 3
    if rel == "index.html":
        return 2
    if name.lower().endswith((".html", ".htm")):
        return 1
    return 0


def upload_order(files: Iterable[LocalFile]) -> List[LocalFile]:
    """Assets zuerst, dann HTML (Startseite zuletzt), .htaccess ganz am Ende."""
    return sorted(files, key=lambda f: (_rank(f.rel), f.rel))


# ----------------------------------------------------------------------- FTPS-Zugriff


@dataclasses.dataclass(frozen=True)
class RemoteEntry:
    kind: str  # "file", "dir" oder "other"
    size: Optional[int]


def make_tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


class FtpsClient:
    """Explizites FTPS (AUTH TLS, PROT P, passiv) mit eingebauten Schreibgrenzen."""

    def __init__(self, cfg: Config, *, ftp_factory=None, tls_context=None):
        self._cfg = cfg
        self._root = cfg.remote_dir
        self._factory = ftp_factory or ftplib.FTP_TLS
        self._context = tls_context
        self._ftp = None

    # Verbindung -----------------------------------------------------------------
    def connect(self) -> None:
        ftp = self._factory(context=self._context or make_tls_context(), timeout=FTP_TIMEOUT)
        self._ftp = ftp
        try:
            ftp.connect(self._cfg.host, self._cfg.port)
            ftp.auth()
            ftp.login(self._cfg.user, self._cfg.password)
            ftp.prot_p()
            ftp.set_pasv(True)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        ftp, self._ftp = self._ftp, None
        if ftp is None:
            return
        try:
            ftp.quit()
        except Exception:
            try:
                ftp.close()
            except Exception:
                pass

    # Pfadgrenzen ----------------------------------------------------------------
    def _inside(self, path: str) -> str:
        if (
            not path.startswith("/")
            or any(ord(c) < 32 or ord(c) == 127 for c in path)
            or ".." in path.split("/")
        ):
            raise DeployError(f"Unzulässiger Serverpfad: {path!r}")
        normalized = posixpath.normpath(path)
        if normalized != self._root and not normalized.startswith(self._root + "/"):
            raise DeployError(f"Serverpfad liegt außerhalb von {self._root}: {path!r}")
        return normalized

    def _inside_strict(self, path: str) -> str:
        normalized = self._inside(path)
        if normalized == self._root:
            raise DeployError("Schreiben auf den Zielordner selbst ist nicht zulässig")
        return normalized

    @staticmethod
    def _own(path: str, prefixes: Sequence[str]) -> bool:
        return posixpath.basename(path).startswith(tuple(prefixes))

    # Lesen ----------------------------------------------------------------------
    def resolve_dir(self, path: str) -> Optional[str]:
        """Wechselt in den Ordner und gibt den vom Server gemeldeten Pfad zurück."""
        self._inside(path)
        try:
            self._ftp.cwd(path)
        except ftplib.error_perm:
            return None
        return self._ftp.pwd()

    def size(self, path: str) -> Optional[int]:
        self._inside(path)
        try:
            self._ftp.voidcmd("TYPE I")
            return self._ftp.size(path)
        except ftplib.error_perm:
            return None

    def list_dir(self, path: str) -> Optional[Dict[str, RemoteEntry]]:
        """Einträge des Ordners oder None, falls er nicht existiert/lesbar ist."""
        self._inside(path)
        entries: Dict[str, RemoteEntry] = {}
        try:
            for name, facts in self._ftp.mlsd(path):
                kind_fact = facts.get("type", "").lower()
                if kind_fact in ("cdir", "pdir") or name in (".", ".."):
                    continue
                kind = {"file": "file", "dir": "dir"}.get(kind_fact, "other")
                size = facts.get("size", "")
                entries[name] = RemoteEntry(kind, int(size) if size.isdigit() else None)
            return entries
        except (ftplib.error_perm, ftplib.error_temp) as exc:
            code = str(exc)[:3]
            if code in ("500", "501", "502", "504"):
                return self._list_fallback(path)
            if code in ("550", "450"):
                return None
            raise

    def _list_fallback(self, path: str) -> Optional[Dict[str, RemoteEntry]]:
        # Server ohne MLSD: NLST plus Einzelprüfung. Versteckte Dateien fehlen dort evtl.
        if self.resolve_dir(path) is None:
            return None
        try:
            names = self._ftp.nlst(path)
        except (ftplib.error_perm, ftplib.error_temp) as exc:
            if str(exc)[:3] not in ("550", "450"):
                raise
            names = []
        entries: Dict[str, RemoteEntry] = {}
        for raw in names:
            base = posixpath.basename(raw.rstrip("/"))
            if base in ("", ".", ".."):
                continue
            full = posixpath.join(path, base)
            if self.resolve_dir(full) is not None:
                entries[base] = RemoteEntry("dir", None)
            else:
                entries[base] = RemoteEntry("file", self.size(full))
        return entries

    # Schreiben (nur im Zielordner und nur für eigene Namen) -----------------------
    def mkdir(self, path: str) -> None:
        self._ftp.mkd(self._inside_strict(path))

    def store(self, path: str, fp) -> None:
        target = self._inside_strict(path)
        if not self._own(target, (TMP_PREFIX,)):
            raise DeployError("Hochladen nur in temporäre Dateien des Deployers zulässig")
        self._ftp.storbinary("STOR " + target, fp)

    def rename(self, source: str, target: str) -> None:
        src = self._inside_strict(source)
        dst = self._inside_strict(target)
        if not self._own(src, (TMP_PREFIX,)):
            raise DeployError("Umbenennen nur von temporären Dateien des Deployers zulässig")
        self._ftp.rename(src, dst)

    def delete(self, path: str) -> None:
        target = self._inside_strict(path)
        if not self._own(target, (TMP_PREFIX, PROBE_PREFIX)):
            raise DeployError("Löschen nur eigener temporärer Dateien/Proben zulässig")
        self._ftp.delete(target)


class ReadOnlyRemote:
    """Reicht ausschließlich lesende Operationen durch; Schreiben ist nicht möglich."""

    def __init__(self, inner):
        self._inner = inner

    def resolve_dir(self, path: str) -> Optional[str]:
        return self._inner.resolve_dir(path)

    def list_dir(self, path: str) -> Optional[Dict[str, RemoteEntry]]:
        return self._inner.list_dir(path)

    def size(self, path: str) -> Optional[int]:
        return self._inner.size(path)


# ----------------------------------------------------------------------------- HTTP


@dataclasses.dataclass(frozen=True)
class HttpResponse:
    status: int
    content_type: str
    body: bytes


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # Weiterleitungen als Status melden
        return None


def http_get(url: str) -> HttpResponse:
    opener = urllib.request.build_opener(
        _NoRedirect, urllib.request.HTTPSHandler(context=make_tls_context())
    )
    request = urllib.request.Request(
        url, headers={"User-Agent": "kreativdeck-ftps-deploy/1", "Cache-Control": "no-cache"}
    )
    try:
        with opener.open(request, timeout=HTTP_TIMEOUT) as response:
            return HttpResponse(
                response.status,
                response.headers.get("Content-Type", ""),
                response.read(HTTP_MAX_BYTES),
            )
    except urllib.error.HTTPError as exc:
        return HttpResponse(exc.code, exc.headers.get("Content-Type", ""), exc.read(HTTP_MAX_BYTES))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise DeployError(f"HTTP-Abruf fehlgeschlagen ({url}): {exc}") from None


# ------------------------------------------------------------------------------ Plan


@dataclasses.dataclass
class Plan:
    total_files: int = 0
    total_bytes: int = 0
    new_files: List[str] = dataclasses.field(default_factory=list)
    replace_same_size: List[str] = dataclasses.field(default_factory=list)
    replace_other_size: List[str] = dataclasses.field(default_factory=list)
    replace_unknown_size: List[str] = dataclasses.field(default_factory=list)
    missing_dirs: List[str] = dataclasses.field(default_factory=list)
    extras: List[str] = dataclasses.field(default_factory=list)
    conflicts: List[str] = dataclasses.field(default_factory=list)

    @property
    def replaced(self) -> int:
        return len(self.replace_same_size) + len(self.replace_other_size) + len(self.replace_unknown_size)

    def render(self, limit: int = 25) -> List[str]:
        def block(title: str, items: List[str]) -> List[str]:
            if not items:
                return []
            shown = items[:limit] if limit else items
            lines = [f"  {title}:"] + [f"    {item}" for item in shown]
            if len(shown) < len(items):
                lines.append(f"    … und {len(items) - len(shown)} weitere")
            return lines

        lines = [
            f"Build: {self.total_files} Dateien ({human_size(self.total_bytes)})",
            f"  neu auf dem Server:                         {len(self.new_files)}",
            f"  gleichnamig vorhanden (würde ersetzt):      {self.replaced}",
            f"    davon gleiche Größe:                      {len(self.replace_same_size)}",
            f"    davon abweichende Größe:                  {len(self.replace_other_size)}",
            f"    davon Größe unbekannt:                    {len(self.replace_unknown_size)}",
            f"  neue Ordner:                                {len(self.missing_dirs)}",
            f"  zusätzliche Serverinhalte (bleiben, nie gelöscht): {len(self.extras)}",
        ]
        lines += block("Gleichnamige Dateien mit abweichender Größe", self.replace_other_size)
        lines += block("Zusätzliche Serverinhalte (bleiben unverändert)", self.extras)
        lines += block("KONFLIKTE (Datei/Ordner-Typ stimmt nicht überein)", self.conflicts)
        return lines


def build_plan(remote, root: str, files: Sequence[LocalFile]) -> Plan:
    """Vergleicht Build und Serverordner rein lesend. Es wird nie in Extras abgestiegen."""
    by_dir: Dict[str, Dict[str, LocalFile]] = {"": {}}
    subdirs: Dict[str, Set[str]] = {"": set()}
    for f in files:
        parts = f.rel.split("/")
        current = ""
        for part in parts[:-1]:
            child = f"{current}/{part}" if current else part
            subdirs.setdefault(current, set()).add(part)
            subdirs.setdefault(child, set())
            by_dir.setdefault(child, {})
            current = child
        by_dir.setdefault(current, {})[parts[-1]] = f

    plan = Plan(total_files=len(files), total_bytes=sum(f.size for f in files))
    queue = [("", False)]  # (relativer Ordner, bekannt fehlend)
    while queue:
        rel_dir, known_missing = queue.pop(0)
        entries: Optional[Dict[str, RemoteEntry]]
        if known_missing:
            entries = {}
        else:
            entries = remote.list_dir(posixpath.join(root, rel_dir) if rel_dir else root)
            if entries is None:
                raise DeployError(
                    f"Serverordner nicht lesbar: {rel_dir or root}"
                    if rel_dir
                    else f"Zielordner {root} existiert nicht oder ist nicht lesbar"
                )
        local_files = by_dir.get(rel_dir, {})
        local_dirs = subdirs.get(rel_dir, set())
        prefix = f"{rel_dir}/" if rel_dir else ""

        for name, f in sorted(local_files.items()):
            entry = entries.get(name)
            if entry is None:
                plan.new_files.append(f.rel)
            elif entry.kind != "file":
                plan.conflicts.append(f"{f.rel}: auf dem Server ist es ein {entry.kind}")
            elif entry.size is None:
                plan.replace_unknown_size.append(f.rel)
            elif entry.size == f.size:
                plan.replace_same_size.append(f.rel)
            else:
                plan.replace_other_size.append(f.rel)

        for name in sorted(local_dirs):
            child = prefix + name
            entry = entries.get(name)
            if entry is None:
                plan.missing_dirs.append(child)
                queue.append((child, True))
            elif entry.kind != "dir":
                plan.conflicts.append(f"{child}/: auf dem Server ist es ein {entry.kind}")
            else:
                queue.append((child, False))

        for name, entry in sorted(entries.items()):
            if name not in local_files and name not in local_dirs:
                plan.extras.append(prefix + name + ("/" if entry.kind == "dir" else ""))
    return plan


# --------------------------------------------------------------------------- Deployer


class Deployer:
    def __init__(
        self,
        cfg: Config,
        remote,
        http: Callable[[str], HttpResponse],
        log: Log,
        *,
        sleep: Callable[[float], None] = time.sleep,
        list_limit: int = 25,
    ):
        self.cfg = cfg
        self.remote = remote
        self.http = http
        self.log = log
        self.sleep = sleep
        self.list_limit = list_limit
        self.root = cfg.remote_dir
        self._run_id = secrets.token_hex(6)
        self._counter = 0

    # Plan (nur lesend) -------------------------------------------------------------
    def check_root(self) -> None:
        resolved = self.remote.resolve_dir(self.root)
        if resolved is None:
            raise DeployError(f"Zielordner {self.root} existiert nicht oder ist nicht zugänglich")
        if resolved.rstrip("/") != self.root:
            raise DeployError(
                f"Server meldet als Arbeitsverzeichnis {resolved!r} statt {self.root!r}; Abbruch"
            )

    def plan(self, files: Sequence[LocalFile]) -> Plan:
        self.check_root()
        plan = build_plan(self.remote, self.root, files)
        for line in plan.render(self.list_limit):
            self.log.info(line)
        if plan.conflicts:
            raise DeployError("Plan enthält Konflikte; es wird nichts übertragen")
        return plan

    # Atomares Hochladen ---------------------------------------------------------------
    def _next_tmp(self, final: str) -> str:
        self._counter += 1
        return posixpath.join(posixpath.dirname(final), f"{TMP_PREFIX}{self._run_id}-{self._counter}")

    def _discard(self, tmp: str) -> None:
        try:
            self.remote.delete(tmp)
        except Exception as exc:  # fehlt meist schlicht, weil der Upload nie begann
            self.log.info(f"  Hinweis: temporäre Datei {posixpath.basename(tmp)} nicht entfernt ({type(exc).__name__})")

    def put_atomic(self, final: str, fp, size: int) -> None:
        tmp = self._next_tmp(final)
        done = False
        try:
            self.remote.store(tmp, fp)
            remote_size = self.remote.size(tmp)
            if remote_size is not None and remote_size != size:
                raise DeployError(
                    f"Größenabweichung nach Upload von {final}: lokal {size}, Server {remote_size}"
                )
            self.remote.rename(tmp, final)
            done = True
        finally:
            if not done:
                self._discard(tmp)

    # Webroot-Bestätigung ----------------------------------------------------------------
    def _expect_probe(self, url: str, expected: bytes) -> None:
        detail = "unbekannt"
        for attempt in range(PROBE_ATTEMPTS):
            if attempt:
                self.sleep(PROBE_RETRY_SECONDS)
            try:
                response = self.http(url)
            except DeployError as exc:
                detail = str(exc)
                continue
            if response.status == 200 and response.body == expected:
                return
            detail = (
                f"HTTP {response.status}, Inhalt stimmt nicht"
                if response.status == 200
                else f"HTTP {response.status}"
            )
        raise DeployError(
            f"Webroot nicht bestätigt: {self.cfg.site_url} liefert die Probe aus {self.root} nicht aus "
            f"({detail}). Abbruch vor dem Aktualisieren von Dateien"
        )

    def _remove_probe(self, final: str, strict: bool) -> None:
        try:
            self.remote.delete(final)
        except Exception as exc:
            message = (
                f"Probe {posixpath.basename(final)} konnte nicht entfernt werden "
                f"({type(exc).__name__}); bitte manuell löschen"
            )
            if strict:
                raise DeployError(message) from None
            self.log.error("WARNUNG: " + message)

    def confirm_webroot(self) -> None:
        name = f"{PROBE_PREFIX}{secrets.token_hex(16)}.txt"
        final = posixpath.join(self.root, name)
        url = f"{self.cfg.site_url}/{name}"
        first = f"kd-deploy-probe {secrets.token_hex(16)} a\n".encode()
        second = f"kd-deploy-probe {secrets.token_hex(16)} b\n".encode()
        created = False
        try:
            self.put_atomic(final, io.BytesIO(first), len(first))
            created = True
            self._expect_probe(url, first)
            # Eigene Probe ersetzen: beweist, dass Umbenennen auf vorhandene Dateien funktioniert.
            self.put_atomic(final, io.BytesIO(second), len(second))
            self._expect_probe(url, second)
        except BaseException:
            if created:
                self._remove_probe(final, strict=False)
            raise
        self._remove_probe(final, strict=True)
        self.log.info("Webroot bestätigt: Zufallsprobe über SITE_URL abgerufen und wieder entfernt")

    # Deploy --------------------------------------------------------------------------------
    def deploy(self, files: Sequence[LocalFile]) -> None:
        plan = self.plan(files)
        self.confirm_webroot()

        for rel_dir in plan.missing_dirs:
            self.remote.mkdir(posixpath.join(self.root, rel_dir))
        if plan.missing_dirs:
            self.log.info(f"{len(plan.missing_dirs)} neue Ordner angelegt")

        ordered = upload_order(files)
        total = len(ordered)
        self.log.info(f"Übertrage {total} Dateien (Assets → HTML → .htaccess)")
        for index, f in enumerate(ordered, 1):
            with open(f.path, "rb") as fp:
                self.put_atomic(posixpath.join(self.root, f.rel), fp, f.size)
            if index % 50 == 0 or index == total:
                self.log.info(f"  {index}/{total} Dateien übertragen")

        self.post_checks(files)
        self.log.info(
            f"Fertig: {plan.replaced} gleichnamige Dateien ersetzt, {len(plan.new_files)} neu, "
            f"{len(plan.extras)} zusätzliche Serverinhalte unverändert belassen"
        )

    def post_checks(self, files: Sequence[LocalFile]) -> None:
        site = self.cfg.site_url
        by_rel = {f.rel: f for f in files}
        failures: List[str] = []

        def fetch(path: str) -> Optional[HttpResponse]:
            try:
                return self.http(site + urllib.parse.quote(path))
            except DeployError as exc:
                failures.append(str(exc))
                return None

        def sha(data: bytes) -> str:
            return hashlib.sha256(data).hexdigest()

        home = fetch("/")
        if home is not None and not (
            home.status == 200 and "html" in home.content_type.lower() and b"<html" in home.body.lower()
        ):
            failures.append(f"/ liefert kein HTML (HTTP {home.status})")

        samples = [rel for rel in ("robots.txt", "sitemap.xml") if rel in by_rel]
        for extension in (".css", ".js"):
            asset = next((r for r in sorted(by_rel) if r.startswith("_astro/") and r.endswith(extension)), None)
            if asset:
                samples.append(asset)
        for rel in samples:
            response = fetch("/" + rel)
            if response is None:
                continue
            with open(by_rel[rel].path, "rb") as fh:
                local_hash = sha(fh.read())
            if response.status != 200:
                failures.append(f"/{rel}: HTTP {response.status}")
            elif sha(response.body) != local_hash:
                failures.append(f"/{rel}: ausgelieferter Inhalt weicht vom Build ab")

        hidden = fetch("/.htaccess")
        if hidden is not None and hidden.status not in (403, 404):
            failures.append(f"/.htaccess ist öffentlich abrufbar (HTTP {hidden.status})")
        missing = fetch(f"/kd-check-{secrets.token_hex(8)}")
        if missing is not None and missing.status != 404:
            failures.append(f"Unbekannte Adresse liefert HTTP {missing.status} statt 404")

        if failures:
            raise DeployError(
                "Dateien sind hochgeladen (kein Rollback), aber die Nachprüfung per HTTPS schlug fehl:\n  "
                + "\n  ".join(failures)
            )
        self.log.info("HTTPS-Prüfung bestanden (Startseite, robots/sitemap, Assets, .htaccess geschützt, 404)")


# ------------------------------------------------------------------------------- CLI


def parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FTPS-Deployer: Standard ist ein rein lesender Plan; Schreiben nur mit --deploy."
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Build-Ordner (Standard: frontend/dist)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="nur lokale Prüfung, keine Verbindung")
    mode.add_argument("--deploy", action="store_true", help="Schreibmodus (erfordert DEPLOY_ENABLED=true)")
    parser.add_argument("--list-limit", type=int, default=25, help="max. Einträge pro Liste (0 = alle)")
    return parser.parse_args(argv)


def _offline_report(files: Sequence[LocalFile], env: Mapping[str, str], log: Log) -> None:
    total = sum(f.size for f in files)
    log.info(f"Build gültig: {len(files)} Dateien ({human_size(total)}), .htaccess und index.html vorhanden")
    counts = [sum(1 for f in files if _rank(f.rel) == rank) for rank in range(4)]
    log.info(
        "Upload-Reihenfolge: "
        f"{counts[0]} Assets → {counts[1]} HTML → {counts[2]} index.html → {counts[3]} .htaccess"
    )
    site_url = env.get("SITE_URL", "").strip()
    if site_url:
        check_build_origin(files, normalize_site_url(site_url))
        log.info(f"SITE_URL und Build-Origin passen zusammen ({normalize_site_url(site_url)})")
    else:
        log.info("SITE_URL nicht gesetzt: Origin-Prüfung übersprungen")
    remote_dir = env.get("FTP_REMOTE_DIR", "").strip()
    if remote_dir:
        log.info(f"FTP_REMOTE_DIR gültig: {normalize_remote_dir(remote_dir)}")
    log.info("Offline-Modus: keine Verbindung, keine Schreibvorgänge")


def main(
    argv: Optional[Sequence[str]] = None,
    env: Optional[Mapping[str, str]] = None,
    *,
    remote_factory=None,
    http=None,
    sleep=time.sleep,
) -> int:
    args = parse_args(argv)
    env = os.environ if env is None else env
    log = Log([env.get("FTP_PASSWORD", "")])
    scrubber = Log([env.get("FTP_PASSWORD", ""), env.get("FTP_USER", "").strip()])
    try:
        if args.deploy and env.get("DEPLOY_ENABLED") != "true":
            raise ConfigError("Schreibmodus gesperrt: DEPLOY_ENABLED muss exakt 'true' sein. Keine Verbindung aufgebaut")

        files = scan_build(args.source)
        if args.offline:
            _offline_report(files, env, log)
            return 0

        try:
            cfg = load_config(env)
        except ConfigError as exc:
            raise ConfigError(f"{exc}. Für eine rein lokale Prüfung --offline verwenden") from None
        check_build_origin(files, cfg.site_url)

        mode = "DEPLOY (Schreibmodus)" if args.deploy else "Plan (nur lesend)"
        log.info(f"Modus: {mode}")
        log.info(f"Ziel: ftps://{cfg.host}:{cfg.port}{cfg.remote_dir} → {cfg.site_url}")

        remote = (remote_factory or FtpsClient)(cfg)
        remote.connect()
        try:
            if args.deploy:
                Deployer(cfg, remote, http or http_get, log, sleep=sleep, list_limit=args.list_limit).deploy(files)
            else:
                Deployer(
                    cfg, ReadOnlyRemote(remote), http or http_get, log, sleep=sleep, list_limit=args.list_limit
                ).plan(files)
                log.info("Plan beendet: Es wurde nichts auf dem Server verändert.")
        finally:
            remote.close()
        return 0
    except ConfigError as exc:
        log.error(f"Konfigurationsfehler: {exc}")
        return 2
    except DeployError as exc:
        log.error(f"Fehler: {exc}")
        return 1
    except ssl.SSLCertVerificationError as exc:
        log.error(
            "Fehler: TLS-Zertifikat konnte nicht geprüft werden "
            f"(FTP_HOST muss zum Zertifikat passen): {scrubber.redact(str(exc))}"
        )
        return 1
    except ftplib.all_errors as exc:
        log.error(f"FTP-Fehler ({type(exc).__name__}): {scrubber.redact(str(exc))}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
