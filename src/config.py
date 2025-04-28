import os
from pathlib import Path
from typing import Optional, List, Dict

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    애플리케이션 설정
    """
    # LLM 관련 설정
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    
    default_llm_model: str = "1.5-flash"
    
    gemini_models: Dict[str, str] = {
        "pro": "gemini-pro",
        "1.0-pro": "gemini-1.0-pro",
        "1.5-flash": "gemini-1.5-flash",
        "1.5-pro": "gemini-1.5-pro",
        "1.5-pro-latest": "gemini-1.5-pro-latest",
        "2.0-flash": "gemini-2.0-flash",
        "2.5-pro": "gemini-2.5-pro-exp-03-25"
    }
    
    # 디렉토리 경로 설정
    project_root: Path = Path(__file__).parent.parent

    data_dir: Path = project_root / "datasets"
    guideline_dir: Path = data_dir / "guideline" / "contents"
    omop_dir: Path = data_dir / "omop"

    output_dir: Path = project_root / "outputs"
    result_dir: Path = output_dir / "results"
    log_dir: Path = output_dir / "logs"
    
    # 로깅 설정
    log_level: str = "INFO"
    
    class Config:
        """Pydantic 설정 클래스"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 전역 설정 인스턴스 생성
# 다른 모듈에서 import하여 사용 가능
settings = Settings()


def get_settings() -> Settings:
    """
    설정 객체를 반환
    
    Returns:
        Settings 인스턴스
    """
    return settings


if __name__ == "__main__":
    # 설정 확인용 코드
    print(f"Project Root: {settings.project_root}")
    print(f"Data Directory: {settings.data_dir}")
    print(f"Log Directory: {settings.log_dir}")
    print(f"Default LLM Model: {settings.default_llm_model}")
    print(f"사용 가능한 Gemini 모델: {list(settings.gemini_models.keys())}") 