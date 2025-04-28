import asyncio
from typing import Any, Dict, List, Optional, Union
from config import settings
from common.llm.common_llm import CommonLLM, LLMResult
from common.logging import log_llm_prompt, log_llm_response
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, ContentDict, PartDict
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.messages import AIMessage, BaseMessage
import logging
import time
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

class GeminiLLM(CommonLLM):
    """
    Google Gemini API를 통해 LLM에 접근하는 클래스
    LangChain 및 LangGraph와 통합을 위한 구현
    """
    client: Any = None
    model: str
    temperature: float = 0.9
    max_output_tokens: int = 8192
    top_p: float = 0.95
    top_k: int = 0
    safety_settings: Optional[Dict[str, str]] = None
    generation_config: Dict[str, Any] = {}
    
    class Config:
        """Pydantic 설정"""
        arbitrary_types_allowed = True
        extra = "allow"
    
    def __init__(self, **kwargs: Any) -> None:
        """
        Google Gemini LLM 클래스 생성자

        Args:
            **kwargs: Gemini LLM 설정 파라미터
                - api_key: Gemini API 키 (기본값: 환경 변수에서 로드)
                - model: 사용 모델명 (기본값: gemini-pro)
                - temperature: 생성 다양성 조절 매개변수 (기본값: 0.7)
                - max_output_tokens: 최대 출력 토큰 수 (기본값: 4096)
                - top_p: 상위 확률 샘플링 파라미터 (기본값: 0.9)
                - top_k: 상위 k개 토큰 샘플링 파라미터 (기본값: 40)
        """
        # 필수 매개변수 확인
        model = kwargs.get("model")
        if not model:
            raise ValueError("모델명이 지정되지 않았습니다.")
            
        # Gemini 특화 매개변수 추출
        model_name = f"gemini_{model}"
        temperature = kwargs.pop("temperature", 0.7)
        max_tokens = kwargs.pop("max_tokens", kwargs.pop("max_output_tokens", 4096))
        
        # 상위 클래스 초기화 - 명시적으로 매개변수 전달
        super().__init__(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # 클래스 속성 설정
        self._raw_model_name = model
        
        # Gemini API 초기화
        self._initialize_gemini(**kwargs)
        
    def _initialize_gemini(self, **kwargs: Any) -> None:
        """
        Gemini API 초기화 및 모델 설정
        
        Args:
            **kwargs: 초기화 파라미터
        """
        # API 키 설정 - 환경 변수 또는 직접 전달값 사용
        api_key = kwargs.get("api_key", settings.gemini_api_key)
        if not api_key:
            raise ValueError("Gemini API 키가 설정되지 않았습니다.")

        # API 초기화
        try:
            genai.configure(api_key=api_key)

            # 모델명 매핑 - 접두사가 제거된 이름을 기반으로 설정된 매핑 사용
            # settings.gemini_models에 해당 모델명이 있는 경우에만 매핑 적용
            if self._raw_model_name in settings.gemini_models:
                self._raw_model_name = settings.gemini_models[self._raw_model_name]
            
            # 생성 매개변수 설정
            self.generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
                "top_p": kwargs.get("top_p", 0.9),
                "top_k": kwargs.get("top_k", 40)
            }
            
            # 안전 설정 - 최소 차단 수준
            self.safety_settings = [
                {
                    "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": HarmBlockThreshold.BLOCK_NONE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE
                }
            ]
            
            # 모델 객체 생성
            self.client = genai.GenerativeModel(
                model_name=self._raw_model_name,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            print(f"Google Gemini API 클라이언트 초기화 성공. 모델: {self._raw_model_name}")
            
        except Exception as e:
            print(f"Gemini API 초기화 오류: {str(e)}")
            self.client = None
            raise
            
    def _validate_client(self) -> None:
        """
        클라이언트가 초기화되었는지 확인
        
        Raises:
            ValueError: 클라이언트가 초기화되지 않은 경우
        """
        if not self.client:
            raise ValueError("Gemini 모델이 초기화되지 않았습니다. API 키를 확인하세요.")

    def _call_request_by_llm(self, system_prompt: str, human_prompt: str) -> str:
        """
        Google Gemini API로 LLM 질의 메서드

        Args:
            system_prompt: LLM 역할/맥락 설정 시스템 프롬프트
            human_prompt: 사용자 요청 프롬프트

        Returns:
            LLM 응답 문자열
        """
        self._validate_client()
        
        try:
            # 시스템 프롬프트와 사용자 프롬프트 결합
            prompt = f"{system_prompt}\n\n{human_prompt}" if system_prompt else human_prompt
            
            # 모델에 요청
            response = self.client.generate_content(prompt)
            
            # 응답 확인 및 반환
            if response.candidates and len(response.candidates) > 0:
                if response.candidates[0].finish_reason == 'BLOCKED':
                    return "안전 필터에 의해 응답이 차단되었습니다."
                else:
                    return response.text
            else:
                return "응답 생성에 실패했습니다."
                
        except Exception as e:
            return f"API 호출 오류: {str(e)}"

    def _chat_request_by_llm(
        self,
        system_prompt: str,
        human_prompt: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> LLMResult:
        """
        Google Gemini API로 대화 진행 메서드

        Args:
            system_prompt: LLM 역할/맥락 설정 시스템 프롬프트
            human_prompt: 사용자 요청 프롬프트
            chat_history: 이전 대화 기록 리스트
                각 딕셔너리는 {"role": "user" or "assistant", "content": "message"} 형태

        Returns:
            응답 결과 딕셔너리
            - 'response': LLM 응답 문자열
            - 'updated_history': 업데이트된 대화 기록
            - 'metadata': 추가 메타데이터
        """
        self._validate_client()
        
        # 채팅 기록 초기화
        if chat_history is None:
            chat_history = []
        
        try:
            # 채팅 세션 생성
            chat = self.client.start_chat(history=[])
            
            # 시스템 프롬프트 설정
            if system_prompt:
                # Gemini는 직접 시스템 프롬프트 개념 없음
                if not any(msg.get("role") == "system" for msg in chat_history):
                    system_message = {"role": "system", "content": system_prompt}
                    chat_history.insert(0, system_message)
                    initial_msg = f"시스템 메시지: {system_prompt}"
                    chat.send_message(initial_msg)
            
            # 채팅 기록 적용
            for msg in chat_history:
                if msg["role"] == "system":
                    continue  # 시스템 메시지는 이미 처리됨
                
                # Gemini 채팅 세션에 메시지 전송
                if msg["role"] == "user":
                    chat.send_message(msg["content"])
                elif msg["role"] == "assistant" and hasattr(chat.history, 'append'):
                    # 응답 메시지는 채팅 역사에 직접 추가
                    chat.history.append({
                        "role": "model",
                        "parts": [{"text": msg["content"]}]
                    })
            
            # 새 사용자 메시지 추가
            response = chat.send_message(human_prompt)
            ai_response = response.text
            
            # 대화 기록 업데이트
            updated_history = chat_history.copy()
            updated_history.append({"role": "user", "content": human_prompt})
            updated_history.append({"role": "assistant", "content": ai_response})
            
            return {
                "response": ai_response,
                "updated_history": updated_history,
                "metadata": {"model": self._raw_model_name}
            }
            
        except Exception as e:
            error_msg = f"API 호출 오류: {str(e)}"
            
            # 에러 발생해도 대화 기록 업데이트
            updated_history = chat_history.copy()
            updated_history.append({"role": "user", "content": human_prompt})
            
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
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        채팅 메시지 리스트로부터 응답을 생성
        
        Args:
            messages: 메시지 리스트
            stop: 생성 중단 토큰 리스트 (Gemini API에서는 지원되지 않음)
            run_manager: 콜백 관리자
            **kwargs: 추가 키워드 인자
            
        Returns:
            ChatResult: 채팅 생성 결과
        """
        self._validate_client()
        
        if stop:
            logging.warning("Gemini API는 중지 토큰을 지원하지 않습니다.")
        
        # 콜백 처리 (시작)
        if run_manager:
            run_manager.on_llm_start({"name": self._llm_type}, messages, **kwargs)
        
        try:
            # 메시지 형식 변환 - LangChain 메시지를 Gemini API 요구 형식으로 변환
            formatted_messages = []
            for message in messages:
                if message.type == "human":
                    formatted_messages.append({"role": "user", "content": message.content})
                elif message.type == "ai":
                    formatted_messages.append({"role": "assistant", "content": message.content})
                elif message.type == "system":
                    formatted_messages.append({"role": "system", "content": message.content})
            
            # 채팅 세션 생성
            chat = self.client.start_chat(history=[])
            
            # 메시지 처리 및 시스템 메시지 설정
            system_message = None
            for msg in formatted_messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                    continue  # 시스템 메시지는 별도 처리
                
                # 일반 메시지는 순차적으로 전송
                if msg["role"] == "user":
                    if system_message and formatted_messages.index(msg) == 1:
                        # 첫 번째 유저 메시지에 시스템 메시지 추가
                        content = f"시스템 메시지: {system_message}\n\n{msg['content']}"
                        chat.send_message(content)
                        system_message = None  # 시스템 메시지 처리 완료
                    else:
                        chat.send_message(msg["content"])
                        
                elif msg["role"] == "assistant" and hasattr(chat.history, 'append'):
                    # 어시스턴트 메시지는 히스토리에 직접 추가
                    chat.history.append({
                        "role": "model",
                        "parts": [{"text": msg["content"]}]
                    })
            
            # 마지막 메시지가 사용자 메시지가 아닌 경우 처리
            if formatted_messages and formatted_messages[-1]["role"] != "user":
                logging.warning("마지막 메시지가 사용자 메시지가 아닙니다. Gemini API는 사용자 메시지로 끝나야 합니다.")
                # 빈 사용자 메시지 추가
                chat.send_message("계속해 주세요.")
            
            # 응답 생성
            last_response = chat.last
            if not last_response or last_response.role != "model":
                raise ValueError("Gemini API 응답이 없거나 예상된 형식이 아닙니다.")
            
            ai_message = AIMessage(content=last_response.parts[0].text)
            generation = ChatGeneration(message=ai_message)
            
            # 콜백 처리 (성공)
            if run_manager:
                run_manager.on_llm_end({"generations": [[generation]]})
            
            return ChatResult(generations=[[generation]])
            
        except Exception as e:
            # 콜백 처리 (오류)
            if run_manager:
                run_manager.on_llm_error(e)
            
            logging.error(f"Gemini 채팅 생성 오류: {str(e)}")
            raise

    # 유틸리티 메서드
    def list_models(self) -> List[str]:
        """
        사용 가능한 Gemini 모델 목록 반환 유틸리티 메서드

        Returns:
            사용 가능 모델명 목록
        """
        try:
            models = genai.list_models()
            return [model.name for model in models if "gemini" in model.name.lower()]
        except Exception as e:
            print(f"모델 목록 조회 오류: {str(e)}")
            return []

    @property
    def _llm_type(self) -> str:
        """LLM 타입을 반환합니다."""
        return "gemini"

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
    )
    def _generate_with_retry(
        self, prompt: str, run_manager: Optional[CallbackManagerForLLMRun] = None
    ) -> str:
        """재시도 로직을 포함하여 텍스트를 생성합니다."""
        try:
            # 모델 인스턴스 가져오기
            model = self.client.GenerativeModel(
                model_name=self.model,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
            )
            
            # 콘텐츠 생성 요청
            response = model.generate_content(prompt)
            
            # 응답 처리
            if hasattr(response, "candidates") and len(response.candidates) > 0:
                if hasattr(response.candidates[0], "content") and hasattr(response.candidates[0].content, "parts"):
                    result = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, "text"))
                    return result
            
            # 응답 형식이 예상과 다를 경우
            raise ValueError(f"예상하지 못한 응답 형식: {response}")
            
        except Exception as e:
            logging.error(f"Gemini API 호출 오류: {e}")
            raise

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        단일 프롬프트에 응답 생성
        
        Args:
            prompt: 입력 프롬프트
            stop: 생성 중단 토큰 (Gemini API에서는 지원되지 않음)
            run_manager: 콜백 관리자
            **kwargs: 추가 키워드 인자
            
        Returns:
            str: 생성된 텍스트 응답
        """
        self._validate_client()
        
        if stop:
            logging.warning("Gemini API는 중지 토큰을 지원하지 않습니다.")
            
        # 콜백 처리 (시작)
        if run_manager:
            run_manager.on_llm_start(
                {"name": self._llm_type}, [prompt], **kwargs
            )
            
        try:
            # 로깅
            log_llm_prompt(self._raw_model_name, "", prompt)
            
            # API 호출
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens,
                }
            )
            
            # 응답 추출
            if response.candidates and len(response.candidates) > 0:
                if response.candidates[0].finish_reason == 'BLOCKED':
                    text_response = "안전 필터에 의해 응답이 차단되었습니다."
                else:
                    text_response = response.text
            else:
                text_response = "응답 생성에 실패했습니다."
            
            # 로깅
            log_llm_response(self._raw_model_name, text_response)
            
            # 콜백 처리 (성공)
            if run_manager:
                run_manager.on_llm_end(text_response)
                
            return text_response
            
        except Exception as e:
            # 콜백 처리 (오류)
            if run_manager:
                run_manager.on_llm_error(e)
                
            logging.error(f"Gemini 텍스트 생성 오류: {str(e)}")
            raise

    def chat(
        self, 
        prompt: Union[str, List[Dict[str, str]]],
        **kwargs: Any
    ) -> Union[str, LLMResult]:
        """
        단일 프롬프트 또는 채팅 형식으로 메시지를 주고받는 메서드
        
        Args:
            prompt: 문자열 프롬프트 또는 메시지 리스트 
                   (각 메시지는 'role'과 'content' 키를 포함하는 딕셔너리)
            **kwargs: 추가 키워드 인자
            
        Returns:
            String 또는 LLMResult: 문자열 응답 또는 응답 결과 객체
        """
        self._validate_client()
        
        # 문자열 프롬프트인 경우 간단한 요청으로 처리
        if isinstance(prompt, str):
            log_llm_prompt(self._raw_model_name, "", prompt)
            
            try:
                response = self.client.generate_content(prompt)
                
                if response.candidates and len(response.candidates) > 0:
                    if response.candidates[0].finish_reason == 'BLOCKED':
                        result = "안전 필터에 의해 응답이 차단되었습니다."
                    else:
                        result = response.text
                else:
                    result = "응답 생성에 실패했습니다."
                    
                log_llm_response(self._raw_model_name, result)
                return result
                
            except Exception as e:
                error_msg = f"API 호출 오류: {str(e)}"
                log_llm_response(self._raw_model_name, error_msg)
                return error_msg
        
        # 메시지 리스트인 경우 채팅 세션으로 처리
        elif isinstance(prompt, list):
            # 로깅
            log_llm_prompt(self._raw_model_name, "", str(prompt))
            
            # Gemini 채팅 세션 생성
            chat = self.client.start_chat(history=[])
            
            # 시스템 메시지 처리
            system_message = None
            for i, message in enumerate(prompt):
                if message["role"] == "system":
                    system_message = message["content"]
                    continue
                    
                # 사용자 메시지 처리
                if message["role"] == "user":
                    content = message["content"]
                    
                    # 첫 번째 사용자 메시지에 시스템 메시지 추가
                    if system_message and i == 1:
                        content = f"시스템 메시지: {system_message}\n\n{content}"
                        system_message = None
                        
                    chat.send_message(content)
                    
                # 어시스턴트 메시지 처리 (히스토리에 추가)
                elif message["role"] == "assistant" and hasattr(chat.history, 'append'):
                    chat.history.append({
                        "role": "model",
                        "parts": [{"text": message["content"]}]
                    })
                    
            # 마지막 메시지가 사용자 메시지가 아닌 경우
            if prompt and prompt[-1]["role"] != "user":
                logging.warning("마지막 메시지가 사용자 메시지가 아닙니다. Gemini API는 사용자 메시지로 끝나야 합니다.")
                # 빈 메시지 추가
                chat.send_message("계속해 주세요.")
                
            # 응답 가져오기
            last_response = chat.last
            if not last_response or last_response.role != "model":
                raise ValueError("Gemini API 응답이 없거나 예상된 형식이 아닙니다.")
                
            response_text = last_response.parts[0].text
            
            # 로깅
            log_llm_response(self._raw_model_name, response_text)
            
            # 응답 및 메타데이터 반환
            return LLMResult(
                response=response_text,
                metadata={
                    "model": self.model_name,
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens,
                }
            )
        else:
            raise ValueError(f"지원하지 않는 프롬프트 타입입니다: {type(prompt)}")

    def generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        callbacks: Optional[Any] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """여러 프롬프트에 대해 생성을 수행합니다.

        Args:
            prompts: 입력 프롬프트 목록
            stop: 중지 단어 목록
            callbacks: 콜백 핸들러 목록
            **kwargs: 추가 매개변수

        Returns:
            LLMResult 객체
        """
        generations = []
        
        for prompt in prompts:
            # 콜백 관리자 설정
            callback_manager = CallbackManagerForLLMRun.configure(
                callbacks, self, {"verbose": self.verbose}
            )
            
            # 텍스트 생성
            generation_text = self._call(
                prompt=prompt,
                stop=stop,
                run_manager=callback_manager,
                **kwargs,
            )
            
            # 결과 추가
            generations.append([Generation(text=generation_text)])
            
        return LLMResult(generations=generations)

    def _prepare_messages_for_chat(self, messages: list[dict]) -> list[ContentDict]:
        """
        LangChain 메시지 형식을 Gemini Content 형식으로 변환
        
        Args:
            messages: LangChain 형식의 메시지 목록
            
        Returns:
            Gemini Content 형식으로 변환된 메시지 목록
        """
        gemini_messages = []
        
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            
            # 메시지 내용이 문자열이 아닌 경우 처리
            if not isinstance(content, str):
                if isinstance(content, list):
                    # 멀티모달 콘텐츠 처리 로직 추가 가능
                    # 현재는 텍스트만 추출하여 사용
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    content = " ".join(text_parts)
                else:
                    # 기타 타입의 경우 문자열로 변환
                    content = str(content)
            
            if role == "user":
                gemini_messages.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                gemini_messages.append({"role": "model", "parts": [{"text": content}]})
            elif role == "system":
                # Gemini는 system 메시지를 직접 지원하지 않으므로 첫 번째 user 메시지에 포함
                if not gemini_messages:
                    gemini_messages.append({"role": "user", "parts": [{"text": content}]})
                elif gemini_messages[0]["role"] == "user":
                    gemini_messages[0]["parts"][0]["text"] = f"{content}\n\n{gemini_messages[0]['parts'][0]['text']}"
                else:
                    gemini_messages.insert(0, {"role": "user", "parts": [{"text": content}]})
                    
        return gemini_messages
