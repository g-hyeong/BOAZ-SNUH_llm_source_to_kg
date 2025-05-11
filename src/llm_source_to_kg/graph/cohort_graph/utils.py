"""
코호트 그래프에서 사용되는 유틸리티 함수
"""
from typing import Literal
from graph.cohort_graph.state import CohortGraphState

# 최대 재시도 횟수
RETRY_COUNT = 3


def route_after_validation(state: CohortGraphState) -> Literal["retry_extract_cohort", "return_final_cohorts"]:
    """
    검증 결과에 따라 다음 노드를 결정하는 라우팅 함수
    
    Args:
        state: 현재 그래프 상태
        
    Returns:
        다음에 실행할 노드 이름
    """
    # 검증 실패한 코호트가 있는지 확인
    invalid_cohorts_exist = any(not cohort.get("is_valid", False) for cohort in state["cohort_result"])
    
    # 재시도가 필요한 코호트 중 최대 재시도 횟수를 초과하지 않은 코호트가 있는지 확인
    retry_needed = any(
        not cohort.get("is_valid", False) and cohort.get("retries", 0) < RETRY_COUNT
        for cohort in state["cohort_result"]
    )
    
    if invalid_cohorts_exist and retry_needed:
        return "retry_extract_cohort"
    else:
        return "return_final_cohorts" 