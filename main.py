"""Lightsalt OMR bridge. POST raw application/pdf to /convert; return JSON {musicxml: ...}."""
import hmac
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from defusedxml import ElementTree as SafeET
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Lightsalt OMR API", docs_url=None, redoc_url=None)
MAX_PDF_BYTES = int(os.getenv("MAX_PDF_MB", "25")) * 1024 * 1024
MAX_XML_BYTES = 12 * 1024 * 1024
OMR_TIMEOUT = int(os.getenv("OMR_TIMEOUT_SECONDS", "105"))


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "Audiveris", "configured": bool(os.getenv("OMR_API_KEY"))}


def find_audiveris():
    configured = os.getenv("AUDIVERIS_BIN", "").strip()
    candidates = [
        configured,
        shutil.which("Audiveris"),
        shutil.which("audiveris"),
        "/opt/audiveris/bin/Audiveris",
        "/usr/bin/audiveris",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise HTTPException(status_code=503, detail="Audiveris 실행 파일을 찾을 수 없습니다.")


def read_musicxml(output_dir: Path) -> str:
    candidates = sorted(
        (p for p in output_dir.rglob("*") if p.is_file() and p.suffix.lower() in (".mxl", ".xml", ".musicxml")),
        key=lambda p: (p.suffix.lower() != ".mxl", str(p))
    )
    for candidate in candidates:
        try:
            if candidate.suffix.lower() == ".mxl":
                with zipfile.ZipFile(candidate) as archive:
                    xml_members = [n for n in archive.namelist()
                                   if n.lower().endswith((".musicxml", ".xml"))
                                   and n != "META-INF/container.xml"
                                   and not n.startswith("META-INF/")]
                    if not xml_members:
                        continue
                    member = xml_members[0]
                    if archive.getinfo(member).file_size > MAX_XML_BYTES:
                        continue
                    content = archive.read(member)
            else:
                if candidate.stat().st_size > MAX_XML_BYTES:
                    continue
                content = candidate.read_bytes()
            root = SafeET.fromstring(content)
            local = root.tag.rsplit("}", 1)[-1]
            if local in ("score-partwise", "score-timewise"):
                return content.decode("utf-8-sig")
        except (ValueError, UnicodeError, OSError, zipfile.BadZipFile, SafeET.ParseError):
            continue
    raise HTTPException(status_code=422, detail="Audiveris가 유효한 MusicXML을 생성하지 못했습니다. 스캔 품질 또는 로그를 확인하세요.")


@app.post("/convert")
async def convert(request: Request):
    expected = os.getenv("OMR_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="서버의 OMR_API_KEY 환경변수가 설정되지 않았습니다.")
    supplied = request.headers.get("authorization", "")
    if not supplied.startswith("Bearer ") or not hmac.compare_digest(supplied[7:], expected):
        raise HTTPException(status_code=401, detail="OMR API 키가 올바르지 않습니다.")
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/pdf":
        raise HTTPException(status_code=415, detail="Content-Type은 application/pdf여야 합니다.")
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF 용량 제한 초과")
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="PDF 용량 제한 초과")
    if not payload.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="유효한 PDF 파일이 아닙니다.")
    engine = find_audiveris()
    with tempfile.TemporaryDirectory(prefix="lightsalt-omr-") as tmp:
        work = Path(tmp)
        input_pdf = work / "input.pdf"
        output_dir = work / "output"
        output_dir.mkdir()
        input_pdf.write_bytes(payload)
        # Audiveris CLI: -batch -export -output <dir> -- <file>
        command = [engine, "-batch", "-export", "-output", str(output_dir), "--", str(input_pdf)]
        try:
            proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=OMR_TIMEOUT, check=False, cwd=str(work))
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="악보 인식 시간이 초과되었습니다. 페이지 수를 줄여 주세요.")
        if proc.returncode != 0:
            # Do not expose full engine logs to unauthenticated visitors.
            print("Audiveris failed:", proc.stdout.decode("utf-8", errors="replace")[-3500:], flush=True)
            raise HTTPException(status_code=422, detail="Audiveris 인식에 실패했습니다. 서버 로그를 확인하세요.")
        musicxml = read_musicxml(output_dir)
        return JSONResponse({"musicxml": musicxml})
