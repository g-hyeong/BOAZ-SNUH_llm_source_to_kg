from dotenv import load_dotenv
import os


load_dotenv()

class Config:
    """설정 클래스 - 속성 접근 방식 사용"""
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")


# 전역 설정 인스턴스 생성
config = Config()

# 다음과 같이 사용 가능:
# from llm_source_to_kg.config import config
# value = config.GEMINI_API_KEY  # 속성 접근 방식
