"""
프로젝트 전반에서 사용될 상수 값들을 정의합니다.

예: API 키 이름, 기본 모델 설정, 파일 경로 등
"""

# --- API Keys & Configuration ---
AWS_REGION_NAME = "us-east-1"  # 예시: AWS 리전
BEDROCK_DEFAULT_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"  # 예시: 기본 Bedrock 모델 ID
GEMINI_API_KEY_ENV_VAR = "GOOGLE_API_KEY"  # 예시: Gemini API 키 환경 변수 이름

# --- File Paths ---
# DATA_DIR = "data/" # 예시: 데이터 디렉토리
# OUTPUT_DIR = "outputs/" # 예시: 결과물 디렉토리
# CONFIG_FILE_PATH = "config/config.yaml" # 예시: 설정 파일 경로

# --- KG Related ---
# NEO4J_URI = "neo4j://localhost:7687" # 예시: Neo4j URI
# NEO4J_USERNAME = "neo4j" # 예시: Neo4j 사용자 이름
# NEO4J_PASSWORD = "password" # 예시: Neo4j 비밀번호

# --- Prompt Templates ---
# DIAGNOSTIC_EXTRACTION_PROMPT_NAME = "diagnostic_extraction.prompt"
# DRUG_EXTRACTION_PROMPT_NAME = "drug_extraction.prompt"

# --- Other Constants ---
DEFAULT_BATCH_SIZE = 10 