"""Abstração de armazenamento de arquivos (fotos de pacientes, PDFs
gerados). Por padrão tudo fica em disco local (`backend/storage/...`,
comportamento de sempre); se as variáveis `S3_*` forem configuradas, os
mesmos arquivos passam a ir para um bucket compatível com S3 (AWS,
Cloudflare R2, Backblaze B2...) — sem precisar trocar nada no resto do
código, que só conhece `Storage.save`/`.read`/`.delete`/`.exists`.

As colunas do banco (`PatientPhoto.file_path`, `Report.pdf_path`) passam a
guardar uma **chave lógica** (ex.: `"{patient_id}/{uuid}.jpg"`), não um
caminho absoluto de disco — funciona igual nos dois backends."""

import abc
from pathlib import Path

from app.core.config import settings


class Storage(abc.ABC):
    @abc.abstractmethod
    def save(self, key: str, content: bytes) -> None: ...

    @abc.abstractmethod
    def read(self, key: str) -> bytes: ...

    @abc.abstractmethod
    def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalDiskStorage(Storage):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def _path(self, key: str) -> Path:
        return self.base_dir / key

    def save(self, key: str, content: bytes) -> None:
        caminho = self._path(key)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(content)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


class S3Storage(Storage):
    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "",
        endpoint_url: str | None = None,
        region: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        import boto3  # import local: só exigido quando S3 está configurado

        self._bucket = bucket
        self._prefix = prefix
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or None,
            region_name=region or None,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
        )

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}" if self._prefix else key

    def save(self, key: str, content: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=self._full_key(key), Body=content)

    def read(self, key: str) -> bytes:
        objeto = self._client.get_object(Bucket=self._bucket, Key=self._full_key(key))
        return objeto["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=self._full_key(key))

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self._bucket, Key=self._full_key(key))
            return True
        except ClientError:
            return False


_LOCAL_STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage"


def _build_storage(subpasta: str) -> Storage:
    if settings.s3_bucket:
        return S3Storage(
            bucket=settings.s3_bucket,
            prefix=f"{subpasta}/",
            endpoint_url=settings.s3_endpoint_url,
            region=settings.s3_region,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
        )
    return LocalDiskStorage(_LOCAL_STORAGE_ROOT / subpasta)


def get_photos_storage() -> Storage:
    return _build_storage("photos")


def get_reports_storage() -> Storage:
    return _build_storage("reports")
