"""
메인 KG 생성 LangGraph 워크플로우를 정의하고 컴파일합니다.
"""

from langgraph.graph import StateGraph, END
from typing import Dict, Any, Literal

# 상태 정의 임포트
from src.graph.state import GraphState

# 노드 함수 임포트 (각 기능별 모듈에서)
from src.loading import s3_loader
from src.preprocessing import text_processor
from src.extraction.diagnostic import node_functions as diag_nodes
from src.extraction.drug import node_functions as drug_nodes
from src.extraction.manager import orchestrator
from src.graph.verify.cohort import node_functions as cohort_verify_nodes
from src.graph.verify.omop_existence import node_functions as omop_verify_nodes
from src.storage import graph_storage
# from src.common.logging import get_logger # 필요시 주석 해제

# logger = get_logger(__name__)

# --- 노드 래퍼 함수들 (필요시 상태 업데이트 및 로깅 추가) ---

def load_data_node(state: GraphState) -> GraphState:
    """데이터 로딩 노드 래퍼"""
    # 예: s3_loader.read_s3_object 호출 및 상태 업데이트
    pass

def preprocess_text_node(state: GraphState) -> GraphState:
    """텍스트 전처리 노드 래퍼"""
    # 예: text_processor.clean_text, text_processor.split_text_into_chunks 호출
    pass

def determine_extraction_type_node(state: GraphState) -> GraphState:
    """추출 유형 결정 노드 래퍼"""
    extraction_type = orchestrator.determine_extraction_type(state)
    # 상태 업데이트 로직 추가
    return state # 수정된 상태 반환 필요

def extract_diagnostic_node(state: GraphState) -> GraphState:
    """진단 정보 추출 노드 래퍼"""
    state = diag_nodes.extract_diagnostic_entities(state)
    state = diag_nodes.structure_diagnostic_info(state)
    state = diag_nodes.validate_diagnostic_extraction(state)
    return state

def extract_drug_node(state: GraphState) -> GraphState:
    """약물 정보 추출 노드 래퍼"""
    state = drug_nodes.extract_drug_entities(state)
    state = drug_nodes.structure_drug_info(state)
    state = drug_nodes.validate_drug_extraction(state)
    return state

def aggregate_results_node(state: GraphState) -> GraphState:
    """결과 통합 노드 래퍼"""
    # 예: orchestrator.aggregate_extraction_results 호출
    pass

def cohort_verification_node(state: GraphState) -> GraphState:
    """코호트 검증 노드 래퍼"""
    # 예: cohort_verify_nodes 관련 함수 호출
    pass

def omop_existence_verification_node(state: GraphState) -> GraphState:
    """OMOP 존재 검증 노드 래퍼"""
    # 예: omop_verify_nodes 관련 함수 호출
    pass

def save_results_node(state: GraphState) -> GraphState:
    """결과 저장 노드 래퍼"""
    # 예: graph_storage 관련 함수 호출 (Neo4j, S3 등)
    pass

# --- 조건부 엣지 함수 --- #

def decide_extraction_path(state: GraphState) -> Literal["extract_diagnostic", "extract_drug", "aggregate"]: 
    """추출 유형에 따라 다음 노드를 결정합니다."""
    extraction_type = state.get("extraction_type", "")
    if extraction_type == "diagnostic":
        return "extract_diagnostic"
    elif extraction_type == "drug":
        return "extract_drug"
    else: # combined 또는 다른 경우
        # 필요시 에러 처리 또는 다른 로직 추가
        return "aggregate" # 예시: 기본적으로 통합 노드로 이동

def check_validation_status(state: GraphState) -> Literal["run_verification", "handle_error", END]:
    """추출 유효성 검사 결과에 따라 다음 단계를 결정합니다."""
    status = state.get("extraction_validation_status", "invalid")
    if status == "valid":
        return "run_verification" # 검증 단계로 이동
    elif status == "needs_review":
        # 필요시 Human-in-the-loop 로직 추가
        return END # 예시: 검토 필요시 종료
    else: # invalid
        return "handle_error" # 오류 처리 노드로 이동

def decide_next_verification(state: GraphState) -> Literal["verify_omop", "save_results", END]:
    """코호트 검증 후 다음 단계를 결정합니다."""
    # 예시: 코호트 검증 결과에 따라 분기
    if state.get("cohort_validation_results", {}).get("status") == "passed":
        return "verify_omop"
    else:
        return END # 예시: 실패 시 종료

# --- 그래프 빌더 --- #

def build_graph():
    """LangGraph 워크플로우 그래프를 빌드합니다."""
    workflow = StateGraph(GraphState)

    # 노드 추가
    workflow.add_node("load_data", load_data_node)
    workflow.add_node("preprocess_text", preprocess_text_node)
    workflow.add_node("determine_extraction_type", determine_extraction_type_node)
    workflow.add_node("extract_diagnostic", extract_diagnostic_node)
    workflow.add_node("extract_drug", extract_drug_node)
    workflow.add_node("aggregate", aggregate_results_node) # 실제 분기 로직 후 필요한 노드
    workflow.add_node("validate_extraction", lambda state: state) # 유효성 검사 자체는 추출 노드 내에서 수행 가정
    workflow.add_node("verify_cohort", cohort_verification_node)
    workflow.add_node("verify_omop", omop_existence_verification_node)
    workflow.add_node("save_results", save_results_node)
    workflow.add_node("handle_error", lambda state: print(f"Error: {state.get('error_message')}")) # 간단한 오류 처리 예시

    # 엣지 설정
    workflow.set_entry_point("load_data")
    workflow.add_edge("load_data", "preprocess_text")
    workflow.add_edge("preprocess_text", "determine_extraction_type")

    # 추출 유형에 따른 조건부 엣지
    workflow.add_conditional_edges(
        "determine_extraction_type",
        decide_extraction_path,
        {
            "extract_diagnostic": "extract_diagnostic",
            "extract_drug": "extract_drug",
            "aggregate": "aggregate", # 통합 노드로 가는 경로
        }
    )

    # 추출 후 유효성 검사 결과에 따른 분기 (추출 노드에서 validate_extraction 노드로 연결 가정)
    # 실제로는 각 추출 노드(diagnostic, drug) 또는 통합(aggregate) 노드에서 validate_extraction 엣지로 연결해야 함.
    # 예시: workflow.add_edge("extract_diagnostic", "validate_extraction")
    # 예시: workflow.add_edge("extract_drug", "validate_extraction")
    workflow.add_edge("aggregate", "validate_extraction") # 예시: 통합 후 검사

    workflow.add_conditional_edges(
        "validate_extraction",
        check_validation_status,
        {
            "run_verification": "verify_cohort", # 유효하면 코호트 검증 시작
            "handle_error": "handle_error",
            END: END
        }
    )

    # 검증 단계 연결
    workflow.add_conditional_edges(
        "verify_cohort",
        decide_next_verification,
        {
            "verify_omop": "verify_omop",
            END: END
        }
    )
    workflow.add_edge("verify_omop", "save_results") # OMOP 검증 후 결과 저장

    # 종료점 설정
    workflow.add_edge("save_results", END)
    workflow.add_edge("handle_error", END)

    # 그래프 컴파일
    app = workflow.compile()
    return app

# 그래프 인스턴스 생성 (실행 시점에 호출)
# compiled_graph = build_graph() 