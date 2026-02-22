# fire/utils/geoserver.py
import requests


class GeoServerManager:
    """
    Reliable publishing:
      - Django downloads GeoTIFF from MinIO (internal URL)
      - Django uploads bytes to GeoServer via REST file.geotiff
    This avoids GeoServer REST limitations around external URL inputs.
    """

    def __init__(self, base_url: str, username: str, password: str, workspace: str):
        self.base_url = (base_url or "").rstrip("/")
        self.auth = (username, password)
        self.workspace = workspace

        if not self.base_url:
            raise ValueError("GeoServer base_url is empty")
        if not username or not password:
            raise ValueError("GeoServer username/password is empty")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def ensure_workspace(self) -> None:
        ws = self.workspace

        r = requests.get(self._url(f"/rest/workspaces/{ws}.json"), auth=self.auth, timeout=30)
        if r.status_code == 200:
            return
        if r.status_code != 404:
            raise Exception(f"Workspace check failed (HTTP {r.status_code}): {r.text}")

        payload = {"workspace": {"name": ws}}
        r = requests.post(
            self._url("/rest/workspaces"),
            json=payload,
            auth=self.auth,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if r.status_code not in (200, 201):
            raise Exception(f"Workspace creation failed (HTTP {r.status_code}): {r.text}")

    def delete_coveragestore_if_exists(self, store_name: str) -> None:
        """
        If a previous failed attempt left a broken store, remove it.
        """
        ws = self.workspace
        r = requests.delete(
            self._url(f"/rest/workspaces/{ws}/coveragestores/{store_name}?recurse=true&purge=all"),
            auth=self.auth,
            timeout=60,
        )
        # 200/202 = deleted, 404 = not exists (ok)
        if r.status_code in (200, 202, 404):
            return
        raise Exception(f"Delete coveragestore failed (HTTP {r.status_code}): {r.text}")

    def publish_geotiff_bytes(
        self,
        geotiff_bytes: bytes,
        store_name: str,
        layer_name: str,
        configure: str = "first",
    ) -> None:
        """
        Upload GeoTIFF bytes directly to GeoServer.
        This auto-creates the store + coverage + layer.
        """
        ws = self.workspace
        self.ensure_workspace()

        # If store exists from previous attempt, delete it to avoid conflicts.
        # (This makes retries deterministic)
        self.delete_coveragestore_if_exists(store_name)

        # Important: use file.geotiff endpoint
        # coverageName helps ensure deterministic layer naming
        put_url = self._url(
            f"/rest/workspaces/{ws}/coveragestores/{store_name}/file.geotiff"
            f"?configure={configure}&coverageName={layer_name}"
        )

        r = requests.put(
            put_url,
            data=geotiff_bytes,
            auth=self.auth,
            headers={"Content-Type": "image/tiff"},
            timeout=300,
        )

        if r.status_code not in (200, 201):
            raise Exception(
                f"PUT {put_url} failed (HTTP {r.status_code}): {r.text}"
            )

    def publish_geotiff_from_minio(
        self,
        minio_internal_url: str,
        store_name: str,
        layer_name: str,
    ) -> None:
        """
        1) GET GeoTIFF from MinIO (internal URL)
        2) PUT bytes to GeoServer
        """
        # Download from MinIO
        rr = requests.get(minio_internal_url, stream=True, timeout=300)
        if rr.status_code != 200:
            raise Exception(
                f"MinIO download failed (HTTP {rr.status_code}): {minio_internal_url}"
            )

        content = rr.content  # (برای فایل‌های خیلی بزرگ میشه stream کرد؛ فعلاً پایدار و ساده)
        if not content or len(content) < 1024:
            raise Exception("MinIO returned empty/too-small content (GeoTIFF bytes).")

        self.publish_geotiff_bytes(
            geotiff_bytes=content,
            store_name=store_name,
            layer_name=layer_name,
            configure="first",
        )