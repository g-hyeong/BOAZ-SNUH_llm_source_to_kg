import sys
import os
import json
from pathlib import Path
from typing import List

# 설정 모듈 임포트 (src/config.py로 변경)
from config import settings
# load_source 모듈에서 get_target_sources 함수와 SELECTED_TARGET_SOURCES 임포트
from extraction.manager.load_source import get_target_sources, SELECTED_TARGET_SOURCES
from extraction.manager.node import ManagerNode
# 로거 가져오기
from common.logging import get_logger

# 'main' 로거 인스턴스 가져오기 - 모듈 이름(__name__) 대신 'main' 문자열을 사용
logger = get_logger("main")

# 선택된 타겟 소스 파일들 (python main.py select 옵션용)
SELECTED_TARGET_SOURCES = [
    "NG238.json",
    "NG240.json"
]

def main():
    """
    메인 실행 함수
    """
    # 명령행 인자 확인
    if len(sys.argv) < 2:
        logger.error("사용법: python main.py <command>")
        logger.error("  command: all, select, 또는 파일명")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        # 타겟 소스 파일 목록 가져오기
        target_sources = get_target_sources(command, SELECTED_TARGET_SOURCES)
        
        if not target_sources:
            logger.warning("처리할 소스 파일이 없습니다.")
            sys.exit(1)
        
        # 처리할 파일 목록 출력
        logger.info(f"처리할 파일 목록 ({len(target_sources)}개):")
        logger.info(f"{target_sources}")
        
        # 여기에 실제 파일 처리 코드 구현
        # ...

        # 모델명이 지정되지 않았을 때 settings에서 기본값 사용
        logger.info(f"기본 모델 키: {settings.default_llm_model}")
        logger.info(f"사용 가능한 모델 키: {list(settings.gemini_models.keys())}")
        model_name = settings.gemini_models.get("2.0-flash")
        logger.info(f"선택된 모델명: {model_name}")
        
        if not model_name:
            raise ValueError("모델명이 지정되지 않았습니다.")
            
        llm_config = {
            "model": model_name,
            "temperature": 0.1,
            "max_tokens": 8192
        }
        
        logger.info(f"LLM 설정: {llm_config}")
        
        try:
            manager = ManagerNode(
                llm_type="gemini",
                llm_config=llm_config,
                command=command,
                targets=target_sources
            )
            logger.info("ManagerNode 초기화 성공")
            
            results = []
            for result in manager.run():
                results.append(result)
        
            # 결과 저장
            results_dir = settings.result_dir
            os.makedirs(results_dir, exist_ok=True)
        
        except Exception as e:
            logger.error(f"ManagerNode 실행 중 오류가 발생했습니다: {e}")
            sys.exit(1)

    except FileNotFoundError as e:
        logger.error(f"오류: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"오류: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
