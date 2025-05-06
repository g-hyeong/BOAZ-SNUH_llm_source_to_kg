"""
추출 프로세스를 조정하는 모듈입니다.

문서 내용과 청크를 분석하여 적절한 추출 유형을 결정하고,
진단 및 약물 정보 추출을 관리합니다.
"""

import json
from typing import List, Dict, Any, Optional
import re

# 진단 및 약물 에이전트 모듈 임포트
from src.extraction.diagnostic.agent import extract_diagnostic_entities
from src.extraction.drug.agent import extract_drug_entities
from src.graph.state import DiagnosticResults, DrugResults
from src.common.utils import get_logger

logger = get_logger(__name__)

def determine_analysis_type(document_content: str, document_chunks: List[str]) -> str:
    """
    문서 내용을 분석하여 적절한 분석 유형을 결정합니다.
    
    Args:
        document_content: 전체 문서 내용
        document_chunks: 분할된 문서 청크 목록
        
    Returns:
        분석 유형 문자열 ("diagnostic", "drug", "both")
    """
    # 간단한 키워드 기반 결정 로직
    diagnostic_keywords = [
        "진단", "질병", "질환", "증상", "syndrome", "disease", "disorder", "diagnosis", 
        "condition", "symptom", "clinical finding"
    ]
    
    drug_keywords = [
        "약물", "의약품", "처방", "투약", "medication", "drug", "pharmaceutical", 
        "prescription", "dosage", "medicine", "therapy", "treatment"
    ]
    
    # 간단한 점수 계산
    diagnostic_score = 0
    drug_score = 0
    
    for chunk in document_chunks:
        for keyword in diagnostic_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', chunk, re.IGNORECASE):
                diagnostic_score += 1
        
        for keyword in drug_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', chunk, re.IGNORECASE):
                drug_score += 1
    
    logger.info(f"분석 유형 결정: diagnostic_score={diagnostic_score}, drug_score={drug_score}")
    
    # 점수에 따른 결정
    if diagnostic_score > 0 and drug_score > 0:
        if diagnostic_score >= drug_score * 2:
            return "diagnostic"
        elif drug_score >= diagnostic_score * 2:
            return "drug"
        else:
            return "both"
    elif diagnostic_score > 0:
        return "diagnostic"
    elif drug_score > 0:
        return "drug"
    else:
        # 기본값
        return "both"

def extract_diagnostic_info(document_content: str, document_chunks: List[str]) -> DiagnosticResults:
    """
    문서에서 진단 관련 정보를 추출합니다.
    
    Args:
        document_content: 전체 문서 내용
        document_chunks: 분할된 문서 청크 목록
        
    Returns:
        진단 결과 객체
    """
    try:
        logger.info("진단 정보 추출 시작")
        
        # LLM 에이전트를 호출하여 진단 정보 추출
        diagnostic_json = extract_diagnostic_entities(document_content)
        
        # JSON 응답을 파싱하여 DiagnosticResults 객체 생성
        diagnostic_results = DiagnosticResults.model_validate(diagnostic_json)
        
        logger.info(f"진단 정보 추출 완료: {len(diagnostic_results.condition_entities)} 엔티티 발견")
        
        return diagnostic_results
    except Exception as e:
        logger.error(f"진단 정보 추출 중 오류 발생: {str(e)}")
        # 예외 처리 및 기본 결과 반환
        raise

def extract_drug_info(document_content: str, document_chunks: List[str]) -> DrugResults:
    """
    문서에서 약물 관련 정보를 추출합니다.
    
    Args:
        document_content: 전체 문서 내용
        document_chunks: 분할된 문서 청크 목록
        
    Returns:
        약물 결과 객체
    """
    try:
        logger.info("약물 정보 추출 시작")
        
        # LLM 에이전트를 호출하여 약물 정보 추출
        drug_json = extract_drug_entities(document_content)
        
        # JSON 응답을 파싱하여 DrugResults 객체 생성
        drug_results = DrugResults.model_validate(drug_json)
        
        logger.info(f"약물 정보 추출 완료: {len(drug_results.drug_entities)} 엔티티 발견")
        
        return drug_results
    except Exception as e:
        logger.error(f"약물 정보 추출 중 오류 발생: {str(e)}")
        # 예외 처리 및 기본 결과 반환
        raise 