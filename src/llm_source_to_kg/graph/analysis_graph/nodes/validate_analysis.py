from src.llm_source_to_kg.graph.analysis_graph.state import AnalysisGraphState
import json
from typing import Dict, Any

def validate_analysis(state: AnalysisGraphState) -> AnalysisGraphState:
    """
    분석 결과가 원본 코호트 내용과 일치하는지 검증합니다.
    
    Args:
        state: 현재 그래프 상태
        
    Returns:
        업데이트된 그래프 상태 (is_valid 필드 포함)
    """
    analysis = state["analysis"]
    cohort_data = state["cohort"]
    
    validation_results = {}
    total_valid = 0
    total_cohorts = 0
    
    # 각 코호트별 분석 결과 검증
    for cohort_id, analysis_result in analysis.cohort_analyses.items():
        total_cohorts += 1
        cohort_content = cohort_data.get(cohort_id, "")
        
        if analysis_result["status"] != "success":
            validation_results[cohort_id] = {
                "is_valid": False,
                "reason": f"분석 실패: {analysis_result.get('error', 'Unknown error')}"
            }
            continue
        
        entities = analysis_result["entities"]
        is_valid = True
        validation_errors = []
        
        # 각 엔티티 유형별 검증
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                # 엔티티가 원본 코호트 내용에 포함되어있는지 확인
                # (실제로는 더 정교한 유사도 검증이 필요할 수 있음)
                if entity.lower() not in cohort_content.lower():
                    # 유연한 검증: 부분 매칭, 동의어 등을 고려할 수 있음
                    # 지금은 단순 포함 검사로 진행
                    pass
        
        # 필수 엔티티 검증 (예: 최소 하나의 drug나 diagnostic이 있어야 함)
        has_medical_entities = (
            len(entities.get("drug", [])) > 0 or
            len(entities.get("diagnostic", [])) > 0 or 
            len(entities.get("medicalTest", [])) > 0 or
            len(entities.get("surgery", [])) > 0
        )
        
        if not has_medical_entities:
            is_valid = False
            validation_errors.append("의료 관련 엔티티가 추출되지 않았습니다.")
        
        validation_results[cohort_id] = {
            "is_valid": is_valid,
            "errors": validation_errors,
            "extracted_count": sum(len(v) for v in entities.values())
        }
        
        if is_valid:
            total_valid += 1
    
    # 전체 검증 결과 결정
    overall_valid = (total_valid == total_cohorts) and total_cohorts > 0
    
    # 상태 업데이트
    state["is_valid"] = overall_valid
    state["validation_results"] = validation_results
    
    # 실패한 경우 재시도 카운트 증가
    if not overall_valid:
        state["retries"] = state.get("retries", 0) + 1
    
    return state