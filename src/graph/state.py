"""
LangGraph 워크플로우의 상태를 정의합니다.

TypedDict 또는 Pydantic 모델을 사용하여 상태의 구조와 타입을 명확히 합니다.
"""

from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict):
    """
    메인 KG 생성 워크플로우의 상태를 나타내는 TypedDict입니다.
    워크플로우 진행에 따라 필드가 추가되거나 업데이트됩니다.
    """
    # 입력 데이터 관련
    input_source: str  # 입력 데이터 소스 (예: s3_uri, file_path)
    document_content: Optional[str]  # 로드 및 전처리된 문서 내용
    document_chunks: Optional[List[str]] # 분할된 문서 청크

    # 추출 관련
    extraction_type: Optional[str] # 결정된 추출 유형 ('diagnostic', 'drug', etc.)
    diagnostic_entities: Optional[List[Dict[str, Any]]] # 추출된 진단 엔티티
    drug_entities: Optional[List[Dict[str, Any]]] # 추출된 약물 엔티티
    structured_diagnostic_info: Optional[Any] # 구조화된 진단 정보 (Pydantic 모델 등)
    structured_drug_info: Optional[Any] # 구조화된 약물 정보 (Pydantic 모델 등)
    aggregated_results: Optional[Any] # 통합된 추출 결과

    # 검증 관련
    extraction_validation_status: Optional[str] # 추출 결과 유효성 상태 ('valid', 'invalid', 'needs_review')
    cohort_validation_results: Optional[Dict[str, Any]] # 코호트 기준 검증 결과
    omop_existence_results: Optional[Dict[str, Any]] # OMOP 존재 여부 검증 결과

    # 최종 결과
    knowledge_graph_nodes: Optional[List[Dict[str, Any]]] # 생성된 KG 노드
    knowledge_graph_edges: Optional[List[Dict[str, Any]]] # 생성된 KG 엣지

    # 오류 및 메타데이터
    error_message: Optional[str] # 워크플로우 중 발생한 오류 메시지
    current_step: Optional[str] # 현재 실행 중인 노드 또는 단계 이름 