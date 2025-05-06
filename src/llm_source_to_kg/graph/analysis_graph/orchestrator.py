from state import AnalysisGraphState
from langgraph import Graph, Orchestrator

from nodes import (
    analyze_cohort,
    load_to_kg,
    mapping_to_omop,
    validate_analysis
)

def build_workflow() -> Graph[AnalysisGraphState]:
    g = Graph[AnalysisGraphState]("OmopMappingWorkflow")

    # 1) 분석 노드
    analysis = analyze_cohort(
        name="RunAnalysis",
        inputs=["cohort"],
        outputs=["analysis"],
    )

    # 2) 검증 노드
    validation = validate_analysis(
        name="ValidateAnalysis",
        inputs=["analysis"],
        outputs=["is_valid"],
    )

    # 3) 매핑 API 호출 노드
    mapping_api = mapping_to_omop(
        name="CallMappingAPI",
        inputs=["analysis"],
        outputs=["mapping_result"],
    )

    # 4) 지식 그래프 적재 노드
    loader = load_to_kg(
        name="LoadToKnowledgeGraph",
        inputs=["mapping_result"],
        outputs=[],
    )

    # 노드 등록
    g.add_nodes(analysis, validation, mapping_api, loader)
    g.add_edge("RunAnalysis", "ValidateAnalysis")
    g.add_edge(
        "ValidateAnalysis", "RunAnalysis",
        condition=lambda st: not st["is_valid"] and st["retries"] < MAX_RETRIES
    )
    g.add_edge(
        "ValidateAnalysis", "CallMappingAPI",
        condition=lambda st: st["is_valid"]
    )
    g.add_edge("CallMappingAPI", "LoadToKnowledgeGraph")

    return g


MAX_RETRIES = 3

def build():    
    init_state: AnalysisGraphState = {
        "context": "",
        "question": "",
        "answer": "",
        "source_reference_number": "",
        "is_valid": False,
        "retries": 0,
        "cohort": {},       # CohortGraphState 결과
        "analysis": {},     # 빈 placeholder
    }

    wf = build_workflow()
    orch = Orchestrator(wf)
    result_state = orch.run(init_state)
    print("Workflow completed. Final state:", result_state)