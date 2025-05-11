# Common LLM interface.
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator

from llm_source_to_kg.schema.llm import *



class LLMInterface(ABC):
    """
    LLM 공통 인터페이스
    모든 LLM 구현체는 이 인터페이스를 상속받아야 함
    """
    
    @abstractmethod
    async def call_llm(
        self, 
        prompt: str, 
        config: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """
        단일 프롬프트로 LLM 호출
        
        Args:
            prompt: LLM에 전달할 프롬프트
            config: LLM 설정
            
        Returns:
            LLM 응답 객체
        """
        pass
    
    @abstractmethod
    async def chat_llm(
        self, 
        messages: List[LLMMessage], 
        config: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """
        메시지 목록으로 LLM 채팅 호출
        
        Args:
            messages: LLM에 전달할 메시지 목록
            config: LLM 설정
            
        Returns:
            LLM 응답 객체
        """
        pass
    
    @abstractmethod
    async def stream_chat_llm(
        self, 
        messages: List[LLMMessage], 
        config: Optional[LLMConfig] = None
    ) -> AsyncGenerator[str, None]:
        """
        메시지 목록으로 LLM 채팅 스트리밍 호출
        
        Args:
            messages: LLM에 전달할 메시지 목록
            config: LLM 설정
            
        Yields:
            스트리밍 응답 토큰
        """
        pass
    
    def create_system_message(self, content: str) -> LLMMessage:
        """시스템 메시지 생성"""
        return LLMMessage(role=LLMRole.SYSTEM, content=content)
    
    def create_user_message(self, content: str) -> LLMMessage:
        """사용자 메시지 생성"""
        return LLMMessage(role=LLMRole.USER, content=content)
    
    def create_assistant_message(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> LLMMessage:
        """어시스턴트 메시지 생성"""
        return LLMMessage(role=LLMRole.ASSISTANT, content=content, tool_calls=tool_calls)
    
    def create_function_message(self, content: str, name: str, tool_call_id: Optional[str] = None) -> LLMMessage:
        """함수 메시지 생성"""
        return LLMMessage(role=LLMRole.FUNCTION, content=content, name=name, tool_call_id=tool_call_id)
    
    def create_tool_message(self, content: str, tool_call_id: str) -> LLMMessage:
        """도구 메시지 생성"""
        return LLMMessage(role=LLMRole.TOOL, content=content, tool_call_id=tool_call_id)