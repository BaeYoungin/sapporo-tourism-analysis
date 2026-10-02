# ============================================================
# utils/ai_utils.py — OpenAI API 호출 유틸리티
#
# 역할:
#   - OpenAI 클라이언트 초기화 (환경 변수에서 API 키 로드)
#   - 문서 텍스트를 받아 GPT-5-mini 로 분석 요청
#   - 요약 / 핵심 키워드 추출 / Q&A 등 분석 기능 제공
#   - API 오류 처리 및 재시도 로직
# ============================================================

import os
from openai import OpenAI


def get_client() -> OpenAI:
    """환경 변수 OPENAI_API_KEY 를 읽어 OpenAI 클라이언트를 반환합니다."""
    # TODO: API 키 유효성 검증 추가
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_document(text: str, instruction: str) -> str:
    """
    문서 텍스트를 GPT-5-mini 로 분석합니다.

    Args:
        text:        분석할 문서의 전체 텍스트
        instruction: 분석 방식을 지정하는 시스템 프롬프트

    Returns:
        모델의 응답 문자열
    """
    # TODO: 구현
    raise NotImplementedError


def summarize(text: str) -> str:
    """문서를 요약합니다."""
    # TODO: 구현
    raise NotImplementedError


def extract_keywords(text: str) -> list[str]:
    """문서에서 핵심 키워드를 추출합니다."""
    # TODO: 구현
    raise NotImplementedError
