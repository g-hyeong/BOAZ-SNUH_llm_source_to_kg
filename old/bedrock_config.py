# AWS Bedrock 설정 파일

import os

# --- AWS Configuration ---
# 환경 변수 또는 기본값 사용
AWS_PROFILE = os.environ.get("AWS_PROFILE", "boaz-snuh")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# --- Bedrock API Configuration ---
BEDROCK_RUNTIME_ENDPOINT = f"https://bedrock-runtime.{AWS_REGION}.amazonaws.com"
REQUEST_TIMEOUT = 60  # 타임아웃 증가 (초)

# --- Model Configuration ---
# 각 모델에 대한 상세 설정 정의
MODELS = {
    "claude_3_7_sonnet": {
        "model_id": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "inference_profile_arn": "arn:aws:bedrock:us-east-1:343218216679:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "provider": "anthropic",
        "request_body_builder": "build_claude_request_body",
        "response_parser": "parse_claude_response"
    },
    "llama_3_3_70b": {
        "model_id": "meta.llama3-3-70b-instruct-v1:0",
        "inference_profile_arn": "arn:aws:bedrock:us-east-1:343218216679:inference-profile/us.meta.llama3-3-70b-instruct-v1:0",
        "provider": "meta",
        "request_body_builder": "build_llama_request_body",
        "response_parser": "parse_llama_response"
    }
}

# --- Default Model Keys ---
# 애플리케이션에서 사용할 기본 모델 지정
DEFAULT_MODEL_KEY = "claude_3_7_sonnet" 