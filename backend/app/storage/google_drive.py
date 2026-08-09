"""Google Drive storage — STUB, not wired up yet.

This is intentionally not functional. It documents the shape the real
implementation will need so the generation service can adopt it later
with zero changes outside this file.

To make this real you will need:
  1. A Google Cloud service account with the Drive API enabled.
  2. The service account's JSON key, injected as a secret (never
     committed) — e.g. GOOGLE_SERVICE_ACCOUNT_JSON as an env var holding
     the key content, or a path to a mounted secret file.
  3. The target Drive folder ID (the "Nuit Blanche" root folder),
     shared with the service account's email address as an Editor.
  4. The `google-api-python-client` and `google-auth` packages
     (deliberately not in requirements.txt yet — add them once this
     is implemented).
  5. Folder-per-year / folder-per-week creation logic mirroring
     LocalStorageProvider's directory layout, using
     `drive.files().create(body={"mimeType": "application/vnd.google-apps.folder", ...})`.
  6. Resumable media upload for each PNG and the ZIP via
     `MediaFileUpload`, then a returned webViewLink for each file.
  7. Rate-limit / retry handling (Drive API quotas) and cleanup of
     partial uploads on failure.
"""

from __future__ import annotations

from pathlib import Path

from app.storage.base import StorageProvider, StoredGeneration


class GoogleDriveStorageProvider(StorageProvider):
    """Not implemented. Raises immediately so it can never be silently used."""

    def __init__(self, *, folder_id: str) -> None:
        self._folder_id = folder_id

    def store(
        self,
        *,
        generation_id: str,
        city: str,
        week_number: int,
        year: int,
        png_paths: list[Path],
        assets_dir: Path,
        manifest_path: Path,
        zip_path: Path,
    ) -> StoredGeneration:
        del generation_id, city, week_number, year, png_paths, assets_dir, manifest_path, zip_path
        raise NotImplementedError(
            "GoogleDriveStorageProvider is a stub. See module docstring for what's "
            "needed to implement it, then wire it in via app/core/config.py."
        )
