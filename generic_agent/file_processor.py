"""
File Processor Module for Generic Chat Agent

Provides document processing for PDF, TXT, MD, and DOCX files
with extraction progress tracking.

Author: Cavin Otieno
"""

import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class ProcessingResult(BaseModel):
    """File processing result model."""
    filename: str
    file_type: str
    content: str
    char_count: int
    success: bool = True
    error: Optional[str] = None


class FileProcessor:
    """Document file processor with multi-format support."""

    SUPPORTED_FORMATS = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "md": "text/markdown",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    def __init__(self):
        """Initialize the file processor."""
        self._pdf_available = self._check_dependency("PyPDF2")
        self._docx_available = self._check_dependency("docx")

    def _check_dependency(self, module_name: str) -> bool:
        """Check if a dependency is available."""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False

    def get_supported_formats(self) -> dict[str, str]:
        """
        Get supported file formats.

        Returns:
            Dictionary of format to MIME type
        """
        return self.SUPPORTED_FORMATS.copy()

    def process_file(
        self,
        file_path: str,
        filename: str
    ) -> ProcessingResult:
        """
        Process a file and extract its content.

        Args:
            file_path: Path to the file
            filename: Original filename

        Returns:
            Processing result with extracted content
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        try:
            if ext == "pdf":
                return self._process_pdf(file_path, filename)
            elif ext in ("txt", "md"):
                return self._process_text(file_path, filename, ext)
            elif ext == "docx":
                return self._process_docx(file_path, filename)
            else:
                return ProcessingResult(
                    filename=filename,
                    file_type=ext,
                    content="",
                    char_count=0,
                    success=False,
                    error=f"Unsupported file type: .{ext}"
                )
        except Exception as e:
            return ProcessingResult(
                filename=filename,
                file_type=ext,
                content="",
                char_count=0,
                success=False,
                error=str(e)
            )

    def _process_pdf(
        self,
        file_path: str,
        filename: str
    ) -> ProcessingResult:
        """Extract text from PDF file with progress tracking."""
        if not self._pdf_available:
            return ProcessingResult(
                filename=filename,
                file_type="pdf",
                content="[PDF extraction unavailable - PyPDF2 not installed]",
                char_count=0,
                success=False,
                error="PyPDF2 not installed"
            )

        try:
            import PyPDF2

            text_parts = []
            total_pages = 0

            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)

                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            content = "\n\n".join(text_parts)

            return ProcessingResult(
                filename=filename,
                file_type="pdf",
                content=content,
                char_count=len(content),
                success=True
            )
        except Exception as e:
            return ProcessingResult(
                filename=filename,
                file_type="pdf",
                content="",
                char_count=0,
                success=False,
                error=f"Error extracting PDF: {str(e)}"
            )

    def _process_text(
        self,
        file_path: str,
        filename: str,
        file_type: str
    ) -> ProcessingResult:
        """Extract text from plain text or markdown file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            return ProcessingResult(
                filename=filename,
                file_type=file_type,
                content=content,
                char_count=len(content),
                success=True
            )
        except Exception as e:
            return ProcessingResult(
                filename=filename,
                file_type=file_type,
                content="",
                char_count=0,
                success=False,
                error=f"Error reading file: {str(e)}"
            )

    def _process_docx(
        self,
        file_path: str,
        filename: str
    ) -> ProcessingResult:
        """Extract text from DOCX file."""
        if not self._docx_available:
            return ProcessingResult(
                filename=filename,
                file_type="docx",
                content="[DOCX extraction unavailable - python-docx not installed]",
                char_count=0,
                success=False,
                error="python-docx not installed"
            )

        try:
            from docx import Document

            doc = Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            content = "\n\n".join(paragraphs)

            return ProcessingResult(
                filename=filename,
                file_type="docx",
                content=content,
                char_count=len(content),
                success=True
            )
        except Exception as e:
            return ProcessingResult(
                filename=filename,
                file_type="docx",
                content="",
                char_count=0,
                success=False,
                error=f"Error extracting DOCX: {str(e)}"
            )


_file_processor: Optional[FileProcessor] = None


def get_file_processor() -> FileProcessor:
    """Get the singleton file processor instance."""
    global _file_processor
    if _file_processor is None:
        _file_processor = FileProcessor()
    return _file_processor
