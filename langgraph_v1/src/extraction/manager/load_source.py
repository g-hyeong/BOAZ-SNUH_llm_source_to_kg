"""
가이드라인 소스 파일을 로드하는 유틸리티 함수들을 제공합니다.
"""

from pathlib import Path
from typing import List
from config import settings
from common.logging import get_logger

logger = get_logger("main")

# 선택된 타겟 소스 파일들 (python main.py select 옵션용)
SELECTED_TARGET_SOURCES = [
    "NG238.json",
    "NG240.json"
]

def get_target_sources(command: str, targets: List[str] = None) -> List[Path]:
    """
    명령어에 따라 처리할 타겟 소스 파일들의 경로 목록을 반환
    
    Args:
        command: 명령행 인자로 받은 명령어 (all, select, 파일명)
        targets: 선택된 타겟 파일 목록 (command가 "select"인 경우)
        
    Returns:
        처리할 소스 파일들의 경로 리스트
    
    Raises:
        FileNotFoundError: 지정된 파일이 존재하지 않을 경우
        ValueError: 적절하지 않은 명령어가 입력된 경우
    """
    guideline_dir = settings.guideline_dir
    
    if command == "all":
        # guideline_dir의 모든 json 파일 반환
        return list(guideline_dir.glob("*.json"))
    
    elif command == "select":
        # targets에 명시된 파일들만 반환
        result = []
        for filename in targets or SELECTED_TARGET_SOURCES:
            file_path = guideline_dir / filename
            if file_path.exists():
                result.append(file_path)
            else:
                logger.warning(f"선택된 소스 파일 '{filename}'이 존재하지 않습니다.")
        return result
    
    else:
        # 특정 파일명이 입력된 경우 (확장자 처리)
        filename = command if command.endswith(".json") else f"{command}.json"
        file_path = guideline_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
        return [file_path] 