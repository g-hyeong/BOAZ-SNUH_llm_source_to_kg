"""
LangGraph 워크플로우의 상태를 정의합니다.

Pydantic 모델을 사용하여 상태의 구조와 타입을 명확히 합니다.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic_types.graph_state import *


# 메인 상태 모델
class GraphState(BaseModel):
    # 입력 데이터 관련
    input_source: str = Field(..., description="입력 데이터 소스 (예: s3_uri, file_path)")
    document_content: Optional[str] = Field(None, description="로드 및 전처리된 문서 내용")
    document_chunks: Optional[List[str]] = Field(None, description="분할된 문서 청크")
    
    # 분석 관련
    analysis_type: Optional[str] = Field(None, description="결정된 분석 유형 ('diagnostic', 'drug', 'both')")
    drug_results: Optional[DrugResults] = Field(None, description="약물 분석 결과")
    diagnostic_results: Optional[DiagnosticResults] = Field(None, description="진단 분석 결과")
    aggregated_results: Optional[Dict[str, Any]] = Field(None, description="통합된 분석 결과")
    
    # 검증 관련
    extraction_val_status: Optional[str] = Field(None, description="추출 결과 유효성 상태 ('valid', 'invalid', 'needs_review')")
    cohort_val_results: Optional[ValidationResult] = Field(None, description="코호트 검증 결과")
    omop_existence_results: Optional[ValidationResult] = Field(None, description="OMOP 존재 여부 검증 결과")
    
    # 최종 결과
    total_results: Optional[Dict[str, Any]] = Field(None, description="모든 처리 결과를 포함하는 최종 결과")
    knowledge_graph_nodes: Optional[List[KnowledgeGraphNode]] = Field(None, description="생성된 KG 노드")
    knowledge_graph_edges: Optional[List[KnowledgeGraphEdge]] = Field(None, description="생성된 KG 엣지")
    
    # 오류 및 메타데이터
    error_message: Optional[str] = Field(None, description="워크플로우 중 발생한 오류 메시지")
    current_step: Optional[str] = Field(None, description="현재 실행 중인 노드 또는 단계 이름") 