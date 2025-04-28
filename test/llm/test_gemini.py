import os
import sys
import pytest
import logging
import time
from datetime import datetime
from typing import Dict, List, Any

# 프로젝트 경로를 시스템 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.common.llm.gemini_llm import GeminiLLM
from src.config import settings

# 테스트 로깅 설정
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "logs")
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"gemini_test_{timestamp}.log")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# 실제 API 호출이 필요한 테스트이므로 mark 사용
@pytest.mark.api
class TestGeminiLLM:
    """
    GeminiLLM 클래스의 기능 테스트
    """
    
    @pytest.fixture
    def gemini_llm(self) -> GeminiLLM:
        """
        테스트용 GeminiLLM 인스턴스를 생성하는 fixture
        """
        # 테스트용 모델 설정
        llm = GeminiLLM(
            model="gemini-1.5-flash",  # 모델명 지정
            temperature=0.5,     # 낮은 온도로 일관된 출력
            max_tokens=1024      # 출력 길이 제한
        )
        return llm
    
    def test_call_llm(self, gemini_llm: GeminiLLM) -> None:
        """
        call_llm 메서드 테스트 - 단일 질문/응답
        """
        # 시스템 프롬프트와 사용자 질문 설정
        system_prompt = "당신은 도움이 되는 AI 비서입니다. 간결하고 정확하게 대답해주세요."
        user_prompt = "파이썬에서 리스트와 튜플의 차이점은 무엇인가요?"
        
        logging.info(f"테스트 시작: call_llm - {user_prompt}")
        
        # LLM 호출
        response = gemini_llm.call_llm(system_prompt, user_prompt)
        
        # 응답 검증
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        
        logging.info(f"LLM 응답: {response}")
        logging.info("테스트 완료: call_llm")
    
    def test_chat_llm_without_history(self, gemini_llm: GeminiLLM) -> None:
        """
        chat_llm 메서드 테스트 - 대화 기록 없이 시작
        """
        # 시스템 프롬프트와 사용자 질문 설정
        system_prompt = "당신은 한국인 사용자를 돕는 AI 비서입니다. 한국어로 대답해주세요."
        user_prompt = "오늘 날씨가 어때요?"
        
        logging.info(f"테스트 시작: chat_llm_without_history - {user_prompt}")
        
        # 대화 기록 없이 LLM 호출
        result = gemini_llm.chat_llm(system_prompt, user_prompt)
        
        # 결과 검증
        assert result is not None
        assert isinstance(result, dict)
        assert "response" in result
        assert "updated_history" in result
        assert len(result["updated_history"]) >= 2  # 최소 시스템, 사용자, 어시스턴트 메시지
        
        logging.info(f"첫 번째 응답: {result['response']}")
        
        # 대화 기록의 올바른 형식 검증
        history = result["updated_history"]
        for msg in history:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ["system", "user", "assistant"]
            
        logging.info("테스트 완료: chat_llm_without_history")
    
    def test_chat_llm_with_history(self, gemini_llm: GeminiLLM) -> None:
        """
        chat_llm 메서드 테스트 - 대화 기록 이어가기
        """
        # 시스템 프롬프트와 초기 대화 기록 설정
        system_prompt = "당신은 대화형 AI 비서입니다. 이전 대화를 기억하고 맥락에 맞게 응답해주세요."
        
        logging.info("테스트 시작: chat_llm_with_history")
        
        # 초기 대화 기록
        chat_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "내 이름은 김철수야."},
            {"role": "assistant", "content": "안녕하세요, 김철수님! 어떻게 도와드릴까요?"}
        ]
        
        # 새 사용자 메시지
        user_prompt = "내 이름이 뭐지?"
        
        logging.info(f"대화 기록: {chat_history}")
        logging.info(f"사용자 질문: {user_prompt}")
        
        # 대화 기록과 함께 LLM 호출
        result = gemini_llm.chat_llm(system_prompt, user_prompt, chat_history)
        
        # 결과 검증
        assert result is not None
        assert "response" in result
        assert "updated_history" in result
        assert len(result["updated_history"]) > len(chat_history)
        
        logging.info(f"두 번째 응답: {result['response']}")
        
        # LLM이 이름을 기억하는지 확인 (컨텍스트 유지 확인)
        assert "철수" in result["response"].lower() or "김철수" in result["response"].lower()
        
        logging.info("테스트 완료: chat_llm_with_history")
        logging.info(f"모든 테스트 로그 저장 위치: {log_file}")

if __name__ == "__main__":
    # 직접 실행 시 테스트 수행
    logging.info("직접 실행 모드 시작")
    
    llm = GeminiLLM(model="gemini-1.5-flash", temperature=0.7)
    
    logging.info("\n===== call_llm 테스트 =====")
    response = llm.call_llm(
        "당신은 도움이 되는 비서입니다.",
        "인공지능의 발전 역사를 간략히 설명해주세요."
    )
    logging.info(f"응답: {response}")
    
    logging.info("\n===== chat_llm 테스트 =====")
    result = llm.chat_llm(
        "당신은 도움이 되는 비서입니다.",
        "한국의 대표적인 음식 3가지를 알려주세요."
    )
    logging.info(f"응답: {result['response']}")
    
    # 대화 이어가기
    follow_up = llm.chat_llm(
        "당신은 도움이 되는 비서입니다.",
        "그 중에서 가장 유명한 것은 무엇인가요?",
        result["updated_history"]
    )
    logging.info(f"응답: {follow_up['response']}")
    
    logging.info(f"모든 테스트 로그 저장 위치: {log_file}")
