import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from routes.chat import get_current_user
from filter.engine import ContentFilter
from filter.scanners import extract_text_from_csv, extract_text_from_xlsx
from config import settings

router = APIRouter(prefix="/api/files")

_filter = ContentFilter(settings.content_filter_path)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = os.path.splitext(file.filename or "")[1].lower()

    if not _filter.is_file_type_allowed(ext):
        raise HTTPException(status_code=400, detail={
            "error": "file_type_not_allowed",
            "message": f"File type '{ext}' is not allowed. Allowed: {_filter.config.allowed_file_types}",
        })

    content = await file.read()

    extracted_text = ""
    if ext == ".csv":
        extracted_text = extract_text_from_csv(content)
    elif ext == ".xlsx":
        extracted_text = extract_text_from_xlsx(content)
    elif ext in (".txt", ".pdf"):
        extracted_text = content.decode("utf-8", errors="replace")

    if extracted_text:
        result = _filter.scan_text(extracted_text)
        if result.blocked:
            raise HTTPException(status_code=403, detail={
                "error": "content_filtered",
                "message": result.message,
                "rule": result.rule,
            })

    return {
        "file_name": file.filename,
        "file_content": extracted_text,
        "size": len(content),
    }
