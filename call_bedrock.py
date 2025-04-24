import boto3
import json
import logging
from typing import Dict, Any, Optional

# 설정 가져오기
from bedrock_config import (
    AWS_PROFILE,
    AWS_REGION,
    MODELS,
    REQUEST_TIMEOUT,
    BEDROCK_RUNTIME_ENDPOINT,
    DEFAULT_MODEL_KEY
)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Boto3 Client Management ---
def get_bedrock_client(profile_name: str = AWS_PROFILE, region_name: str = AWS_REGION) -> boto3.client:
    """
    지정된 프로필과 리전을 사용하여 Bedrock 런타임 클라이언트를 생성하고 반환합니다.
    Singleton 패턴 대신 필요할 때마다 생성하여 스레드 안정성 및 구성 유연성을 높입니다.

    Args:
        profile_name (str): 사용할 AWS 프로필 이름.
        region_name (str): 사용할 AWS 리전 이름.

    Returns:
        boto3.client: Bedrock 런타임 클라이언트.
    """
    try:
        logger.debug(f"Creating Bedrock client with profile '{profile_name}' in region '{region_name}'.")
        session = boto3.Session(profile_name=profile_name)
        # boto3.client의 config 파라미터를 사용하여 타임아웃 설정
        from botocore.config import Config
        config = Config(
            read_timeout=REQUEST_TIMEOUT,
            connect_timeout=REQUEST_TIMEOUT,
            retries={'max_attempts': 3} # 기본 재시도 설정
        )
        client = session.client(
            service_name='bedrock-runtime',
            region_name=region_name,
            endpoint_url=BEDROCK_RUNTIME_ENDPOINT, # 엔드포인트 명시
            config=config
        )
        logger.debug("Bedrock client created successfully.")
        return client
    except Exception as e:
        logger.error(f"Failed to create Bedrock client: {e}", exc_info=True)
        raise ConnectionError(f"Could not create Bedrock client: {e}")

# --- Request Body Builders ---
# 각 모델 유형에 맞는 요청 본문을 생성하는 함수들

def build_claude_request_body(prompt: str, max_tokens: int, temperature: float, top_p: float, top_k: int, stop_sequences=None) -> Dict[str, Any]:
    """Anthropic Claude 모델의 요청 본문을 생성합니다."""
    return {
        "anthropic_version": "bedrock-2023-05-31", # 모델 설정에서 가져올 수도 있음
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "stop_sequences": stop_sequences if stop_sequences is not None else [],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    }

def build_llama_request_body(prompt: str, max_tokens: int, temperature: float, top_p: float, **kwargs) -> Dict[str, Any]:
    """Meta Llama 모델의 요청 본문을 생성합니다."""
    return {
        "prompt": prompt,
        "max_gen_len": max_tokens, # 파라미터 이름 주의
        "temperature": temperature,
        "top_p": top_p
    }

# --- Response Parsers ---
# 각 모델 유형의 응답에서 텍스트를 추출하는 함수들

def parse_claude_response(response_body: Dict[str, Any]) -> str:
    """Claude 모델 응답에서 텍스트를 추출합니다."""
    content_list = response_body.get("content", [])
    if content_list and isinstance(content_list, list):
        first_content = content_list[0]
        if isinstance(first_content, dict) and first_content.get("type") == "text":
            return first_content.get("text", "")
    # 호환성을 위한 Claude v2 형식 처리
    elif "completion" in response_body:
        return response_body.get("completion", "")
    logger.warning(f"Could not parse text from Claude response: {response_body}")
    return ""

def parse_llama_response(response_body: Dict[str, Any]) -> str:
    """Llama 모델 응답에서 텍스트를 추출합니다."""
    generation = response_body.get("generation", "")
    if not generation:
        logger.warning(f"Could not parse text from Llama response: {response_body}")
    return generation

# --- Core Invocation Logic ---
def invoke_model(
    prompt: str,
    model_key: str = DEFAULT_MODEL_KEY,
    max_tokens: int = 1024, # 기본값 증가
    temperature: float = 0.7,
    top_p: Optional[float] = 0.9,
    top_k: Optional[int] = 250,
    **kwargs # 추가 파라미터 허용
) -> Dict[str, Any]:
    """
    지정된 Bedrock 모델을 호출하고 원시 응답 본문을 반환합니다.

    Args:
        prompt (str): 모델에 전달할 프롬프트.
        model_key (str): 사용할 모델의 키 (bedrock_config.MODELS 참조).
        max_tokens (int): 생성할 최대 토큰 수.
        temperature (float): 샘플링 온도 (0.0 ~ 1.0).
        top_p (Optional[float]): Nucleus 샘플링 확률.
        top_k (Optional[int]): Top-k 샘플링.
        **kwargs: 각 모델 빌더에 전달될 추가 파라미터.

    Returns:
        Dict[str, Any]: 모델의 원시 응답 본문 (JSON 디코딩됨).

    Raises:
        ValueError: 유효하지 않은 model_key가 제공된 경우.
        ConnectionError: Bedrock 클라이언트 생성 또는 API 호출 실패 시.
        Exception: 기타 예외 발생 시.
    """
    # 1. 모델 설정 가져오기
    if model_key not in MODELS:
        valid_keys = ", ".join(MODELS.keys())
        raise ValueError(f"Invalid model_key: '{model_key}'. Valid keys are: {valid_keys}")
    model_config = MODELS[model_key]
    logger.info(f"Invoking model: '{model_key}' ({model_config.get('provider')}) with prompt: '{prompt[:50]}...'")

    # 2. Bedrock 클라이언트 가져오기
    bedrock_client = get_bedrock_client()

    # 3. 요청 본문 생성
    builder_func_name = model_config.get("request_body_builder")
    if not builder_func_name or not hasattr(__import__(__name__), builder_func_name):
        raise ValueError(f"Invalid request body builder function name '{builder_func_name}' for model '{model_key}'")
    builder_func = getattr(__import__(__name__), builder_func_name)

    # 필요한 파라미터만 선택적으로 전달
    builder_args = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k
    }
    # None 값 제거 및 kwargs 추가
    final_builder_args = {k: v for k, v in builder_args.items() if v is not None}
    final_builder_args.update(kwargs)

    try:
        request_body = builder_func(**final_builder_args)
    except TypeError as e:
        logger.error(f"Error building request body for {model_key} with args {final_builder_args}: {e}", exc_info=True)
        raise ValueError(f"Could not build request body for {model_key}: {e}")

    # 4. 모델 호출 (Inference Profile ARN 또는 Model ID 사용)
    identifier = model_config.get("inference_profile_arn") or model_config.get("model_id")
    if not identifier:
         raise ValueError(f"No inference_profile_arn or model_id found for model '{model_key}'")

    logger.debug(f"Invoking model identifier: {identifier}")
    logger.debug(f"Request body: {json.dumps(request_body, indent=2)}")

    try:
        response = bedrock_client.invoke_model(
            modelId=identifier,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        logger.info(f"Successfully invoked model '{model_key}'.")

        # 5. 응답 처리
        response_body_raw = response['body'].read()
        response_body_decoded = json.loads(response_body_raw)
        logger.debug(f"Raw response body: {response_body_decoded}")
        return response_body_decoded

    except bedrock_client.exceptions.AccessDeniedException as e:
        logger.error(f"Access denied for model '{identifier}'. Check IAM permissions and model access in Bedrock console.", exc_info=True)
        raise ConnectionError(f"Access denied for model '{identifier}': {e}")
    except bedrock_client.exceptions.ResourceNotFoundException as e:
        logger.error(f"Model or profile '{identifier}' not found. Verify the ARN/ID and region.", exc_info=True)
        raise ConnectionError(f"Model or profile '{identifier}' not found: {e}")
    except bedrock_client.exceptions.ValidationException as e:
        logger.error(f"Validation error invoking model '{identifier}'. Check request parameters and model quotas. Detail: {e}", exc_info=True)
        # 여기에서 On-Demand 미지원 오류를 잡을 수도 있음
        if "on-demand throughput isn\'t supported" in str(e):
             logger.error("This model might require Provisioned Throughput, not On-Demand via Inference Profile.")
        raise ValueError(f"Validation error for model '{identifier}': {e}")
    except Exception as e:
        logger.error(f"Error invoking model '{model_key}' ({identifier}): {e}", exc_info=True)
        raise ConnectionError(f"Failed to invoke model '{model_key}': {e}")

# --- Convenience Function ---
def get_text_response(
    prompt: str,
    model_key: str = DEFAULT_MODEL_KEY,
    **kwargs # invoke_model의 모든 파라미터 전달 가능
) -> str:
    """
    모델을 호출하고 응답에서 추출된 텍스트만 반환하는 편의 함수입니다.

    Args:
        prompt (str): 모델에 전달할 프롬프트.
        model_key (str): 사용할 모델의 키.
        **kwargs: max_tokens, temperature 등 invoke_model에 전달될 파라미터.

    Returns:
        str: 모델이 생성한 텍스트 응답.

    Raises:
        ValueError, ConnectionError, Exception: invoke_model에서 발생한 예외.
    """
    try:
        response_body = invoke_model(prompt=prompt, model_key=model_key, **kwargs)

        # 응답 파서 가져오기
        model_config = MODELS[model_key]
        parser_func_name = model_config.get("response_parser")
        if not parser_func_name or not hasattr(__import__(__name__), parser_func_name):
             logger.error(f"Invalid response parser function name '{parser_func_name}' for model '{model_key}'")
             return "[Parsing Error]"
        parser_func = getattr(__import__(__name__), parser_func_name)

        return parser_func(response_body)

    except (ValueError, ConnectionError) as e:
        # 이미 로깅된 오류이므로 여기서는 간단히 재발생
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting text response for model '{model_key}': {e}", exc_info=True)
        raise # 예상치 못한 오류는 상위 호출자에게 전파


# --- Example Usage (Optional) ---
if __name__ == "__main__":
    # 스크립트로 직접 실행 시 테스트 호출
    test_prompt = "안녕. 너는 누구야? 간단히 자기소개 해줘."
    print(f"--- Testing {DEFAULT_MODEL_KEY} --- ")
    try:
        text_result = get_text_response(test_prompt, model_key=DEFAULT_MODEL_KEY)
        print("Response:")
        print(text_result)
    except Exception as e:
        print(f"Error: {e}")

    # 다른 모델 테스트 (설정에 있는 경우)
    if "llama_3_3_70b" in MODELS:
        print("\n--- Testing llama_3_3_70b --- ")
        try:
            text_result_llama = get_text_response(test_prompt, model_key="llama_3_3_70b")
            print("Response:")
            print(text_result_llama)
        except Exception as e:
            print(f"Error: {e}") 