"""Install the bundled font catalog (`app/pdf_engine/font_catalog.py`) from
its lockfile, `scripts/fonts.lock.json`.

Only Liberation and Open Sans are committed to the repo; everything else is
downloaded by this script (run by the Docker build, and once locally):

    .venv/bin/python scripts/fetch_fonts.py                 # install from the lockfile
    .venv/bin/python scripts/fetch_fonts.py roboto lato     # only these directories
    .venv/bin/python scripts/fetch_fonts.py --refresh       # re-resolve sources, rewrite the lockfile

Install mode downloads each file from the exact URL recorded in the
lockfile and refuses it unless its SHA-256 matches: these files are parsed
by FreeType/MuPDF at runtime, so a tampered download (a compromised
mirror -- mirrors.ctan.org redirects to third-party mirrors -- or a moved
branch) must never reach the image. An integrity failure always exits
non-zero; a network failure only does without --allow-missing (the backend
degrades to the next closest family when one is missing).

Refresh mode is the only place where sources are trusted on first use: it
resolves every family's source again (Google Fonts CSS API, pinned GitHub
commits/releases, CTAN), downloads, hashes and rewrites the lockfile. Review
its diff like any other dependency bump.

Google Fonts' CSS API serves full static TTF instances (not unicode-range
subsets) to a client that doesn't advertise WOFF2 support; its font URLs
are versioned (".../s/roboto/v48/...") so the recorded URL keeps serving
the same bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.pdf_engine.font_catalog import (  # noqa: E402
    CATALOG,
    FontFamily,
    GoogleSource,
    Style,
    UrlSource,
    ZipSource,
)

FONTS_DIR = BACKEND / "app" / "fonts"
LOCKFILE = BACKEND / "scripts" / "fonts.lock.json"
# License files for Google families, read from a pinned google/fonts commit.
GOOGLE_FONTS_COMMIT = "9710da1eacb3be272583c3224dcb70f9da6eadbb"
GOOGLE_LICENSE_PATHS = ("ofl/{slug}/OFL.txt", "apache/{slug}/LICENSE.txt", "ufl/{slug}/UFL.txt")

# python.org's macOS builds ship without any CA bundle configured; fall
# back to the system one there instead of requiring `Install Certificates`.
_SSL = ssl.create_default_context()
if not _SSL.get_ca_certs() and Path("/etc/ssl/cert.pem").is_file():
    _SSL = ssl.create_default_context(cafile="/etc/ssl/cert.pem")

_zip_cache: dict[str, zipfile.ZipFile] = {}


class IntegrityError(Exception):
    pass


def _get(url: str, attempts: int = 4) -> bytes:
    # No User-Agent on purpose: that's what makes the Google Fonts CSS API
    # answer with plain TTF URLs.
    req = urllib.request.Request(url, headers={"User-Agent": ""})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60, context=_SSL) as resp:
                return resp.read()
        except urllib.error.HTTPError:
            raise  # a real answer (404, 400): retrying won't change it
        except Exception:
            # mirrors.ctan.org redirects to a random mirror, some of which
            # have broken TLS -- a retry usually lands on a healthy one.
            # Certificate verification itself is never relaxed.
            if attempt == attempts - 1:
                raise
            time.sleep(1 + attempt)
    raise AssertionError("unreachable")


def _zip_member(url: str, member: str) -> bytes:
    if url not in _zip_cache:
        _zip_cache[url] = zipfile.ZipFile(io.BytesIO(_get(url)))
    return _zip_cache[url].read(member)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _directory_of(rel_path: str) -> str:
    return rel_path.split("/", 1)[0]


# --- install ---------------------------------------------------------------


def _install_entry(rel_path: str, entry: dict) -> str:
    target = FONTS_DIR / rel_path
    if target.is_file() and _sha256(target.read_bytes()) == entry["sha256"]:
        return "ok"
    data = _zip_member(entry["url"], entry["member"]) if "member" in entry else _get(entry["url"])
    if _sha256(data) != entry["sha256"]:
        # Whatever is on disk didn't match either: don't leave it for the
        # backend to load.
        target.unlink(missing_ok=True)
        raise IntegrityError(f"{rel_path}: SHA-256 mismatch for {entry['url']}")
    _write_atomic(target, data)
    return "downloaded"


def install(directories: set[str], allow_missing: bool) -> int:
    entries = json.loads(LOCKFILE.read_text())["files"]
    groups: dict[str, list[tuple[str, dict]]] = {}
    for rel_path, entry in entries.items():
        if not directories or _directory_of(rel_path) in directories:
            groups.setdefault(_directory_of(rel_path), []).append((rel_path, entry))

    integrity_failures: list[str] = []
    network_failures: list[str] = []

    def run(group: list[tuple[str, dict]]) -> None:
        for rel_path, entry in group:
            try:
                if _install_entry(rel_path, entry) == "downloaded":
                    print(f"  {rel_path}")
            except IntegrityError as e:
                integrity_failures.append(str(e))
            except Exception as e:  # noqa: BLE001 - report every failure, keep going
                network_failures.append(f"{rel_path}: {e}")

    # One thread per directory: files sharing a zip archive stay together.
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(run, groups.values()))

    total = sum(len(g) for g in groups.values())
    print(f"{total - len(integrity_failures) - len(network_failures)}/{total} font files installed and verified")
    for failure in network_failures:
        print(f"  DOWNLOAD FAILED: {failure}")
    for failure in integrity_failures:
        print(f"  INTEGRITY FAILURE (file rejected): {failure}")
    if integrity_failures:
        return 2
    if network_failures and not allow_missing:
        return 1
    return 0


# --- refresh -----------------------------------------------------------------


def _google_style_url(family: str, style: Style) -> str | None:
    bold, italic = style
    query = urllib.parse.quote(family) + f":ital,wght@{int(italic)},{700 if bold else 400}"
    try:
        css = _get(f"https://fonts.googleapis.com/css2?family={query}").decode()
    except urllib.error.HTTPError as exc:
        if exc.code == 400:  # style not offered by this family
            return None
        raise
    match = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css)
    return match.group(1) if match else None


def _google_license_url(family: str) -> str | None:
    slug = re.sub(r"[^a-z0-9]", "", family.lower())
    for path in GOOGLE_LICENSE_PATHS:
        url = f"https://raw.githubusercontent.com/google/fonts/{GOOGLE_FONTS_COMMIT}/" + path.format(slug=slug)
        try:
            _get(url)
            return url
        except urllib.error.HTTPError:
            continue
    return None


def _resolve(family: FontFamily) -> dict[str, dict]:
    """rel_path -> {url, [member]} for every file of `family` its source offers."""
    source = family.source
    resolved: dict[str, dict] = {}
    for style, filename in family.files.items():
        rel_path = f"{family.directory}/{filename}"
        if isinstance(source, GoogleSource):
            url = _google_style_url(source.family, style)
            if url:
                resolved[rel_path] = {"url": url}
        elif isinstance(source, UrlSource):
            resolved[rel_path] = {"url": source.urls[style]}
        elif isinstance(source, ZipSource):
            resolved[rel_path] = {"url": source.url, "member": source.members[style]}

    license_path = f"{family.directory}/{family.license_file}"
    if isinstance(source, GoogleSource):
        url = _google_license_url(source.family)
        if url:
            resolved[license_path] = {"url": url}
    elif isinstance(source, UrlSource):
        resolved[license_path] = {"url": source.license_url}
    elif source.license_member:
        resolved[license_path] = {"url": source.url, "member": source.license_member}
    else:
        resolved[license_path] = {"url": source.license_url}
    return resolved


def refresh(directories: set[str]) -> int:
    previous = json.loads(LOCKFILE.read_text())["files"] if LOCKFILE.is_file() else {}
    families = [f for f in CATALOG if f.source is not None and (not directories or f.directory in directories)]
    groups: dict[str, list[FontFamily]] = {}
    for family in families:
        groups.setdefault(family.directory, []).append(family)

    new_entries: dict[str, dict] = {}
    failures: list[str] = []

    def run(group: list[FontFamily]) -> None:
        for family in group:
            try:
                for rel_path, entry in _resolve(family).items():
                    data = _zip_member(entry["url"], entry["member"]) if "member" in entry else _get(entry["url"])
                    _write_atomic(FONTS_DIR / rel_path, data)
                    new_entries[rel_path] = {**entry, "sha256": _sha256(data)}
                print(f"  {family.key}")
            except Exception as e:  # noqa: BLE001
                failures.append(f"{family.key}: {e}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(run, groups.values()))

    refreshed_dirs = set(groups)
    kept = {p: e for p, e in previous.items() if _directory_of(p) not in refreshed_dirs}
    files = dict(sorted({**kept, **new_entries}.items()))
    LOCKFILE.write_text(json.dumps({"files": files}, indent=1) + "\n")
    print(f"lockfile: {len(files)} files")
    for failure in failures:
        print(f"  FAILED: {failure}")
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("directories", nargs="*", help="only these font directories")
    parser.add_argument("--refresh", action="store_true", help="re-resolve sources and rewrite the lockfile")
    parser.add_argument(
        "--allow-missing", action="store_true", help="exit 0 when downloads fail (integrity failures still fail)"
    )
    args = parser.parse_args()
    directories = set(args.directories)
    sys.exit(refresh(directories) if args.refresh else install(directories, args.allow_missing))


if __name__ == "__main__":
    main()
