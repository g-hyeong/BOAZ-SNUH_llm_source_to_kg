from typing import Dict, Any
from common.llm.gemini_llm import GeminiLLM

def get_llm(llm_type: str, llm_config: Dict[str, Any]):
    """
    LLM 타입에 따라 적절한 LLM 인스턴스를 반환합니다.
    
    Args:
        llm_type: LLM 타입 ("gemini", "openai" 등)
        llm_config: LLM 설정 정보
        
    Returns:
        LLM 인스턴스
        
    Raises:
        ValueError: 지원하지 않는 LLM 타입이 입력된 경우
    """
    if llm_type == "gemini":
        return GeminiLLM(**llm_config)
    else:
        raise ValueError(f"지원하지 않는 LLM 타입입니다: {llm_type}")
