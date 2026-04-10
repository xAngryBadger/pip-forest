import os
import shutil
from typing import List

try:
    from azure.storage.blob import BlobServiceClient
except Exception:
    BlobServiceClient = None


class Storage:
    def __init__(self):
        self.use_blob = os.environ.get("SRF_USE_AZURE_BLOB", "0").strip() in ("1", "true", "yes", "on")
        self.conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "").strip()
        self.container = os.environ.get("AZURE_STORAGE_CONTAINER", "srf-pilot").strip()
        self._blob = None
        if self.use_blob and self.conn and BlobServiceClient is not None:
            self._blob = BlobServiceClient.from_connection_string(self.conn)
            try:
                self._blob.create_container(self.container)
            except Exception:
                pass

    def enabled_blob(self) -> bool:
        return self._blob is not None

    def upload_if_enabled(self, local_path: str, blob_name: str) -> None:
        if not self.enabled_blob():
            return
        with open(local_path, "rb") as f:
            bc = self._blob.get_blob_client(container=self.container, blob=blob_name)
            bc.upload_blob(f, overwrite=True)

    def download_if_enabled(self, blob_name: str, local_path: str) -> bool:
        if not self.enabled_blob():
            return False
        try:
            bc = self._blob.get_blob_client(container=self.container, blob=blob_name)
            data = bc.download_blob().readall()
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
            return True
        except Exception:
            return False

    def list_blobs_if_enabled(self, prefix: str) -> List[str]:
        if not self.enabled_blob():
            return []
        out = []
        for b in self._blob.get_container_client(self.container).list_blobs(name_starts_with=prefix):
            out.append(b.name)
        return sorted(out)


def safe_copy(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)

