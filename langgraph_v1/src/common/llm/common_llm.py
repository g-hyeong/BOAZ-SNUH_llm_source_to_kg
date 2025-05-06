import abc
from typing import Any, Dict, List, Optional, Union, Callable, TypedDict, Awaitable
import json
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun
from pydantic import Field, PrivateAttr

from common.logging import log_llm_prompt, log_llm_response

class LLMResult(TypedDict, total=False):
    """
    LLM 응답 결과를 위한 TypedDict
    """
    response: str  # LLM 응답 텍스트
    updated_history: List[Dict[str, str]]  # 업데이트된 대화 기록
    metadata: Dict[str, Any]  # 추가 메타데이터

class CommonLLM(BaseChatModel):
    """
    모든 LLM 구현 클래스를 위한 추상 베이스 클래스
    LLM 설정, 호출, 채팅 기능의 공통 인터페이스 정의
    LangChain 및 LangGraph 통합을 위한 BaseChatModel 상속
    """
    model_name: str = Field(default="unknown", description="LLM 모델 이름")
    temperature: float = Field(default=0.7, description="생성 다양성 조절 매개변수")
    max_tokens: int = Field(default=4096, description="최대 출력 토큰 수")
    
    
    
    class Config:
        """Pydantic 설정"""
        arbitrary_types_allowed = True
    
    def __init__(
        self, 
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ):
        """
        CommonLLM 클래스 생성자

        Args:
            model_name: LLM 모델 이름
            temperature: 생성 다양성 조절 매개변수
            max_tokens: 최대 출력 토큰 수
            **kwargs: 추가 인자
        """
        # 기본값을 명시적으로 설정하여 하위 클래스에서 오버라이드할 수 있게 함
        model_kwargs = {}
        if model_name is not None:
            model_kwargs["model_name"] = model_name
        if temperature is not None:
            model_kwargs["temperature"] = temperature
        if max_tokens is not None:
            model_kwargs["max_tokens"] = max_tokens
        
        # BaseChatModel 초기화
        super().__init__(**model_kwargs, **kwargs)
        
        
    def _llm_type(self) -> str:
        """LLM 유형 반환"""
        return "custom_llm"

    def call_llm(self, system_prompt: str, human_prompt: str) -> str:
        """
        LLM 호출 메서드
        단일 요청-응답 상호작용용

        Args:
            system_prompt: LLM 역할/맥락 설정 시스템 프롬프트
            human_prompt: 사용자 요청 프롬프트

        Returns:
            LLM 응답 문자열
        """
        
        
        # 상세 로깅
        log_llm_prompt(self.model_name, system_prompt, human_prompt)
        
        try:
            response = self._call_request_by_llm(system_prompt, human_prompt)
            response_len = len(response)
            
            # 응답 로깅
            log_llm_response(self.model_name, response)
            
            
            return response
        except Exception as e:
            raise

    def chat_llm(
        self,
        system_prompt: str,
        human_prompt: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> LLMResult:
        """
        LLM 채팅 메서드
        대화 기록 관리로 컨텍스트 유지

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

        chat_history_count = len(chat_history) if chat_history else 0
        
        
        # 상세 로깅
        log_llm_prompt(
            self.model_name, 
            system_prompt, 
            human_prompt, 
            chat_history_length=chat_history_count
        )
        
        try:
            result = self._chat_request_by_llm(system_prompt, human_prompt, chat_history)
            
            if isinstance(result, dict) and "response" in result:
                response_len = len(result["response"])
                log_llm_response(self.model_name, result["response"])
            else:
                raise ValueError("예상치 않은 응답 형식입니다.")
                
            return result
        except Exception as e:
            raise
    
    def _convert_messages_to_langchain(self, 
                                      system_prompt: str,
                                      human_prompt: str, 
                                      chat_history: Optional[List[Dict[str, str]]] = None) -> List[BaseMessage]:
        """
        일반 메시지 형식을 LangChain 메시지 형식으로 변환

        Args:
            system_prompt: 시스템 프롬프트
            human_prompt: 사용자 프롬프트
            chat_history: 대화 기록

        Returns:
            LangChain 메시지 리스트
        """
        messages = []
        
        # 시스템 메시지 추가
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
            
        # 대화 기록 추가
        if chat_history:
            for msg in chat_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
                elif msg["role"] == "system" and not any(isinstance(m, SystemMessage) for m in messages):
                    messages.append(SystemMessage(content=msg["content"]))
        
        # 현재 사용자 메시지 추가
        messages.append(HumanMessage(content=human_prompt))
        
        return messages
    
    def _convert_langchain_to_messages(self, 
                                      lc_messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """
        LangChain 메시지 형식을 일반 메시지 형식으로 변환

        Args:
            lc_messages: LangChain 메시지 리스트

        Returns:
            일반 메시지 딕셔너리 리스트
        """
        messages = []
        
        for msg in lc_messages:
            if isinstance(msg, SystemMessage):
                messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, ChatMessage):
                role = msg.role
                if role == "system":
                    messages.append({"role": "system", "content": msg.content})
                elif role == "user" or role == "human":
                    messages.append({"role": "user", "content": msg.content})
                elif role == "assistant" or role == "ai":
                    messages.append({"role": "assistant", "content": msg.content})
                
        return messages
    
    # LangChain 인터페이스 구현
    def _generate(
        self, 
        messages: List[BaseMessage], 
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> ChatResult:
        """
        LangChain 인터페이스 : 메시지 목록에서 생성
        
        Args:
            messages: 메시지 리스트
            stop: 생성 중단 토큰 리스트
            run_manager: 콜백 관리자
            **kwargs: 추가 키워드 인자
            
        Returns:
            ChatResult: 채팅 생성 결과
        """
        # 시스템 프롬프트와 마지막 사용자 메시지 추출
        system_prompt = ""
        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = msg.content
                break
                
        # 사용자 메시지 목록 추출 (마지막 메시지만 사용)
        human_msg = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                human_msg = msg
                break
        
        if not human_msg:
            raise ValueError("사용자 메시지가 없습니다.")
            
        # 대화 기록 생성 (시스템 및 현재 사용자 메시지 제외)
        chat_history = self._convert_langchain_to_messages(
            [msg for msg in messages if not (
                isinstance(msg, SystemMessage) or msg == human_msg
            )]
        )
        
        # LLM 호출
        result = self._chat_request_by_llm(
            system_prompt=system_prompt,
            human_prompt=human_msg.content,
            chat_history=chat_history
        )
        
        # 응답 포맷팅
        chat_generation = ChatGeneration(
            message=AIMessage(content=result["response"]),
            generation_info={"updated_history": result.get("updated_history", [])}
        )
        
        return ChatResult(generations=[chat_generation])
    
    @abc.abstractmethod
    def _call_request_by_llm(self, system_prompt: str, human_prompt: str) -> str:
        """
        LLM 요청 메서드
        추상 메서드로 하위 클래스에서 구현 필요
        
        Args:
            system_prompt: 시스템 프롬프트
            human_prompt: 사용자 프롬프트
            
        Returns:
            LLM 응답 문자열
        """
        raise NotImplementedError("LLM 요청 메서드는 하위 클래스에서 구현 필요")
    
    @abc.abstractmethod
    def _chat_request_by_llm(
        self, 
        system_prompt: str, 
        human_prompt: str, 
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> LLMResult:
        """
        LLM 채팅 요청 메서드
        추상 메서드로 하위 클래스에서 구현 필요
        
        Args:
            system_prompt: 시스템 프롬프트
            human_prompt: 사용자 프롬프트
            chat_history: 대화 기록
            
        Returns:
            LLM 응답 결과 (LLMResult)
        """
        raise NotImplementedError("LLM 채팅 요청 메서드는 하위 클래스에서 구현 필요")
        