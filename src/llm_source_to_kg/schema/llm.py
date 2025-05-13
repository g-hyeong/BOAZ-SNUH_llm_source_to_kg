from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

class LLMRole(str, Enum):
    """LLM 메시지 역할 정의"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"  # langgraph 도구 호출 결과를 위한 역할


class LLMMessage(BaseModel):
    """LLM 메시지 구조 정의"""
    role: LLMRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class LLMUsage(BaseModel):
    """LLM 사용량 정보"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """LLM 응답 구조 정의"""
    content: str
    model: str
    usage: LLMUsage
    raw_response: Any = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class LLMConfig(BaseModel):
    """LLM 설정 구조 정의"""
    model: str
    temperature: float = 0.1
    max_tokens: Optional[int] = 8192
    top_p: float = 0.4
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None