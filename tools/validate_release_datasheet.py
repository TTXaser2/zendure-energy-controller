#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate the canonical technical datasheet shipped with a ZEC release.

Stdlib-only by design so the package/installer preflight can run on the
productive controller without adding a runtime dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile

REQUIRED_TEXT = (
    "Technische Voraussetzungen und Anlagenkonstellationen",
    "Hardware und Infrastruktur",
    "Software und Dienste",
    "Anlagenkonstellationen und Unterstützungsstatus",
    "SMA Energy Meter",
    "Speedwire/UDP",
    "Shelly Pro 3EM",
    "Shelly-kompatibler HTTP",
)
RELEASE_RE = re.compile(r"V\d+\.\d+\.\d+")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _docx_text(path: Path) -> str:
    with ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.startswith("word/") and n.endswith(".xml")]
        xml = "\n".join(zf.read(n).decode("utf-8", errors="ignore") for n in names)
    # DOCX XML is sufficient for release markers/required phrases after entity normalization.
    return re.sub(r"<[^>]+>", "", xml).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


def validate(root: Path) -> dict:
    from version import APP_BUILD_ID, APP_VERSION, APP_VERSION_LABEL

    root = root.resolve()
    docs = root / "docs"
    pdf = docs / "ZEC_Technisches_Datenblatt.pdf"
    docx = docs / "ZEC_Technisches_Datenblatt.docx"
    meta_path = docs / "ZEC_Technisches_Datenblatt.release.json"
    errors: list[str] = []

    for p in (pdf, docx, meta_path):
        if not p.is_file():
            errors.append(f"MISSING:{p.relative_to(root)}")
        elif p.stat().st_size <= 0:
            errors.append(f"EMPTY:{p.relative_to(root)}")
    if errors:
        return {"status": "FAIL", "errors": errors}

    if pdf.stat().st_size < 20_000 or pdf.read_bytes()[:5] != b"%PDF-":
        errors.append("PDF_INVALID_OR_IMPLAUSIBLY_SMALL")
    if docx.stat().st_size < 20_000:
        errors.append("DOCX_IMPLAUSIBLY_SMALL")

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "FAIL", "errors": [f"METADATA_INVALID:{exc}"]}

    expected = {
        "release_version": APP_VERSION,
        "release_label": APP_VERSION_LABEL,
        "build_id": APP_BUILD_ID,
    }
    for key, value in expected.items():
        if meta.get(key) != value:
            errors.append(f"METADATA_{key.upper()}_MISMATCH:{meta.get(key)!r}!={value!r}")
    for key, path in (("docx_sha256", docx), ("pdf_sha256", pdf)):
        actual = _sha256(path)
        if meta.get(key) != actual:
            errors.append(f"METADATA_{key.upper()}_MISMATCH")

    try:
        text = _docx_text(docx)
    except Exception as exc:
        errors.append(f"DOCX_READ_ERROR:{exc}")
        text = ""
    if APP_VERSION_LABEL not in text:
        errors.append("DOCX_CURRENT_RELEASE_LABEL_MISSING")
    if APP_BUILD_ID not in text:
        errors.append("DOCX_CURRENT_BUILD_ID_MISSING")
    for phrase in REQUIRED_TEXT:
        if phrase not in text:
            errors.append(f"DOCX_REQUIRED_TEXT_MISSING:{phrase}")
    identities = sorted(set(RELEASE_RE.findall(text)))
    stale = [v for v in identities if v != APP_VERSION_LABEL]
    if stale:
        errors.append("DOCX_STALE_RELEASE_IDENTITIES:" + ",".join(stale))

    manifest = root / f"V{APP_VERSION.replace('.', '_')}_SOURCE_MANIFEST.sha256"
    if manifest.is_file():
        manifest_text = manifest.read_text(encoding="utf-8", errors="ignore")
        for rel in (
            "./docs/ZEC_Technisches_Datenblatt.pdf",
            "./docs/ZEC_Technisches_Datenblatt.docx",
            "./docs/ZEC_Technisches_Datenblatt.release.json",
        ):
            if rel not in manifest_text:
                errors.append(f"SOURCE_MANIFEST_ENTRY_MISSING:{rel}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "release": expected,
        "datasheet": {
            "pdf": str(pdf.relative_to(root)), "pdf_bytes": pdf.stat().st_size, "pdf_sha256": _sha256(pdf),
            "docx": str(docx.relative_to(root)), "docx_bytes": docx.stat().st_size, "docx_sha256": _sha256(docx),
            "metadata": str(meta_path.relative_to(root)),
        },
        "release_identities_in_docx": identities,
        "required_text_count": len(REQUIRED_TEXT),
        "errors": errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate ZEC release datasheet")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    if str(root.resolve()) not in sys.path:
        sys.path.insert(0, str(root.resolve()))
    result = validate(root)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"DATASHEET_GATE={result['status']}")
        for error in result.get("errors", []):
            print(f"ERROR={error}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
