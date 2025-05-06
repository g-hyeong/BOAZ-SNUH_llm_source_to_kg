"""
추출된 결과의 검증을 위한 모듈입니다.

코호트 관련 검증 및 OMOP 존재 여부 검증을 수행합니다.
"""

import json
from typing import Dict, Any, List
import re
import os

from src.graph.state import ValidationResult
from src.common.utils import get_logger

logger = get_logger(__name__)

def verify_cohort(aggregated_results: Dict[str, Any]) -> ValidationResult:
    """
    추출된 코호트 정보의 유효성을 검증합니다.
    
    Args:
        aggregated_results: 통합된 추출 결과
        
    Returns:
        코호트 검증 결과 객체
    """
    logger.info("코호트 검증 시작")
    
    try:
        # 코호트 데이터 추출
        cohort_data = extract_cohort_data(aggregated_results)
        
        if not cohort_data:
            return ValidationResult(
                status="failed",
                details={"reason": "코호트 정보가 없습니다."},
                questions=[]
            )
        
        # 코호트 검증을 위한 질문 생성
        questions = generate_validation_questions(cohort_data)
        
        # 검증 상태 및 결과 생성
        validation_status = "passed" if questions else "needs_review"
        
        result = ValidationResult(
            status=validation_status,
            details={
                "cohort_data": cohort_data,
                "validation_method": "question_generation"
            },
            questions=questions
        )
        
        logger.info(f"코호트 검증 완료: 상태={validation_status}, 질문 수={len(questions)}")
        
        return result
    except Exception as e:
        logger.error(f"코호트 검증 중 오류 발생: {str(e)}")
        return ValidationResult(
            status="failed",
            details={"error": str(e)},
            questions=[]
        )

def extract_cohort_data(aggregated_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    통합 결과에서 코호트 관련 데이터를 추출합니다.
    
    Args:
        aggregated_results: 통합된 추출 결과
        
    Returns:
        코호트 관련 데이터
    """
    cohort_data = {}
    
    # 진단 정보에서 코호트 데이터 추출
    if "diagnostic" in aggregated_results:
        diagnostic_data = aggregated_results["diagnostic"]
        if "condition_cohorts" in diagnostic_data:
            cohort_data["condition_cohorts"] = diagnostic_data["condition_cohorts"]
    
    # 약물 정보에서 코호트 데이터 추출
    if "drug" in aggregated_results:
        drug_data = aggregated_results["drug"]
        if "medication_cohorts" in drug_data:
            cohort_data["medication_cohorts"] = drug_data["medication_cohorts"]
    
    return cohort_data

def generate_validation_questions(cohort_data: Dict[str, Any]) -> List[str]:
    """
    코호트 데이터에 대한 검증 질문을 생성합니다.
    
    Args:
        cohort_data: 코호트 관련 데이터
        
    Returns:
        검증 질문 목록
    """
    questions = []
    
    # 진단 코호트에 대한 질문 생성
    if "condition_cohorts" in cohort_data:
        for cohort in cohort_data["condition_cohorts"]:
            cohort_name = cohort.get("name", "")
            if cohort_name:
                questions.append(f"{cohort_name}은(는) 유효한 코호트 정의입니까?")
            
            # 포함 기준에 대한 질문
            for criterion in cohort.get("inclusion_criteria", []):
                criterion_text = criterion.get("criterion", "")
                if criterion_text:
                    questions.append(f"{criterion_text}은(는) 유효한 포함 기준입니까?")
    
    # 약물 코호트에 대한 질문 생성
    if "medication_cohorts" in cohort_data:
        for cohort in cohort_data["medication_cohorts"]:
            cohort_name = cohort.get("name", "")
            if cohort_name:
                questions.append(f"{cohort_name}은(는) 유효한 약물 코호트 정의입니까?")
            
            # 약물 노출에 대한 질문
            for exposure in cohort.get("drug_exposures", []):
                drug_name = exposure.get("drug", "")
                if drug_name:
                    questions.append(f"{drug_name}은(는) 유효한 약물입니까?")
    
    # 최대 5개의 질문으로 제한
    return questions[:5]

def verify_omop_existence(aggregated_results: Dict[str, Any]) -> ValidationResult:
    """
    추출된 엔티티가 OMOP CDM에 존재하는지 검증합니다.
    
    Args:
        aggregated_results: 통합된 추출 결과
        
    Returns:
        OMOP 존재 여부 검증 결과 객체
    """
    logger.info("OMOP 존재 여부 검증 시작")
    
    try:
        # 모든 엔티티 추출
        entities = extract_all_entities(aggregated_results)
        
        if not entities:
            return ValidationResult(
                status="failed",
                details={"reason": "검증할 엔티티가 없습니다."},
                questions=None
            )
        
        # 간단한 검증 로직 (실제로는 OMOP 데이터베이스 조회 필요)
        # 이 예제에서는 단순화를 위해 80% 이상의 엔티티가 존재한다고 가정
        total_entities = len(entities)
        existing_entities = simulate_omop_check(entities)
        existing_ratio = len(existing_entities) / total_entities if total_entities > 0 else 0
        
        # 검증 상태 결정
        if existing_ratio >= 0.8:
            validation_status = "passed"
        elif existing_ratio >= 0.5:
            validation_status = "needs_review"
        else:
            validation_status = "failed"
        
        result = ValidationResult(
            status=validation_status,
            details={
                "total_entities": total_entities,
                "existing_entities": len(existing_entities),
                "existing_ratio": existing_ratio,
                "non_existing_entities": list(set(entities) - set(existing_entities))
            },
            questions=None
        )
        
        logger.info(f"OMOP 존재 여부 검증 완료: 상태={validation_status}, 비율={existing_ratio:.2f}")
        
        return result
    except Exception as e:
        logger.error(f"OMOP 존재 여부 검증 중 오류 발생: {str(e)}")
        return ValidationResult(
            status="failed",
            details={"error": str(e)},
            questions=None
        )

def extract_all_entities(aggregated_results: Dict[str, Any]) -> List[str]:
    """
    통합 결과에서 모든 엔티티를 추출합니다.
    
    Args:
        aggregated_results: 통합된 추출 결과
        
    Returns:
        엔티티 이름 목록
    """
    entities = []
    
    # 진단 정보에서 엔티티 추출
    if "diagnostic" in aggregated_results:
        diagnostic_data = aggregated_results["diagnostic"]
        if "condition_entities" in diagnostic_data:
            for entity in diagnostic_data["condition_entities"]:
                if "concept_name" in entity:
                    entities.append(entity["concept_name"])
    
    # 약물 정보에서 엔티티 추출
    if "drug" in aggregated_results:
        drug_data = aggregated_results["drug"]
        if "drug_entities" in drug_data:
            for entity in drug_data["drug_entities"]:
                if "concept_name" in entity:
                    entities.append(entity["concept_name"])
    
    return entities

def simulate_omop_check(entities: List[str]) -> List[str]:
    """
    OMOP CDM 개념 검사를 시뮬레이션합니다.
    실제 구현에서는 데이터베이스 쿼리로 대체해야 합니다.
    
    Args:
        entities: 검사할 엔티티 이름 목록
        
    Returns:
        OMOP CDM에 존재하는 엔티티 목록
    """
    # 실제 OMOP 검사 대신 약 85%의 엔티티가 존재한다고 가정
    import random
    random.seed(42)  # 재현 가능한 결과를 위한 시드 설정
    
    existing_entities = []
    for entity in entities:
        if random.random() < 0.85:
            existing_entities.append(entity)
    
    return existing_entities 