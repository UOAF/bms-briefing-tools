#!/usr/bin/env python3
"""Upload a Claude design bundle through Anthropic's Files API."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any
from urllib import request


API_URL = "https://api.anthropic.com/v1/files"
FILES_BETA = "files-api-2025-04-14"
ANTHROPIC_VERSION = "2023-06-01"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def multipart_body(path: Path, mime_type: str) -> tuple[bytes, str]:
    boundary = f"----uoaf-bms-{uuid.uuid4().hex}"
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8")
    footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return header + path.read_bytes() + footer, boundary


def upload_file(path: Path, mime_type: str, api_key: str) -> dict[str, Any]:
    body, boundary = multipart_body(path, mime_type)
    req = request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "anthropic-beta": FILES_BETA,
            "content-type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def content_block(asset: dict[str, Any], file_id: str) -> dict[str, Any] | None:
    mime_type = str(asset.get("mime_type") or "")
    if mime_type.startswith("image/"):
        return {"type": "image", "source": {"type": "file", "file_id": file_id}}
    if mime_type == "text/plain":
        return {
            "type": "document",
            "source": {"type": "file", "file_id": file_id},
            "title": asset.get("name"),
            "context": asset.get("role"),
        }
    return {"type": "container_upload", "file_id": file_id}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True, help="Directory created by export_claude_design_bundle.py.")
    parser.add_argument("--api-key-env", default="ANTHROPIC_API_KEY", help="Environment variable containing the Anthropic API key.")
    parser.add_argument("--out", type=Path, help="Output upload manifest path.")
    parser.add_argument("--dry-run", action="store_true", help="Build the upload plan without calling the API.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundle_dir = args.bundle_dir.resolve()
    manifest_path = bundle_dir / "manifest.json"
    manifest = load_json(manifest_path)
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key and not args.dry_run:
        raise SystemExit(f"Missing API key environment variable: {args.api_key_env}")

    upload_records = []
    for asset in manifest.get("assets") or []:
        rel_path = Path(str(asset.get("path") or ""))
        path = bundle_dir / rel_path
        if not path.exists():
            raise SystemExit(f"Missing bundle asset: {path}")
        mime_type = str(asset.get("mime_type") or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        if path.suffix.lower() == ".json":
            mime_type = "text/plain"
        record = {"asset": asset, "path": str(path), "mime_type": mime_type}
        if not args.dry_run:
            response = upload_file(path, mime_type, api_key)
            record["file"] = response
            record["content_block"] = content_block(asset, response["id"])
        upload_records.append(record)

    prompt_path = bundle_dir / "claude_design_prompt.md"
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    image_blocks = [record.get("content_block") for record in upload_records if (record.get("content_block") or {}).get("type") == "image"]
    doc_blocks = [record.get("content_block") for record in upload_records if (record.get("content_block") or {}).get("type") == "document"]
    other_blocks = [record.get("content_block") for record in upload_records if (record.get("content_block") or {}).get("type") == "container_upload"]
    upload_manifest = {
        "schema": "uoaf.bms.claude_design_upload.v1",
        "bundle_dir": str(bundle_dir),
        "dry_run": args.dry_run,
        "betas": [FILES_BETA],
        "uploads": upload_records,
        "message_content": [
            *[block for block in image_blocks if block],
            *[block for block in doc_blocks if block],
            *[block for block in other_blocks if block],
            {"type": "text", "text": prompt},
        ],
    }
    out_path = args.out or (bundle_dir / "claude_files_manifest.json")
    out_path.write_text(json.dumps(upload_manifest, indent=2) + "\n", encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
