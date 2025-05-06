"""
진단 관련 정보를 추출하는 LLM 에이전트 모듈입니다.
"""

import os
import json
from typing import Dict, Any
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.common.utils import get_logger

logger = get_logger(__name__)

def extract_diagnostic_entities(document_content: str) -> Dict[str, Any]:
    """
    문서 내용에서 진단 관련 정보를 추출합니다.
    
    Args:
        document_content: 분석할 문서 내용
    
    Returns:
        추출된 진단 정보
    """
    logger.info("진단 에이전트 호출 시작")
    
    try:
        # LLM 모델 설정
        model = ChatOpenAI(
            model="gpt-4",
            temperature=0.1
        )
        
        # 프롬프트 파일 로드
        prompt_path = Path(__file__).parent / "prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
        
        # System 프롬프트 구성
        system_prompt = """
        당신은 의료 문서에서 진단 관련 정보를 추출하는 전문가입니다.
        OMOP CDM 개념과 의학 지식을 바탕으로 문서에서 질병, 증상, 조건 등을 식별하고 
        구조화된 JSON 형식으로 반환해야 합니다.
        """
        
        # 인간 프롬프트 구성 (Jinja2 대신 직접 변수 삽입)
        manager_response = "문서를 분석하여 진단 관련 엔티티를 추출하고 구조화해주세요."
        human_prompt = prompt_template.replace("{{ manager_response }}", manager_response)
        
        # 메시지 구성
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{human_prompt}\n\n문서 내용:\n{document_content}")
        ]
        
        # LLM 호출
        response = model.invoke(messages)
        
        # 응답에서 JSON 추출
        json_text = extract_json_from_response(response.content)
        result = json.loads(json_text)
        
        logger.info("진단 에이전트 응답 파싱 완료")
        
        return result
    except Exception as e:
        logger.error(f"진단 에이전트 호출 중 오류 발생: {str(e)}")
        # 예시 데이터로 기본 반환
        return {
            "condition_entities": [],
            "condition_relationships": [],
            "diagnostic_pathways": [],
            "condition_cohorts": [],
            "detailed_analysis": f"오류 발생: {str(e)}"
        }

def extract_json_from_response(response_text: str) -> str:
    """
    응답 텍스트에서 JSON 부분만 추출합니다.
    
    Args:
        response_text: LLM 응답 텍스트
    
    Returns:
        JSON 문자열
    """
    # JSON 코드 블록 추출
    import re
    json_match = re.search(r'```(?:json)?(.*?)```', response_text, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1).strip()
        return json_str
    
    # JSON 블록이 없는 경우 전체 텍스트에서 JSON 객체 추출 시도
    try:
        # 중괄호 내 내용 추출
        json_match = re.search(r'({.*})', response_text.replace('\n', ' '), re.DOTALL)
        if json_match:
            return json_match.group(1)
    except:
        pass
    
    # 추출 실패 시 원본 반환
    return response_text 