from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from PIL import Image
import pandas as pd

from app.core.errors import EmptyFileError, FileTooLargeError, InvalidMimeError, PolicyDeniedError, UnsupportedFileError
from app.core.policies import safe_filename


def upload(name: str, data: bytes, mime="application/octet-stream"):
    return UploadFile(filename=name, file=BytesIO(data), headers={"content-type": mime})


@pytest.mark.asyncio
async def test_file_upload_csv(files, workspace):
    session = workspace.create(); record = await files.save_upload(upload("sales.csv", b"a,b\n1,2\n", "text/csv"), session.conversation_id)
    assert record.kind == "table" and files.path_for(record).exists()


@pytest.mark.asyncio
async def test_file_upload_json(files, workspace):
    session = workspace.create(); record = await files.save_upload(upload("metrics.json", b"[{\"x\":1}]", "application/json"), session.conversation_id)
    assert record.kind == "json"


@pytest.mark.asyncio
async def test_file_upload_png(files, workspace):
    image = Image.new("RGB", (20, 20), "red"); memory = BytesIO(); image.save(memory, "PNG")
    record = await files.save_upload(upload("chart.png", memory.getvalue(), "image/png"), workspace.create().conversation_id)
    assert record.kind == "image"


@pytest.mark.asyncio
async def test_file_upload_jpeg(files, workspace):
    image = Image.new("RGB", (20, 20), "red"); memory = BytesIO(); image.save(memory, "JPEG")
    record = await files.save_upload(upload("chart.jpg", memory.getvalue(), "image/jpeg"), workspace.create().conversation_id)
    assert record.extension == ".jpg"


@pytest.mark.asyncio
async def test_file_upload_xlsx(files, workspace):
    memory = BytesIO(); pd.DataFrame({"revenue": [10, 20]}).to_excel(memory, index=False)
    record = await files.save_upload(upload("marketing.xlsx", memory.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), workspace.create().conversation_id)
    assert record.extension == ".xlsx"


@pytest.mark.asyncio
async def test_malformed_xlsx_rejected(files, workspace):
    with pytest.raises(InvalidMimeError): await files.save_upload(upload("bad.xlsx", b"not-a-zip"), workspace.create().conversation_id)


@pytest.mark.asyncio
async def test_size_limit(files, workspace):
    files.settings = files.settings.__class__(storage_root=files.settings.storage_root, max_file_size=4)
    with pytest.raises(FileTooLargeError): await files.save_upload(upload("x.csv", b"a,b\n1,2\n"), workspace.create().conversation_id)


@pytest.mark.asyncio
async def test_empty_rejected(files, workspace):
    with pytest.raises(EmptyFileError): await files.save_upload(upload("x.csv", b""), workspace.create().conversation_id)


@pytest.mark.asyncio
async def test_invalid_mime_rejected(files, workspace):
    with pytest.raises(InvalidMimeError): await files.save_upload(upload("x.png", b"not-image", "image/png"), workspace.create().conversation_id)


@pytest.mark.asyncio
async def test_extension_rejected(files, workspace):
    with pytest.raises(UnsupportedFileError): await files.save_upload(upload("x.exe", b"MZ"), workspace.create().conversation_id)


def test_path_traversal_rejected():
    assert safe_filename("../../secret.csv") == "secret.csv"
    with pytest.raises(PolicyDeniedError): safe_filename("..")
