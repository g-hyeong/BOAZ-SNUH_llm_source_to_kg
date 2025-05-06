"""
공통 유틸리티 함수 모듈입니다.
"""

import logging
import os
import json
from typing import Any, Dict
from datetime import datetime
from pathlib import Path

def get_logger(name: str) -> logging.Logger:
    """
    지정된 이름으로 로거를 생성하고 반환합니다.
    
    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)
        
    Returns:
        설정된 로거 객체
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 추가되어 있으면 재설정하지 않음
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # 로그 파일 저장 디렉토리 설정 (logs 폴더)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 파일명에 날짜 포함
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{today}.log"
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def save_json(data: Dict[str, Any], filepath: str) -> None:
    """
    데이터를 JSON 파일로 저장합니다.
    
    Args:
        data: 저장할 데이터 딕셔너리
        filepath: 저장할 파일 경로
    """
    # 디렉토리 확인 및 생성
    dir_path = os.path.dirname(filepath)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path)
    
    # JSON 형식으로 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(filepath: str) -> Dict[str, Any]:
    """
    JSON 파일에서 데이터를 로드합니다.
    
    Args:
        filepath: 로드할 파일 경로
        
    Returns:
        로드된 데이터 딕셔너리
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"파일이 존재하지 않습니다: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    텍스트를 지정된 길이로 잘라서 반환합니다.
    
    Args:
        text: 잘라낼 텍스트
        max_length: 최대 길이
        
    Returns:
        잘라낸 텍스트
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..." 