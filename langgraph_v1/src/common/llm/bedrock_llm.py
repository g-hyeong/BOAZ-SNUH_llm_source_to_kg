import json
import asyncio
from typing import Any, Dict, List, Optional, Union
import boto3
from botocore.exceptions import ClientError

from src.common.llm.common_llm import CommonLLM, LLMResult
from src.common.logging import log_llm_prompt, log_llm_response
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.messages import AIMessage, BaseMessage

class BedrockLLM(CommonLLM):
    """
    AWS Bedrock API를 통해 다양한 LLM 모델 접근 클래스
    LangChain 및 LangGraph와 통합을 위한 구현
    """
    client: Any = None
    
    def __init__(self, **kwargs: Any) -> None:
        """
        AWS Bedrock LLM 클래스 생성자

        Args:
            **kwargs: AWS Bedrock LLM 설정 파라미터
                - region_name: AWS 리전 이름 (기본값: us-east-1)
                - model_id: 사용 모델 ID (기본값: anthropic.claude-v2)
                - aws_access_key_id: AWS 액세스 키 ID (선택적)
                - aws_secret_access_key: AWS 시크릿 액세스 키 (선택적)
                - profile_name: AWS 프로필 이름 (선택적)
                - temperature: 생성 다양성 조절 매개변수 (기본값: 0.7)
                - max_tokens: 최대 출력 토큰 수 (기본값: 4096)
        """
        # Bedrock 특화 매개변수 추출
        model_id = kwargs.get("model_id", "anthropic.claude-v2")
        model_name = f"bedrock/{model_id}"
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
        self.model_id = model_id
        
        # Bedrock 클라이언트 초기화
        self._initialize_bedrock(**kwargs)
        
    def _initialize_bedrock(self, **kwargs: Any) -> None:
        """
        AWS Bedrock 클라이언트 초기화 및 설정
        
        Args:
            **kwargs: 초기화 파라미터
            
        Raises:
            ValueError: 클라이언트 초기화 실패 시
        """
        # 기본 설정값
        region_name = kwargs.get("region_name", "us-east-1")
        
        # AWS 인증 정보 설정
        session_kwargs = {"region_name": region_name}
        
        if "aws_access_key_id" in kwargs and "aws_secret_access_key" in kwargs:
            session_kwargs["aws_access_key_id"] = kwargs["aws_access_key_id"]
            session_kwargs["aws_secret_access_key"] = kwargs["aws_secret_access_key"]
        elif "profile_name" in kwargs:
            session_kwargs["profile_name"] = kwargs["profile_name"]
        
        try:
            # Bedrock 클라이언트 생성
            self.session = boto3.Session(**session_kwargs)
            self.client = self.session.client(service_name="bedrock-runtime")
            print(f"AWS Bedrock 클라이언트 초기화 성공. 리전: {region_name}, 모델: {self.model_id}")
        except Exception as e:
            print(f"AWS Bedrock 클라이언트 초기화 오류: {str(e)}")
            self.client = None
            raise ValueError(f"AWS Bedrock 클라이언트 초기화 오류: {str(e)}")
            
    def _validate_client(self) -> None:
        """
        클라이언트가 초기화되었는지 확인
        
        Raises:
            ValueError: 클라이언트가 초기화되지 않은 경우
        """
        if not self.client:
            raise ValueError("Bedrock 클라이언트가 초기화되지 않았습니다.")

    def _call_request_by_llm(self, system_prompt: str, human_prompt: str) -> str:
        """
        AWS Bedrock API로 LLM 질의 메서드

        Args:
            system_prompt: LLM 역할/맥락 설정 시스템 프롬프트
            human_prompt: 사용자 요청 프롬프트

        Returns:
            LLM 응답 문자열
        """
        self._validate_client()
        
        try:
            # 모델 패밀리별 요청 형식 구성
            if self.model_id.startswith("anthropic."):
                # Anthropic Claude 모델 요청 형식
                prompt = f"\n\nHuman: {system_prompt}\n\n{human_prompt}\n\nAssistant:"
                body = json.dumps({
                    "prompt": prompt,
                    "max_tokens_to_sample": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": 0.9,
                })
            elif self.model_id.startswith("ai21."):
                # AI21 Jurassic 모델 요청 형식
                prompt = f"{system_prompt}\n\n{human_prompt}"
                body = json.dumps({
                    "prompt": prompt,
                    "maxTokens": self.max_tokens,
                    "temperature": self.temperature,
                    "topP": 0.9,
                })
            elif self.model_id.startswith("amazon.titan-"):
                # Amazon Titan 모델 요청 형식
                prompt = f"System: {system_prompt}\nHuman: {human_prompt}\nAssistant:"
                body = json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": self.max_tokens,
                        "temperature": self.temperature,
                        "topP": 0.9,
                    }
                })
            else:
                # 기본 요청 형식 (다른 모델용)
                prompt = f"{system_prompt}\n\n{human_prompt}"
                body = json.dumps({
                    "prompt": prompt,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                })
            
            # API 호출
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body
            )
            
            # 응답 파싱
            response_body = json.loads(response.get("body").read())
            
            # 모델 패밀리별 응답 형식 처리
            if self.model_id.startswith("anthropic."):
                response_text = response_body.get("completion", "")
            elif self.model_id.startswith("ai21."):
                response_text = response_body.get("completions", [{}])[0].get("data", {}).get("text", "")
            elif self.model_id.startswith("amazon.titan-"):
                response_text = response_body.get("results", [{}])[0].get("outputText", "")
            else:
                response_text = str(response_body)
            
            return response_text
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            return f"AWS Bedrock API 호출 오류: {error_code} - {error_msg}"
        except Exception as e:
            return f"API 호출 오류: {str(e)}"

    def _chat_request_by_llm(
        self,
        system_prompt: str,
        human_prompt: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> LLMResult:
        """
        AWS Bedrock API로 대화 컨텍스트 유지 채팅 메서드

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
        
        try:
            # 모델 패밀리별 요청 형식 구성
            if self.model_id.startswith("anthropic.claude-"):
                # Claude 3 지원 모델인 경우 메시지 형식 사용
                # 시스템 메시지 설정
                messages = [{"role": "system", "content": system_prompt}]
                
                # 대화 기록 추가
                for msg in updated_history:
                    if msg["role"] in ["user", "assistant"]:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                
                # 현재 사용자 메시지 추가
                messages.append({"role": "user", "content": human_prompt})
                
                # API 요청 본문 구성
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "messages": messages
                })
                
                # API 호출
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=body
                )
                
                # 응답 파싱
                response_body = json.loads(response.get("body").read())
                ai_response = response_body.get("content", [{}])[0].get("text", "")
                
            elif self.model_id.startswith("anthropic."):
                # 이전 Claude 모델용 (Claude 1, Claude 2)
                
                # 대화 기록을 Claude의 'Human' / 'Assistant' 형식으로 변환
                conversation = ""
                
                # 대화 기록 추가
                for msg in updated_history:
                    role = msg["role"]
                    content = msg["content"]
                    
                    if role == "system" and not conversation:
                        # 시스템 프롬프트는 첫 번째 Human 메시지에 포함
                        conversation += f"\n\nHuman: {content}\n\n"
                    elif role == "user":
                        conversation += f"\n\nHuman: {content}\n\n"
                    elif role == "assistant":
                        conversation += f"Assistant: {content}"
                
                # 현재 사용자 메시지와 시스템 프롬프트 추가
                if not any(msg.get("role") == "system" for msg in updated_history):
                    conversation += f"\n\nHuman: {system_prompt}\n\n{human_prompt}\n\n"
                else:
                    conversation += f"\n\nHuman: {human_prompt}\n\n"
                
                conversation += "Assistant:"
                
                # API 요청 본문 구성
                body = json.dumps({
                    "prompt": conversation,
                    "max_tokens_to_sample": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": 0.9,
                })
                
                # API 호출
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=body
                )
                
                # 응답 파싱
                response_body = json.loads(response.get("body").read())
                ai_response = response_body.get("completion", "")
                
            else:
                # 다른 모델의 경우 단일 호출 방식 사용
                # 대화 기록과 현재 메시지를 하나의 프롬프트로 결합
                full_prompt = f"System: {system_prompt}\n\n"
                
                for msg in updated_history:
                    role = msg["role"]
                    content = msg["content"]
                    
                    if role == "user":
                        full_prompt += f"User: {content}\n"
                    elif role == "assistant":
                        full_prompt += f"Assistant: {content}\n"
                
                full_prompt += f"User: {human_prompt}\nAssistant:"
                
                # 단순 call_llm 호출로 응답 얻기
                ai_response = self._call_request_by_llm("", full_prompt)
            
            # 응답을 대화 기록에 추가
            updated_history.append({"role": "user", "content": human_prompt})
            updated_history.append({"role": "assistant", "content": ai_response})
            
            return {
                "response": ai_response,
                "updated_history": updated_history,
                "metadata": {"model": self.model_id}
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            error_response = f"AWS Bedrock API 호출 오류: {error_code} - {error_msg}"
            
            # 에러 발생해도 대화 기록 업데이트
            updated_history.append({"role": "user", "content": human_prompt})
            
            return {
                "response": error_response,
                "updated_history": updated_history,
                "metadata": {"error": error_msg}
            }
        except Exception as e:
            error_response = f"API 호출 오류: {str(e)}"
            
            # 에러 발생해도 대화 기록 업데이트
            updated_history.append({"role": "user", "content": human_prompt})
            
            return {
                "response": error_response,
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
        AWS Bedrock API로 텍스트 임베딩 생성 메서드

        Args:
            text: 임베딩 생성할 텍스트

        Returns:
            텍스트 임베딩 벡터
        """
        self._validate_client()
        
        # 임베딩 모델 ID (Titan Embeddings 사용)
        embedding_model_id = "amazon.titan-embed-text-v1"
        
        try:
            # API 요청 본문 구성
            body = json.dumps({
                "inputText": text
            })
            
            # API 호출
            response = self.client.invoke_model(
                modelId=embedding_model_id,
                body=body
            )
            
            # 응답 파싱
            response_body = json.loads(response.get("body").read())
            embeddings = response_body.get("embedding", [])
            
            return embeddings
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            print(f"AWS Bedrock 임베딩 API 호출 오류: {error_code} - {error_msg}")
            return []
        except Exception as e:
            print(f"임베딩 API 호출 오류: {str(e)}")
            return []
            
    def list_models(self) -> List[str]:
        """
        사용 가능한 Bedrock 모델 목록 반환 유틸리티 메서드
        
        Returns:
            사용 가능한 모델 ID 목록
        """
        try:
            # Bedrock 모델 관리 클라이언트 생성
            bedrock_client = self.session.client(service_name="bedrock")
            response = bedrock_client.list_foundation_models()
            
            models = []
            for model in response.get("modelSummaries", []):
                model_id = model.get("modelId")
                if model_id:
                    models.append(model_id)
                    
            return models
        except Exception as e:
            print(f"모델 목록 조회 오류: {str(e)}")
            return []
