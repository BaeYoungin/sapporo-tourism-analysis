# ============================================================
# utils/file_utils.py — 파일 처리 유틸리티
#
# 역할:
#   - 업로드된 파일 객체(PDF / DOCX / TXT)에서 텍스트 추출
#   - 파일 형식 검증 및 크기 제한 확인
#   - 추출된 텍스트 전처리 (공백 정규화, 특수문자 처리 등)
#   - sample_data/ 폴더의 샘플 파일 로드 헬퍼
# ============================================================

from pathlib import Path


def parse_uploaded_file(file_obj) -> str:
    """
    Streamlit UploadedFile 객체를 받아 텍스트를 추출합니다.

    Args:
        file_obj: st.file_uploader 가 반환한 UploadedFile 객체

    Returns:
        추출된 텍스트 문자열
    """
    # TODO: 파일 확장자에 따라 PDF / DOCX / TXT 파서 분기 처리
    raise NotImplementedError


def extract_text_from_pdf(file_obj) -> str:
    """PDF 파일에서 텍스트를 추출합니다."""
    # TODO: PyPDF2 또는 pdfplumber 사용
    raise NotImplementedError


def extract_text_from_docx(file_obj) -> str:
    """DOCX 파일에서 텍스트를 추출합니다."""
    # TODO: python-docx 사용
    raise NotImplementedError


def extract_text_from_txt(file_obj) -> str:
    """TXT 파일에서 텍스트를 읽어옵니다."""
    # TODO: 인코딩(UTF-8 / EUC-KR) 자동 감지 처리
    raise NotImplementedError


def load_sample_file(filename: str) -> str:
    """
    sample_data/ 폴더에서 샘플 문서를 로드합니다.

    Args:
        filename: sample_data/ 내 파일명

    Returns:
        파일 텍스트 내용
    """
    # TODO: 구현
    sample_path = Path(__file__).parent.parent / "sample_data" / filename
    raise NotImplementedError
