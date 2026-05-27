"""Document-upload router."""

import os
import re
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.events import bus, Event, EventType
from app.core.perm import require_owner
from app.core.security import get_current_user
from app.schemas.document import DocumentOut
from db.models import Document, DocumentStatus, DocumentType, User
from db.session import get_db

router = APIRouter(prefix="/documents", tags=["documents"])


def _sanitize_filename(filename: str) -> str:
    """Strip path separators and collapse repeated separators into single underscore.

    Preserves the file extension so uploaded files remain recognisable.
    """
    name = os.path.basename(filename)
    base, ext = os.path.splitext(name)
    safe_base = re.sub(r"[^a-zA-Z0-9]", "_", base)
    safe_base = re.sub(r"_{2,}", "_", safe_base).strip("_")
    return f"{safe_base}{ext}"


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Upload a document file (W2, 1099, 1098, reimbursement receipt)."""
    if file.size > settings.max_upload_size:
        raise HTTPException(status_code=413, detail="File too large")

    filename = file.filename or "upload"
    safe_name = _sanitize_filename(filename)

    if "w2" in filename.lower():
        doc_type = DocumentType.FORM_W2
    elif "1099" in filename.lower():
        doc_type = DocumentType.FORM_1099
    elif "1098" in filename.lower():
        doc_type = DocumentType.FORM_1098
    elif "receipt" in filename.lower():
        doc_type = DocumentType.REIMBURSEMENT_RECEIPT
    else:
        doc_type = DocumentType.OTHER

    storage_name = f"{uuid.uuid4().hex}_{safe_name}"

    # --- Persist DB row BEFORE writing file so orphaned files are avoided ---
    doc = Document(
        user_id=current_user.id,
        doc_type=doc_type,
        storage_filename=storage_name,
        status=DocumentStatus.UPLOADED,
    )
    session.add(doc)
    await session.flush()
    await session.refresh(doc)

    # Persist file to uploads dir
    target = settings.uploads_path / storage_name
    with target.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Emit event via module-level singleton
    await bus.emit(Event(
        type=EventType.DOCUMENT_UPLOADED,
        payload={"doc_id": doc.id, "storage": storage_name},
    ))

    return doc


@router.get("/list")
async def list_documents(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents for the authenticated user."""
    from sqlalchemy import select
    rows = await session.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.id)
    )
    return rows.scalars().all()


@router.get("/{id}", response_model=DocumentOut)
async def get_document(
    doc: Document = Depends(require_owner(Document)),
):
    """Get a single document — ownership verified by the dependency."""
    return doc


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc: Document = Depends(require_owner(Document)),
    session: AsyncSession = Depends(get_db),
):
    """Delete a document and its file — ownership verified by the dependency."""
    await session.delete(doc)
    await session.flush()
