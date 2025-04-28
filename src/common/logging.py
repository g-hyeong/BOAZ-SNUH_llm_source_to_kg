"""
프로젝트 로깅 설정을 관리하고 로거 인스턴스를 제공합니다.
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional, Any, Union, Literal

from config import settings

# 로그 디렉토리 설정 - config에서 가져옴
LOG_DIR = settings.log_dir
# 실행 시간별 로그 디렉토리 생성 (MMDD_HHMM 형식)
CURRENT_TIME = datetime.now().strftime("%m%d_%H%M")
CURRENT_LOG_DIR = os.path.join(LOG_DIR, CURRENT_TIME)

# 로그 파일명 정의
LOG_FILES = {
    "main": "main.log",
    "llm_prompt": "llm_prompt.log",
    "llm_response": "llm_response.log"
}

# 로거 인스턴스 캐싱용 딕셔너리
_loggers: Dict[str, logging.Logger] = {}

def setup_logging(level: int = None) -> None:
    """
    로깅 시스템 초기화

    Args:
        level: 로깅 레벨
    """
    # 설정 파일에서 로그 레벨 가져오기
    if level is None:
        level_name = settings.log_level
        level = getattr(logging, level_name)
    
    # 로그 디렉토리 생성
    os.makedirs(CURRENT_LOG_DIR, exist_ok=True)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    root_logger.addHandler(console_handler)
    
    # 3가지 로거 초기화
    _create_logger("main", level)
    _create_logger("llm_prompt", level)
    _create_logger("llm_response", level)

def _create_logger(logger_name: str, level: int) -> logging.Logger:
    """
    특정 로거 생성 및 설정

    Args:
        logger_name: 로거 이름
        level: 로깅 레벨

    Returns:
        설정된 로거 인스턴스
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False  # 부모 로거로 전파하지 않음
    
    # 파일 핸들러 설정
    log_file_path = os.path.join(CURRENT_LOG_DIR, LOG_FILES[logger_name])
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(file_handler)
    
    # main 로거에만 콘솔 핸들러 추가 (터미널 출력)
    if logger_name == "main":
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            "%(levelname)s - %(message)s"  # 터미널에는 간소화된 형식 사용
        ))
        logger.addHandler(console_handler)
    
    # 캐시에 저장
    _loggers[logger_name] = logger
    
    return logger

def get_logger(name: str = "main") -> logging.Logger:
    """
    기본 로거 인스턴스 반환
    
    Args:
        name: 로거 이름 또는 모듈 이름

    Returns:
        로거 인스턴스
    """
    if name != "main" and name not in _loggers:
        # 모듈별 로거 생성 (main 로거 파일에 기록)
        module_logger = logging.getLogger(name)
        # 모듈 로거는 기본적으로 루트 로거를 따름
        return module_logger
    
    return _loggers.get(name, logging.getLogger())

def get_prompt_logger() -> logging.Logger:
    """
    LLM 프롬프트 로깅용 로거 반환
    
    Returns:
        llm_prompt 로거
    """
    return _loggers.get("llm_prompt", logging.getLogger("llm_prompt"))

def get_response_logger() -> logging.Logger:
    """
    LLM 응답 로깅용 로거 반환
    
    Returns:
        llm_response 로거
    """
    return _loggers.get("llm_response", logging.getLogger("llm_response"))

def log_llm_prompt(model_name: str, system_prompt: str, human_prompt: str, **kwargs) -> None:
    """
    LLM 프롬프트 로깅 유틸리티 함수
    
    Args:
        model_name: 사용된 LLM 모델 이름
        system_prompt: 시스템 프롬프트
        human_prompt: 사용자 프롬프트
        **kwargs: 추가 로깅 정보
    """
    prompt_logger = get_prompt_logger()
    
    # 기본 로그 메시지 구성
    log_msg = f"[모델: {model_name}] 프롬프트 전송\n"
    log_msg += f"=== 시스템 프롬프트 ===\n{system_prompt}\n"
    log_msg += f"=== 사용자 프롬프트 ===\n{human_prompt}\n"
    
    # 추가 로깅 정보가 있으면 추가
    if kwargs:
        log_msg += "=== 추가 정보 ===\n"
        for key, value in kwargs.items():
            log_msg += f"{key}: {value}\n"
    
    prompt_logger.info(log_msg)

def log_llm_response(model_name: str, response_text: str, **kwargs) -> None:
    """
    LLM 응답 로깅 유틸리티 함수
    
    Args:
        model_name: 사용된 LLM 모델 이름
        response_text: LLM 응답 텍스트
        **kwargs: 추가 로깅 정보
    """
    response_logger = get_response_logger()
    
    # 기본 로그 메시지 구성
    log_msg = f"[모델: {model_name}] 응답 수신\n"
    log_msg += f"=== 응답 내용 ===\n{response_text}\n"
    
    # 추가 로깅 정보가 있으면 추가
    if kwargs:
        log_msg += "=== 추가 정보 ===\n"
        for key, value in kwargs.items():
            log_msg += f"{key}: {value}\n"
    
    response_logger.info(log_msg)

# 유틸리티 함수들 - 로깅 레벨별로 바로 사용할 수 있는 도우미 함수
def log_debug(message: str, **kwargs: Any) -> None:
    """DEBUG 레벨 로깅 도우미 함수"""
    log_main(message, level="DEBUG", **kwargs)

def log_info(message: str, **kwargs: Any) -> None:
    """INFO 레벨 로깅 도우미 함수"""
    log_main(message, level="INFO", **kwargs)

def log_warning(message: str, **kwargs: Any) -> None:
    """WARNING 레벨 로깅 도우미 함수"""
    log_main(message, level="WARNING", **kwargs)

def log_error(message: str, **kwargs: Any) -> None:
    """ERROR 레벨 로깅 도우미 함수"""
    log_main(message, level="ERROR", **kwargs)

def log_critical(message: str, **kwargs: Any) -> None:
    """CRITICAL 레벨 로깅 도우미 함수"""
    log_main(message, level="CRITICAL", **kwargs)

# 초기 로깅 설정 실행
setup_logging() 