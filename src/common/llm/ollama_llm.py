import requests
import asyncio
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

from src.common.llm.common_llm import CommonLLM, LLMResult
from src.common.logging import log_llm_prompt, log_llm_response
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.messages import AIMessage, BaseMessage

class OllamaLLM(CommonLLM):
    """
    Ollama API를 통해 LLM에 접근하는 클래스
    LangChain 및 LangGraph와 통합을 위한 구현
    """
    client_initialized: bool = False
    
    def __init__(self, **kwargs: Any) -> None:
        """
        Ollama LLM 클래스 생성자

        Args:
            **kwargs: Ollama LLM 설정 파라미터
                - base_url: Ollama API 서버 URL (기본값: http://localhost:11434)
                - model: 사용 모델명 (기본값: llama2)
                - temperature: 생성 다양성 조절 매개변수 (기본값: 0.7)
                - max_tokens: 최대 출력 토큰 수 (기본값: 4096)
                - top_p: 상위 확률 샘플링 파라미터 (기본값: 0.9)
        """
        # Ollama 특화 매개변수 추출
        model = kwargs.get("model", "llama2")
        model_name = f"ollama/{model}"
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 4096)
        
        # 상위 클래스 초기화 - 명시적으로 매개변수 전달
        super().__init__(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # 클래스 속성 설정
        self.base_url = kwargs.get("base_url", "http://localhost:11434").rstrip('/')
        self.model = model
        
        # Ollama API 초기화
        self._initialize_ollama()
        
    def _initialize_ollama(self) -> None:
        """
        Ollama API 초기화 및 연결 테스트
        
        Raises:
            ValueError: API 연결 실패 시
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                self.client_initialized = True
                available_models = response.json()
                print(f"Ollama 서버 연결 성공. 사용 가능 모델: {available_models}")
            else:
                print(f"Ollama 서버 연결 테스트 실패: {response.status_code}")
                raise ValueError(f"Ollama 서버 연결 실패: {response.status_code}")
        except Exception as e:
            print(f"Ollama 서버 연결 오류: {str(e)}")
            raise ValueError(f"Ollama 서버 연결 오류: {str(e)}")
            
    def _validate_client(self) -> None:
        """
        클라이언트가 초기화되었는지 확인
        
        Raises:
            ValueError: 클라이언트가 초기화되지 않은 경우
        """
        if not self.client_initialized:
            raise ValueError("Ollama API가 초기화되지 않았습니다.")

    def _call_request_by_llm(self, system_prompt: str, human_prompt: str) -> str:
        """
        Ollama API를 통해 LLM 질의 메서드

        Args:
            system_prompt: LLM 역할/맥락 설정 시스템 프롬프트
            human_prompt: 사용자 요청 프롬프트

        Returns:
            LLM 응답 문자열
        """
        self._validate_client()
        
        prompt = f"{system_prompt}\n\n{human_prompt}" if system_prompt else human_prompt
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                },
                timeout=60  # 타임아웃 설정
            )
            
            if response.status_code == 200:
                response_text = response.json().get("response", "")
                return response_text
            else:
                return f"오류 발생: {response.status_code} - {response.text}"
        except Exception as e:
            return f"API 호출 오류: {str(e)}"

    def _chat_request_by_llm(
        self,
        system_prompt: str,
        human_prompt: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> LLMResult:
        """
        Ollama API 채팅 모드로 대화 진행 메서드

        Args:
            system_prompt: LLM 역할/맥락 설정 시스템 프롬프트
            human_prompt: 사용자 요청 프롬프트
            chat_history: 이전 대화 기록 리스트
                각 딕셔너리는 {"role": "user" or "assistant", "content": "message"} 형태

        Returns:
            응답 결과 딕셔너리 (LLMResult)
            - 'response': LLM 응답 문자열
            - 'updated_history': 업데이트된 대화 기록
            - 'metadata': 추가 메타데이터
        """
        self._validate_client()
        
        # 채팅 기록 초기화
        if chat_history is None:
            chat_history = []
            
        # 복사본 생성하여 원본을 변경하지 않도록 함
        updated_history = chat_history.copy()
        
        # 시스템 프롬프트 추가
        if system_prompt and not any(msg.get("role") == "system" for msg in updated_history):
            updated_history.insert(0, {"role": "system", "content": system_prompt})
        
        # 사용자 메시지 추가
        updated_history.append({"role": "user", "content": human_prompt})
        
        # Ollama API 형식으로 메시지 변환
        messages = []
        system_content = None
        
        for msg in updated_history:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_content = content
            elif role == "user":
                messages.append({"role": "user", "content": content})
            elif role == "assistant":
                messages.append({"role": "assistant", "content": content})
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                        "system": system_content
                    }
                },
                timeout=60  # 타임아웃 설정
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("message", {}).get("content", "")
                
                # 응답을 채팅 기록에 추가
                updated_history.append({"role": "assistant", "content": ai_response})
                
                return {
                    "response": ai_response,
                    "updated_history": updated_history,
                    "metadata": {"model": self.model}
                }
            else:
                error_msg = f"오류 발생: {response.status_code} - {response.text}"
                return {
                    "response": error_msg,
                    "updated_history": updated_history,
                    "metadata": {"error": error_msg}
                }
        except Exception as e:
            error_msg = f"API 호출 오류: {str(e)}"
            return {
                "response": error_msg,
                "updated_history": updated_history,
                "metadata": {"error": str(e)}
            }
            
    # LangChain 비동기 인터페이스 구현
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        LangChain 비동기 인터페이스 구현
        
        Args:
            messages: 메시지 리스트
            stop: 생성 중단 토큰 리스트
            run_manager: 콜백 관리자
            **kwargs: 추가 키워드 인자
            
        Returns:
            ChatResult: 채팅 생성 결과
        """
        # 동기 메서드를 비동기로 실행
        return await asyncio.to_thread(self._generate, messages, stop, run_manager, **kwargs)

    def get_embedding(self, text: str) -> List[float]:
        """
        Ollama API로 텍스트 임베딩 생성 메서드

        Args:
            text: 임베딩 생성할 텍스트

        Returns:
            텍스트 임베딩 벡터
        """
        self._validate_client()
        
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("embedding", [])
            else:
                print(f"임베딩 생성 오류: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"임베딩 API 호출 오류: {str(e)}")
            return []
            
    def list_models(self) -> List[str]:
        """
        사용 가능한 Ollama 모델 목록 반환 유틸리티 메서드
        
        Returns:
            사용 가능 모델명 목록
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models_data = response.json()
                return [model["name"] for model in models_data.get("models", [])]
            else:
                return []
        except Exception as e:
            print(f"모델 목록 조회 오류: {str(e)}")
            return []
