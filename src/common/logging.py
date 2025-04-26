"""
프로젝트 로깅 설정을 관리하고 로거 인스턴스를 제공합니다.
"""

import logging
import sys

def setup_logging(level: int = logging.INFO) -> None:
    """
    루트 로거를 설정합니다.

    Args:
        level: 로깅 레벨 (예: logging.INFO, logging.DEBUG)
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,  # 또는 파일 핸들러 등 설정 가능
    )

def get_logger(name: str) -> logging.Logger:
    """
    지정된 이름의 로거 인스턴스를 가져옵니다.

    Args:
        name: 로거 이름 (일반적으로 모듈 이름 `__name__` 사용)

    Returns:
        설정된 로거 인스턴스
    """
    return logging.getLogger(name)

# 초기 로깅 설정 실행
setup_logging() 