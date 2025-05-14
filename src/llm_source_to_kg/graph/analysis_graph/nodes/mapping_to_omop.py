from src.llm_source_to_kg.graph.analysis_graph.state import AnalysisGraphState
import requests
import json
from typing import Dict, Any
import asyncio

async def mapping_to_omop(state: AnalysisGraphState) -> AnalysisGraphState:
    """
    분석된 의료 엔티티를 OMOP CDM으로 매핑합니다.
    
    Args:
        state: 현재 그래프 상태
        
    Returns:
        업데이트된 그래프 상태 (mapping_result 필드 포함)
    """
    analysis = state["analysis"]
    
    # Elasticsearch OMOP 매핑 API 설정 (더미)
    ELASTICSEARCH_URL = "http://localhost:9200"
    OMOP_MAPPING_INDEX = "omop_mappings"
    
    mapping_results = {}
    
    # 각 코호트별 엔티티 매핑
    for cohort_id, analysis_result in analysis.cohort_analyses.items():
        if analysis_result["status"] != "success":
            mapping_results[cohort_id] = {
                "status": "skipped",
                "reason": "분석 실패"
            }
            continue
        
        entities = analysis_result["entities"]
        cohort_mapping = {}
        
        # 각 엔티티 유형별 OMOP 매핑
        for entity_type, entity_list in entities.items():
            mapped_entities = []
            
            for entity in entity_list:
                try:
                    # dummy Elasticsearch request (실제 구현시)
                    # query = {
                    #     "query": {
                    #         "match": {
                    #             "concept_name": entity
                    #         }
                    #     },
                    #     "size": 1,
                    #     "_source": ["concept_id", "concept_name", "domain_id"]
                    # }
                    # response = requests.post(
                    #     f"{ELASTICSEARCH_URL}/{OMOP_MAPPING_INDEX}/_search",
                    #     json=query
                    # )
                    # result = response.json()
                    
                    # 더미 응답 생성
                    dummy_omop_mapping = {
                        "concept_id": f"OMOP_{hash(entity) % 1000000}",
                        "concept_name": entity,
                        "domain_id": get_omop_domain(entity_type),
                        "vocabulary_id": get_omop_vocabulary(entity_type),
                        "concept_class_id": get_omop_concept_class(entity_type),
                        "standard_concept": "S",
                        "confidence_score": 0.95
                    }
                    
                    mapped_entities.append({
                        "original_entity": entity,
                        "omop_mapping": dummy_omop_mapping,
                        "mapping_status": "success"
                    })
                    
                except Exception as e:
                    mapped_entities.append({
                        "original_entity": entity,
                        "omop_mapping": None,
                        "mapping_status": "failed",
                        "error": str(e)
                    })
            
            cohort_mapping[entity_type] = mapped_entities
        
        mapping_results[cohort_id] = {
            "status": "success",
            "mappings": cohort_mapping,
            "summary": {
                "total_entities": sum(len(entities[et]) for et in entities),
                "mapped_entities": sum(
                    len([m for m in cohort_mapping[et] if m["mapping_status"] == "success"])
                    for et in cohort_mapping
                )
            }
        }
    
    # 상태 업데이트
    state["mapping_result"] = mapping_results
    
    return state

def get_omop_domain(entity_type: str) -> str:
    """엔티티 타입에 따른 OMOP 도메인 반환"""
    domain_mapping = {
        "drug": "Drug",
        "diagnostic": "Condition", 
        "medicalTest": "Measurement",
        "surgery": "Procedure",
        "symptoms": "Observation",
        "procedures": "Procedure"
    }
    return domain_mapping.get(entity_type, "Observation")

def get_omop_vocabulary(entity_type: str) -> str:
    """엔티티 타입에 따른 OMOP 어휘 반환"""
    vocab_mapping = {
        "drug": "RxNorm",
        "diagnostic": "SNOMED",
        "medicalTest": "LOINC", 
        "surgery": "SNOMED",
        "symptoms": "SNOMED",
        "procedures": "SNOMED"
    }
    return vocab_mapping.get(entity_type, "SNOMED")

def get_omop_concept_class(entity_type: str) -> str:
    """엔티티 타입에 따른 OMOP 컨셉 클래스 반환"""
    class_mapping = {
        "drug": "Clinical Drug",
        "diagnostic": "Clinical Finding",
        "medicalTest": "Lab Test",
        "surgery": "Procedure", 
        "symptoms": "Clinical Finding",
        "procedures": "Procedure"
    }
    return class_mapping.get(entity_type, "Clinical Finding")
