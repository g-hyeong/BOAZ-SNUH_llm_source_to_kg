"""
테스트용 로깅 설정 모듈
"""
import os
import sys
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
TEST_ROOT = Path(__file__).parent

def setup_test_logging(test_name: str = "test") -> str:
    """
    테스트용 로깅 설정 함수
    로그를 test/outputs/logs 디렉토리에 저장합니다
    
    Args:
        test_name: 테스트 이름 (로그 파일명에 사용)
        
    Returns:
        생성된 로그 파일 경로
    """
    # 로그 디렉토리 설정
    log_dir = os.path.join(TEST_ROOT, "outputs", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 현재 시간을 포함한 로그 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{test_name}_{timestamp}.log")
    
    # 로거 생성 및 설정
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 파일 핸들러 추가
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(file_handler)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(console_handler)
    
    return log_file

def get_test_logger(name: Optional[str] = None) -> logging.Logger:
    """
    테스트에서 사용할 로거 인스턴스를 반환합니다
    
    Args:
        name: 로거 이름 (None인 경우 루트 로거 반환)
        
    Returns:
        설정된 로거 인스턴스
    """
    if name:
        return logging.getLogger(name)
    return logging.getLogger() 