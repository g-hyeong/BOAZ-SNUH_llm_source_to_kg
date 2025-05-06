import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any

# 패키지 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 설정 모듈 임포트
from src.config import settings
# load_source 모듈에서 get_target_sources 함수와 SELECTED_TARGET_SOURCES 임포트
from extraction.manager.load_source import get_target_sources, SELECTED_TARGET_SOURCES
# LangGraph 워크플로우 임포트
from graph.workflow import process_source
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
        
        # 모델명이 지정되지 않았을 때 settings에서 기본값 사용
        logger.info(f"기본 모델 키: {settings.default_llm_model}")
        logger.info(f"사용 가능한 모델 키: {list(settings.gemini_models.keys())}")
        model_name = settings.gemini_models.get("2.0-flash")
        logger.info(f"선택된 모델명: {model_name}")
        
        if not model_name:
            raise ValueError("모델명이 지정되지 않았습니다.")
            
        # LLM 설정
        llm_config = {
            "model": model_name,
            "temperature": 0.1,
            "max_tokens": 8192
        }
        
        logger.info(f"LLM 설정: {llm_config}")
        
        # LangGraph 워크플로우로 각 소스 파일 처리
        results = []
        
        for source_path in target_sources:
            logger.info(f"소스 파일 처리 시작: {source_path}")
            
            # LangGraph 워크플로우 실행
            result = process_source(
                source_path=str(source_path),
                llm_config=llm_config
            )
            
            if result["success"]:
                logger.info(f"소스 파일 처리 완료: {source_path}")
            else:
                logger.error(f"소스 파일 처리 실패: {source_path} - {result['error']}")
            
            results.append(result)
        
        # 전체 결과 요약
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        logger.info(f"모든 처리 완료: 성공={successful}, 실패={failed}")
        
        # 결과 파일 경로 출력
        result_files = list(settings.result_dir.glob("*.json"))
        if result_files:
            logger.info(f"결과 파일이 다음 위치에 저장되었습니다: {settings.result_dir}")
            for file in result_files[-len(results):]:  # 가장 최근 파일들만 표시
                logger.info(f" - {file.name}")

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
