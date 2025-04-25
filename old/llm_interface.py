"""
LLM 인터페이스 - 다양한 LLM 백엔드를 통합적으로 관리하는 모듈

이 모듈은 다양한 LLM 백엔드(Ollama, Bedrock, Gemini 등)를 추상화하여 
통일된 인터페이스를 제공합니다. 이를 통해 애플리케이션은 
백엔드 구현에 관계없이 동일한 방식으로 LLM을 호출할 수 있습니다.
"""

import os
import json
import logging
import importlib.util
from typing import Dict, Any, Optional, Tuple, List, Union, Callable

# 로깅 설정
logger = logging.getLogger(__name__)

# LLM 백엔드 타입 상수
LLM_TYPE_OLLAMA = "ollama"
LLM_TYPE_BEDROCK = "bedrock"
LLM_TYPE_GEMINI = "gemini"

# 모델 ID 매핑: 커맨드라인 인자 -> 백엔드 및 모델 정보
MODEL_MAPPING = {
    # Ollama 모델
    "deepseek": {"backend": LLM_TYPE_OLLAMA, "model_id": "deepseek-r1:14b"},
    "deepseek-coder": {"backend": LLM_TYPE_OLLAMA, "model_id": "deepseek-coder:16b"}, 
    "dolphin": {"backend": LLM_TYPE_OLLAMA, "model_id": "dolphin-mistral"}, 
    "mixtral": {"backend": LLM_TYPE_OLLAMA, "model_id": "mixtral"}, 
    "vicuna": {"backend": LLM_TYPE_OLLAMA, "model_id": "vicuna"}, 
    "llama2": {"backend": LLM_TYPE_OLLAMA, "model_id": "llama2"}, 
    
    # AWS Bedrock 모델
    "claude": {"backend": LLM_TYPE_BEDROCK, "model_key": "claude_3_7_sonnet"},
    "llama": {"backend": LLM_TYPE_BEDROCK, "model_key": "llama_3_3_70b"},
    
    # Google Gemini 모델
    "gemini-2.5": {"backend": LLM_TYPE_GEMINI, "model_key": "gemini-2.5-pro-exp-03-25"},
    "gemini-2.0": {"backend": LLM_TYPE_GEMINI, "model_key": "gemini-2.0-flash"}
}

# 현재 사용중인 LLM 정보
_current_llm_info = None

def get_available_models() -> List[str]:
    """사용 가능한 모든 모델 ID 목록 반환"""
    return list(MODEL_MAPPING.keys())

def setup_llm(model_id: str) -> Dict[str, Any]:
    """
    지정된 모델 ID에 해당하는 LLM 백엔드를 설정하고 관련 정보를 반환합니다.
    
    Args:
        model_id: 설정할 모델의 ID (예: "claude", "deepseek", "gemini-2.5")
        
    Returns:
        Dict[str, Any]: LLM 유형 및 모델 정보를 포함하는 딕셔너리
        
    Raises:
        ValueError: 지원되지 않는 모델 ID가 제공된 경우
    """
    global _current_llm_info
    
    # 주어진 모델 ID가 유효한지 확인
    if model_id not in MODEL_MAPPING:
        valid_models = ", ".join(get_available_models())
        raise ValueError(f"지원되지 않는 모델 ID: '{model_id}'. 유효한 모델: {valid_models}")
    
    # 모델 매핑 정보 가져오기
    model_info = MODEL_MAPPING[model_id]
    llm_type = model_info["backend"]
    
    # 백엔드별 설정
    if llm_type == LLM_TYPE_OLLAMA:
        # Ollama 백엔드 필요한 모듈이 있는지 확인
        try:
            import requests
            # Ollama 상태 확인 (선택 사항)
            # response = requests.get("http://localhost:11434/api/tags")
            # if response.status_code != 200:
            #     logger.warning(f"Ollama 서버 응답 상태 코드: {response.status_code}")
        except ImportError:
            logger.error("Ollama 백엔드 사용을 위해 'requests' 패키지가 필요합니다.")
            raise
        except Exception as e:
            logger.warning(f"Ollama 서버 상태 확인 실패: {e}")
    
    elif llm_type == LLM_TYPE_BEDROCK:
        # Bedrock 백엔드 필요 모듈 확인
        try:
            import boto3
            # Bedrock 모듈 로드
            if importlib.util.find_spec("call_bedrock") is None:
                logger.error("Bedrock 백엔드 사용을 위해 'call_bedrock.py' 모듈이 필요합니다.")
                raise ImportError("call_bedrock 모듈을 찾을 수 없습니다.")
            
            # AWS 환경 변수 확인 (선택 사항)
            aws_profile = os.environ.get("AWS_PROFILE", "boaz-snuh")
            logger.info(f"AWS 프로필: {aws_profile}")
        except ImportError:
            logger.error("Bedrock 백엔드 사용을 위해 'boto3' 패키지가 필요합니다.")
            raise
    
    elif llm_type == LLM_TYPE_GEMINI:
        # Gemini 백엔드 필요 모듈 확인
        try:
            import google.generativeai
            # Gemini 모듈 로드
            if importlib.util.find_spec("call_gemini") is None:
                logger.error("Gemini 백엔드 사용을 위해 'call_gemini.py' 모듈이 필요합니다.")
                raise ImportError("call_gemini 모듈을 찾을 수 없습니다.")
            
            # 환경 변수 확인
            if not os.environ.get("GEMINI_API_KEY"):
                logger.warning("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
                
            # Gemini 모듈 가져오기
            import call_gemini
            
            # 모델 초기화
            model_key = model_info.get("model_key")
            gemini_info = call_gemini.initialize_gemini(model_key)
            # 추가 모델 정보 병합
            model_info.update(gemini_info)
            
        except ImportError:
            logger.error("Gemini 백엔드 사용을 위해 'google-generativeai' 패키지가 필요합니다.")
            raise
    
    # 현재 LLM 정보 업데이트
    _current_llm_info = {
        "type": llm_type,
        "model_id": model_id,
        **model_info  # 나머지 모델 정보 포함
    }
    
    logger.info(f"LLM 백엔드 설정 완료: {llm_type}, 모델: {model_id}")
    return _current_llm_info

def call_llm(prompt: str, temperature: float = 0.1, max_tokens: int = 128000, stop: Optional[List[str]] = None) -> Tuple[str, bool]:
    """
    설정된 LLM 백엔드를 사용하여 프롬프트를 처리하고 응답을 반환합니다.
    
    Args:
        prompt: LLM에 전달할 프롬프트
        temperature: 생성 온도 (0.0 ~ 1.0)
        max_tokens: 생성할 최대 토큰 수
        stop: 생성을 중단할 시퀀스 목록
        
    Returns:
        Tuple[str, bool]: (응답 텍스트, 성공 여부)
        
    Raises:
        RuntimeError: LLM이 설정되지 않았거나 호출 중 오류가 발생한 경우
    """
    global _current_llm_info
    
    # LLM이 설정되어 있는지 확인
    if _current_llm_info is None:
        raise RuntimeError("LLM을 호출하기 전에 setup_llm()을 사용하여 LLM을 설정해야 합니다.")
    
    llm_type = _current_llm_info["type"]
    try:
        # Ollama 백엔드 호출
        if llm_type == LLM_TYPE_OLLAMA:
            return _call_ollama(prompt, temperature, max_tokens, stop)
        
        # Bedrock 백엔드 호출
        elif llm_type == LLM_TYPE_BEDROCK:
            return _call_bedrock(prompt, temperature, max_tokens, stop)
        
        # Gemini 백엔드 호출
        elif llm_type == LLM_TYPE_GEMINI:
            return _call_gemini(prompt, temperature, max_tokens, stop)
        
        # 지원되지 않는 백엔드 유형
        else:
            raise ValueError(f"지원되지 않는 LLM 백엔드 유형: {llm_type}")
    
    except Exception as e:
        logger.error(f"LLM 호출 중 오류 발생: {e}", exc_info=True)
        return f"[LLM 호출 오류: {e}]", False

def _call_ollama(prompt: str, temperature: float = 0.1, max_tokens: int = 4000, stop: Optional[List[str]] = None) -> Tuple[str, bool]:
    """Ollama 백엔드를 통해 LLM 호출"""
    import requests
    
    model_id = _current_llm_info.get("model_id", "deepseek-r1:14b")  # 기본값 설정
    
    # Ollama API 요청 본문 생성
    data = {
        "model": model_id,
        "prompt": prompt,
        "temperature": temperature,
        "num_predict": max_tokens,
    }
    
    # 정지 시퀀스가 제공된 경우 추가
    if stop:
        data["stop"] = stop
    
    logger.debug(f"Ollama 요청: 모델={model_id}, 온도={temperature}")
    
    try:
        # Ollama API 호출
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=data,
            stream=False
        )
        
        # 응답 확인
        if response.status_code != 200:
            logger.error(f"Ollama API 오류: 상태 코드 {response.status_code}")
            return f"[Ollama API 오류: 상태 코드 {response.status_code}]", False
        
        # 응답 파싱
        result = response.json()
        response_text = result.get("response", "")
        
        return response_text.strip(), True
    
    except requests.RequestException as e:
        logger.error(f"Ollama API 요청 오류: {e}")
        return f"[Ollama API 요청 오류: {e}]", False
    
    except Exception as e:
        logger.error(f"Ollama 호출 중 예상치 못한 오류: {e}")
        return f"[Ollama 호출 오류: {e}]", False

def _call_bedrock(prompt: str, temperature: float = 0.1, max_tokens: int = 4000, stop: Optional[List[str]] = None) -> Tuple[str, bool]:
    """AWS Bedrock 백엔드를 통해 LLM 호출"""
    try:
        # call_bedrock 모듈 동적 임포트
        import call_bedrock
        
        # 모델 키 가져오기
        model_key = _current_llm_info.get("model_key", "claude_3_7_sonnet")  # 기본값 설정
        
        # 사용자가 지정한 경우 stop 시퀀스 적용
        kwargs = {}
        if stop:
            # 백틱이 포함된 경우 제거 (백틱은 JSON 코드 블록 반환을 방해함)
            filtered_stop = [s for s in stop if s != "```"]
            # 클로드 모델에만 적용
            if "claude" in model_key and filtered_stop:
                kwargs["stop_sequences"] = filtered_stop
        
        # Bedrock API 호출
        logger.debug(f"Bedrock 요청: 모델={model_key}, 온도={temperature}")
        response_text = call_bedrock.get_text_response(
            prompt=prompt,
            model_key=model_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response_text.strip(), True
    
    except ModuleNotFoundError:
        logger.error("call_bedrock 모듈을 찾을 수 없습니다.")
        return "[call_bedrock 모듈 로드 실패]", False
    
    except Exception as e:
        logger.error(f"Bedrock 호출 중 오류: {e}")
        return f"[Bedrock 호출 오류: {e}]", False

def _call_gemini(prompt: str, temperature: float = 0.1, max_tokens: int = 8192, stop: Optional[List[str]] = None) -> Tuple[str, bool]:
    """Google Gemini 백엔드를 통해 LLM 호출"""
    try:
        # call_gemini 모듈 동적 임포트
        import call_gemini
        
        # 모델 키 가져오기
        model_key = _current_llm_info.get("model_key", call_gemini.GEMINI_2_5_PRO)  # 기본값 설정
        
        # Gemini API 호출
        logger.debug(f"Gemini 요청: 모델={model_key}, 온도={temperature}")
        response_text, success = call_gemini.get_gemini_response(
            prompt=prompt,
            model_key=model_key,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop
        )
        
        return response_text.strip(), success
    
    except ModuleNotFoundError:
        logger.error("call_gemini 모듈을 찾을 수 없습니다.")
        return "[call_gemini 모듈 로드 실패]", False
    
    except Exception as e:
        logger.error(f"Gemini 호출 중 오류: {e}")
        return f"[Gemini 호출 오류: {e}]", False 