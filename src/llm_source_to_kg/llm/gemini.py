# py for Gemini LLM
import os
import json
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
import google.generativeai as genai

from llm_source_to_kg.config import config

from .common_llm_interface import (
    LLMInterface, 
    LLMMessage, 
    LLMResponse, 
    LLMConfig, 
    LLMRole,
    LLMUsage
)



class GeminiLLM(LLMInterface):
    """
    Google Gemini LLM 구현체
    """
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        """
        Gemini LLM 초기화
        
        Args:
            api_key: Google AI API 키 (없으면 환경 변수에서 가져옴)
        """
        self.api_key = config.GEMINI_API_KEY
        
        # Gemini API 초기화
        genai.configure(api_key=self.api_key)
        
        # 지원되는 모델 목록
        self.supported_models = {
            "gemini-2.5-pro": "gemini-2.5-pro-preview-05-06",
            "gemini-2.5-flash": "gemini-2.5-flash-preview-04-17",
            "gemini-2.0-flash": "gemini-2.0-flash",
        }
        
        # 기본 모델 설정
        self.default_model = self.supported_models[model]
    
    def _convert_messages_to_gemini_format(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """
        LLMMessage 목록을 Gemini 형식으로 변환
        
        Args:
            messages: LLM 메시지 목록
            
        Returns:
            Gemini 형식의 메시지 목록
        """
        gemini_messages = []
        
        # Gemini는 system 메시지를 별도로 처리해야 함
        system_content = ""
        for message in messages:
            if message.role == LLMRole.SYSTEM:
                system_content += message.content + "\n"
        
        # 시스템 메시지가 있으면 첫 번째 사용자 메시지에 추가
        for i, message in enumerate(messages):
            if message.role == LLMRole.SYSTEM:
                continue
                
            if message.role == LLMRole.USER and system_content and not gemini_messages:
                # 첫 번째 사용자 메시지에 시스템 메시지 추가
                gemini_messages.append({
                    "role": "user",
                    "parts": [{"text": f"{system_content}\n\n{message.content}"}]
                })
            elif message.role == LLMRole.USER:
                # 사용자 메시지에 멀티모달 컨텐츠가 있는지 확인
                gemini_messages.append({
                    "role": "user",
                    "parts": [{"text": message.content}]
                })
            elif message.role == LLMRole.ASSISTANT:
                # 함수 호출이 있는지 확인
                if message.tool_calls:
                    # 첫 번째 tool_call만 처리 (여러 개가 있을 경우)
                    tool_call = message.tool_calls[0] if message.tool_calls else None
                    gemini_messages.append({
                        "role": "model",
                        "parts": [
                            {
                                "text": message.content,
                                "function_call": {
                                    "name": tool_call.get("name", "") if tool_call else "",
                                    "args": tool_call.get("arguments", {}) if tool_call else {}
                                }
                            }
                        ]
                    })
                else:
                    gemini_messages.append({
                        "role": "model",
                        "parts": [{"text": message.content}]
                    })
            elif message.role == LLMRole.FUNCTION:
                # Gemini 2.0 이상은 함수 결과를 직접 지원
                gemini_messages.append({
                    "role": "function",
                    "parts": [{
                        "function_response": {
                            "name": message.name,
                            "response": message.content
                        }
                    }]
                })
            elif message.role == LLMRole.TOOL:
                # 도구 호출 결과 처리
                tool_id = f" (ID: {message.tool_call_id})" if message.tool_call_id else ""
                gemini_messages.append({
                    "role": "user",
                    "parts": [{"text": f"도구{tool_id} 결과: {message.content}"}]
                })
        
        return gemini_messages
    
    def _get_model_name(self, config: Optional[LLMConfig]) -> str:
        """
        설정에서 모델 이름 가져오기
        
        Args:
            config: LLM 설정
            
        Returns:
            Gemini 모델 이름
        """
        if config and config.model:
            model_name = config.model
            # 모델 이름에 'gemini-'가 없으면 추가
            if not model_name.startswith("gemini-"):
                model_name = f"gemini-{model_name}"
            
            # 지원되는 모델인지 확인
            if model_name in self.supported_models:
                return self.supported_models[model_name]
            else:
                return model_name  # 사용자가 직접 지정한 모델 이름 사용
        
        return self.default_model
    
    def _create_generation_config(self, config: Optional[LLMConfig]) -> Dict[str, Any]:
        """
        LLMConfig를 Gemini 생성 설정으로 변환
        
        Args:
            config: LLM 설정
            
        Returns:
            Gemini 생성 설정
        """
        if not config:
            return {
                "temperature": 0.7,
                "top_p": 1.0,
                "max_output_tokens": 1024,
            }
        
        generation_config = {
            "temperature": config.temperature,
            "top_p": config.top_p,
        }
        
        if config.max_tokens:
            generation_config["max_output_tokens"] = config.max_tokens
        
        # 함수 호출 설정 추가
        if hasattr(config, "functions") and config.functions:
            generation_config["tools"] = [{
                "function_declarations": config.functions
            }]
        
        return generation_config
    
    def _calculate_usage(self, prompt: str, response_text: str) -> LLMUsage:
        """
        토큰 사용량 추정 (정확한 계산은 아님)
        
        Args:
            prompt: 입력 프롬프트
            response_text: 응답 텍스트
            
        Returns:
            토큰 사용량 추정치
        """
        # 매우 간단한 추정: 영어 기준 단어 수의 약 4/3배
        prompt_tokens = len(prompt.split()) * 4 // 3
        completion_tokens = len(response_text.split()) * 4 // 3
        
        return LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    
    async def call_llm(self, prompt: str, config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        단일 프롬프트로 Gemini LLM 호출
        
        Args:
            prompt: LLM에 전달할 프롬프트
            config: LLM 설정
            
        Returns:
            LLM 응답 객체
        """
        model_name = self._get_model_name(config)
        generation_config = self._create_generation_config(config)
        
        # Gemini 모델 생성
        model = genai.GenerativeModel(model_name=model_name)
        
        # 함수 호출 설정이 있는 경우 추가
        if "tools" in generation_config:
            model = genai.GenerativeModel(
                model_name=model_name,
                tools=generation_config.pop("tools")
            )
        
        # 응답 생성
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        response_text = response.text
        
        # 함수 호출 처리
        tool_calls = None
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                content = candidate.content
                if hasattr(content, "parts") and content.parts:
                    for part in content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            tool_calls = [{
                                "name": part.function_call.name,
                                "arguments": part.function_call.args
                            }]
        
        # 사용량 추정
        usage = self._calculate_usage(prompt, response_text)
        
        return LLMResponse(
            content=response_text,
            model=model_name,
            usage=usage,
            raw_response=response,
            tool_calls=tool_calls
        )
    
    async def chat_llm(self, messages: List[LLMMessage], config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        메시지 목록으로 Gemini 채팅 호출
        
        Args:
            messages: LLM에 전달할 메시지 목록
            config: LLM 설정
            
        Returns:
            LLM 응답 객체
        """
        model_name = self._get_model_name(config)
        generation_config = self._create_generation_config(config)
        
        # Gemini 형식으로 메시지 변환
        gemini_messages = self._convert_messages_to_gemini_format(messages)
        
        # 메시지가 없으면 빈 응답 반환
        if not gemini_messages:
            return LLMResponse(
                content="",
                model=model_name,
                usage=LLMUsage(),
                raw_response=None
            )
        
        # Gemini 모델 생성
        tools = None
        if "tools" in generation_config:
            tools = generation_config.pop("tools")
            
        model = genai.GenerativeModel(
            model_name=model_name,
            tools=tools
        )
        
        # 채팅 세션 생성
        chat = model.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
        
        # 마지막 메시지 전송 및 응답 생성
        last_message = gemini_messages[-1]
        response = chat.send_message(
            last_message["parts"][0]["text"],
            generation_config=generation_config
        )
        
        response_text = response.text
        
        # 함수 호출 처리
        tool_calls = None
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                content = candidate.content
                if hasattr(content, "parts") and content.parts:
                    for part in content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            tool_calls = [{
                                "name": part.function_call.name,
                                "arguments": part.function_call.args
                            }]
        
        # 모든 메시지 내용을 합쳐서 프롬프트 토큰 추정
        all_prompts = "\n".join([msg["parts"][0]["text"] for msg in gemini_messages])
        
        # 사용량 추정
        usage = self._calculate_usage(all_prompts, response_text)
        
        return LLMResponse(
            content=response_text,
            model=model_name,
            usage=usage,
            raw_response=response,
            tool_calls=tool_calls
        )
    
    async def stream_chat_llm(self, messages: List[LLMMessage], config: Optional[LLMConfig] = None) -> AsyncGenerator[str, None]:
        """
        메시지 목록으로 Gemini 채팅 스트리밍 호출
        
        Args:
            messages: LLM에 전달할 메시지 목록
            config: LLM 설정
            
        Yields:
            스트리밍 응답 토큰
        """
        model_name = self._get_model_name(config)
        generation_config = self._create_generation_config(config)
        
        # 스트리밍 활성화
        generation_config["stream"] = True
        
        # 함수 호출 설정 추출
        tools = None
        if "tools" in generation_config:
            tools = generation_config.pop("tools")
        
        # Gemini 형식으로 메시지 변환
        gemini_messages = self._convert_messages_to_gemini_format(messages)
        
        # 메시지가 없으면 빈 응답 반환
        if not gemini_messages:
            yield ""
            return
        
        # Gemini 모델 생성
        model = genai.GenerativeModel(
            model_name=model_name,
            tools=tools
        )
        
        # 채팅 세션 생성
        chat = model.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
        
        # 마지막 메시지 전송 및 응답 생성
        last_message = gemini_messages[-1]
        
        # 스트리밍 응답 생성
        response_stream = chat.send_message(
            last_message["parts"][0]["text"],
            generation_config=generation_config,
            stream=True
        )
        
        # 응답 스트리밍
        for chunk in response_stream:
            if hasattr(chunk, "text") and chunk.text:
                yield chunk.text
            # 비동기 환경에서 다른 태스크에 양보
            await asyncio.sleep(0)