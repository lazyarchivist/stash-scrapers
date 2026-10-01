#!/usr/bin/env python3
"""Build a Stash scraper source: one zip per scraper plus an index.yml.

    python build.py _site/stable

Every directory under `scrapers/` is one package, named after the directory.
Its main file is `<id>.yml`; any other file in the directory ships with it.

The output mirrors the CommunityScrapers source that Stash already knows how to
read, checked against the live one:

  * each package is a zip holding the scraper's files at its root, no folder;
  * `index.yml` lists id, name, version, date, path, sha256, optionally
    `requires` and `metadata.scene_urls`; the sha256 is that of the zip.

`version` is the short hash of the last commit that touched the package's
directory, and `date` that commit's time, so Stash flags an update only for the
scrapers that actually changed. This needs the full git history (the workflow
checks out with fetch-depth 0); without git the version is "dev".

Zips are written deterministically (sorted entries, fixed timestamps), so an
unchanged scraper rebuilds to the same bytes and the same sha256.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
SCRAPERS = os.path.join(ROOT, "scrapers")
# A dependency on another package, declared the way CommunityScrapers does it.
_REQUIRES_RE = re.compile(r"^#\s*requires:\s*(\S+)", re.M)
# 1980-01-01 is the earliest timestamp a zip entry can hold.
_FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def git_version(path: str) -> tuple[str, str]:
    """(short hash, "YYYY-MM-DD HH:MM:SS" UTC) of the last commit touching path."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%h %ct", "--", path],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        out = []
    if len(out) != 2:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return "dev", now
    stamp = datetime.fromtimestamp(int(out[1]), timezone.utc)
    return out[0], stamp.strftime("%Y-%m-%d %H:%M:%S")


def scene_urls(cfg: dict) -> list[str]:
    urls: list[str] = []
    for entry in cfg.get("sceneByURL") or []:
        for u in entry.get("url") or []:
            if u not in urls:
                urls.append(u)
    return urls


def build_zip(src_dir: str, dest: str) -> str:
    """Zip src_dir's files at the archive root; return the zip's sha256."""
    files = sorted(
        f for f in os.listdir(src_dir)
        if os.path.isfile(os.path.join(src_dir, f)) and not f.startswith(".")
    )
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            info = zipfile.ZipInfo(name, date_time=_FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(os.path.join(src_dir, name), "rb") as fh:
                z.writestr(info, fh.read())
    with open(dest, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build(out_dir: str) -> list[dict]:
    os.makedirs(out_dir, exist_ok=True)
    index: list[dict] = []
    for pkg_id in sorted(os.listdir(SCRAPERS)):
        src = os.path.join(SCRAPERS, pkg_id)
        if not os.path.isdir(src):
            continue
        main = os.path.join(src, f"{pkg_id}.yml")
        if not os.path.isfile(main):
            raise SystemExit(f"{pkg_id}: missing {pkg_id}.yml")
        with open(main, encoding="utf-8") as fh:
            text = fh.read()
        cfg = yaml.safe_load(text)  # also rejects a scraper that isn't valid YAML
        name = (cfg or {}).get("name")
        if not name:
            raise SystemExit(f"{pkg_id}: {pkg_id}.yml has no 'name'")

        version, date = git_version(os.path.relpath(src, ROOT))
        sha = build_zip(src, os.path.join(out_dir, f"{pkg_id}.zip"))

        entry: dict = {
            "id": pkg_id,
            "name": name,
            "version": version,
            "date": date,
            "path": f"{pkg_id}.zip",
            "sha256": sha,
        }
        requires = _REQUIRES_RE.findall(text)
        if requires:
            entry["requires"] = requires
        urls = scene_urls(cfg)
        if urls:
            entry["metadata"] = {"scene_urls": urls}
        index.append(entry)
        print(f"{pkg_id:20} {version:8} {sha[:12]}  {', '.join(urls)}")

    with open(os.path.join(out_dir, "index.yml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump(index, fh, sort_keys=False, allow_unicode=True)
    return index


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: build.py OUTPUT_DIR")
    build(sys.argv[1])
