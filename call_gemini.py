"""
Gemini API 호출 모듈 - Google Gemini 모델 호출을 위한 인터페이스

이 모듈은 Google Gemini API를 통해 Gemini 2.5 Pro 및 Gemini 2.0 모델과 
통신할 수 있는 함수를 제공합니다.
"""

import os
import google.generativeai as genai
from typing import Dict, Any, Optional, List, Union, Tuple

# 로깅 설정
import logging
logger = logging.getLogger(__name__)

# Gemini API 모델 상수
GEMINI_2_5_PRO = 'gemini-2.5-pro-exp-03-25'
GEMINI_2_0_FLASH = 'gemini-2.0-flash'

# 환경 변수에서 API 키 가져오기
def get_api_key() -> str:
    """환경 변수에서 Gemini API 키를 가져옵니다."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
    return api_key

def initialize_gemini(model_key: str = GEMINI_2_5_PRO) -> Dict[str, Any]:
    """
    Gemini API를 초기화하고 지정된 모델 정보를 반환합니다.
    
    Args:
        model_key: 사용할 Gemini 모델 키
        
    Returns:
        Dict[str, Any]: 모델 정보를 포함하는 딕셔너리
    """
    try:
        # API 키 설정
        api_key = get_api_key()
        genai.configure(api_key=api_key)
        
        # 유효한 모델 키인지 확인
        if model_key not in [GEMINI_2_5_PRO, GEMINI_2_0_FLASH]:
            logger.warning(f"지원되지 않는 Gemini 모델 키: {model_key}. 기본값 {GEMINI_2_5_PRO}로 설정합니다.")
            model_key = GEMINI_2_5_PRO
        
        # 모델 초기화
        model = genai.GenerativeModel(model_key)
        
        logger.info(f"Gemini 모델 초기화 완료: {model_key}")
        return {
            "model_key": model_key,
            "model": model
        }
    
    except Exception as e:
        logger.error(f"Gemini API 초기화 중 오류 발생: {e}")
        raise

def get_gemini_response(
    prompt: str, 
    model_key: str = GEMINI_2_5_PRO, 
    temperature: float = 0.1,
    max_tokens: int = 8192,
    stop: Optional[List[str]] = None
) -> Tuple[str, bool]:
    """
    Gemini API를 사용하여 프롬프트에 대한 응답을 생성합니다.
    
    Args:
        prompt: 모델에 전송할 프롬프트
        model_key: 사용할 Gemini 모델 키
        temperature: 생성 온도 (0.0 ~ 1.0)
        max_tokens: 생성할 최대 토큰 수
        stop: 생성을 중단할 시퀀스 목록 (Gemini API가 지원하는 경우)
        
    Returns:
        Tuple[str, bool]: (응답 텍스트, 성공 여부)
    """
    try:
        # API 키 설정
        api_key = get_api_key()
        genai.configure(api_key=api_key)
        
        # 모델 초기화
        model = genai.GenerativeModel(model_key)
        
        # 생성 설정
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        # stop 시퀀스가 있는 경우 (참고: Gemini API의 특정 버전에 따라 지원 여부 확인 필요)
        if stop:
            logger.info(f"Stop 시퀀스가 제공되었으나 Gemini API에서 직접 지원하지 않을 수 있습니다: {stop}")
        
        # 응답 생성
        response = model.generate_content(
            prompt, 
            generation_config=generation_config
        )
        
        # 응답 텍스트 추출
        if hasattr(response, 'text'):
            return response.text.strip(), True
        else:
            text = ""
            for part in response.parts:
                if hasattr(part, 'text'):
                    text += part.text
            return text.strip(), True
    
    except Exception as e:
        logger.error(f"Gemini API 호출 중 오류 발생: {e}")
        return f"[Gemini API 호출 오류: {e}]", False 