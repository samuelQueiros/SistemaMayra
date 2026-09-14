from unittest.mock import MagicMock

import app.services.storage as storage_module
from app.services.storage import LocalDiskStorage, S3Storage, get_photos_storage, get_reports_storage


def test_local_disk_storage_salva_le_e_apaga(tmp_path):
    storage = LocalDiskStorage(tmp_path)

    storage.save("pasta/arquivo.txt", b"conteudo de teste")

    assert storage.exists("pasta/arquivo.txt")
    assert storage.read("pasta/arquivo.txt") == b"conteudo de teste"

    storage.delete("pasta/arquivo.txt")

    assert not storage.exists("pasta/arquivo.txt")


def test_sem_s3_configurado_usa_disco_local(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_module.settings, "s3_bucket", None)
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path)

    assert isinstance(get_photos_storage(), LocalDiskStorage)
    assert isinstance(get_reports_storage(), LocalDiskStorage)


def test_com_s3_bucket_configurado_usa_s3storage(monkeypatch):
    monkeypatch.setattr(storage_module.settings, "s3_bucket", "meu-bucket-de-teste")
    monkeypatch.setattr(storage_module.settings, "s3_endpoint_url", None)
    monkeypatch.setattr(storage_module.settings, "s3_region", None)
    monkeypatch.setattr(storage_module.settings, "s3_access_key", None)
    monkeypatch.setattr(storage_module.settings, "s3_secret_key", None)

    cliente_falso = MagicMock()
    boto3_falso = MagicMock()
    boto3_falso.client.return_value = cliente_falso
    monkeypatch.setitem(__import__("sys").modules, "boto3", boto3_falso)

    storage = get_photos_storage()

    assert isinstance(storage, S3Storage)
    assert storage._bucket == "meu-bucket-de-teste"
    assert storage._prefix == "photos/"


def test_s3storage_save_read_delete_chamam_o_cliente_boto3_com_a_chave_certa(monkeypatch):
    cliente_falso = MagicMock()
    cliente_falso.get_object.return_value = {"Body": MagicMock(read=lambda: b"bytes-do-s3")}
    boto3_falso = MagicMock()
    boto3_falso.client.return_value = cliente_falso
    monkeypatch.setitem(__import__("sys").modules, "boto3", boto3_falso)

    storage = S3Storage(bucket="bucket-x", prefix="reports/")

    storage.save("abc.pdf", b"conteudo")
    cliente_falso.put_object.assert_called_once_with(Bucket="bucket-x", Key="reports/abc.pdf", Body=b"conteudo")

    conteudo = storage.read("abc.pdf")
    cliente_falso.get_object.assert_called_once_with(Bucket="bucket-x", Key="reports/abc.pdf")
    assert conteudo == b"bytes-do-s3"

    storage.delete("abc.pdf")
    cliente_falso.delete_object.assert_called_once_with(Bucket="bucket-x", Key="reports/abc.pdf")
