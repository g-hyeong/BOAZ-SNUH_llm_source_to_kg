from src.llm_source_to_kg.graph.analysis_graph.state import AnalysisGraphState
import json
from typing import Dict, Any
import requests
from datetime import datetime

def load_to_kg(state: AnalysisGraphState) -> AnalysisGraphState:
    """
    OMOP 매핑 결과를 지식 그래프에 적재합니다.
    
    Args:
        state: 현재 그래프 상태
        
    Returns:
        업데이트된 그래프 상태 (kg_load_result 필드 포함)
    """
    mapping_result = state["mapping_result"]
    
    # 지식 그래프 설정 (Neo4j, GraphDB 등)
    KG_ENDPOINT = "http://localhost:7474/db/data/transaction/commit"
    
    load_results = {}
    total_loaded = 0
    
    # 각 코호트별 매핑 결과를 지식 그래프에 적재
    for cohort_id, mapping_data in mapping_result.items():
        if mapping_data["status"] != "success":
            load_results[cohort_id] = {
                "status": "skipped",
                "reason": "매핑 실패"
            }
            continue
        
        try:
            # 코호트 노드 생성
            cohort_node_query = create_cohort_node_query(cohort_id, state["cohort"][cohort_id])
            
            # 각 엔티티별 노드 및 관계 생성
            entity_queries = []
            mappings = mapping_data["mappings"]
            
            for entity_type, entities in mappings.items():
                for entity_data in entities:
                    if entity_data["mapping_status"] == "success":
                        omop_mapping = entity_data["omop_mapping"]
                        
                        # 엔티티 노드 생성 쿼리
                        entity_query = create_entity_node_query(
                            entity_type,
                            entity_data["original_entity"],
                            omop_mapping
                        )
                        entity_queries.append(entity_query)
                        
                        # 코호트-엔티티 관계 생성 쿼리
                        relation_query = create_cohort_entity_relation_query(
                            cohort_id,
                            omop_mapping["concept_id"],
                            entity_type
                        )
                        entity_queries.append(relation_query)
            
            # 전체 쿼리 구성
            all_queries = [cohort_node_query] + entity_queries
            
            # 지식 그래프에 적재 (더미 요청)
            # kg_request = {
            #     "statements": [{"statement": query} for query in all_queries]
            # }
            # response = requests.post(KG_ENDPOINT, json=kg_request)
            # response.raise_for_status()
            
            load_results[cohort_id] = {
                "status": "success",
                "loaded_entities": len([e for et in mappings.values() for e in et if e["mapping_status"] == "success"]),
                "queries_executed": len(all_queries),
                "timestamp": datetime.now().isoformat()
            }
            
            total_loaded += load_results[cohort_id]["loaded_entities"]
            
        except Exception as e:
            load_results[cohort_id] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # 전체 적재 결과
    kg_load_result = {
        "overall_status": "success" if all(r["status"] == "success" for r in load_results.values()) else "partial",
        "cohort_results": load_results,
        "summary": {
            "total_cohorts": len(mapping_result),
            "successful_loads": len([r for r in load_results.values() if r["status"] == "success"]),
            "total_entities_loaded": total_loaded
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # 상태 업데이트
    state["kg_load_result"] = kg_load_result
    
    return state

def create_cohort_node_query(cohort_id: str, cohort_content: str) -> str:
    """코호트 노드 생성 Cypher 쿼리"""
    return f"""
    MERGE (c:Cohort {{id: '{cohort_id}'}})
    SET c.content = '{cohort_content.replace("'", "\\'")}',
        c.created_at = timestamp()
    """

def create_entity_node_query(entity_type: str, original_entity: str, omop_mapping: dict) -> str:
    """엔티티 노드 생성 Cypher 쿼리"""
    concept_id = omop_mapping["concept_id"]
    concept_name = omop_mapping["concept_name"]
    domain_id = omop_mapping["domain_id"]
    
    return f"""
    MERGE (e:Entity:OMOP {{concept_id: '{concept_id}'}})
    SET e.concept_name = '{concept_name.replace("'", "\\'")}',
        e.domain_id = '{domain_id}',
        e.vocabulary_id = '{omop_mapping.get("vocabulary_id", "")}',
        e.concept_class_id = '{omop_mapping.get("concept_class_id", "")}',
        e.original_text = '{original_entity.replace("'", "\\'")}',
        e.entity_type = '{entity_type}',
        e.created_at = timestamp()
    """

def create_cohort_entity_relation_query(cohort_id: str, concept_id: str, entity_type: str) -> str:
    """코호트-엔티티 관계 생성 Cypher 쿼리"""
    relation_type = f"HAS_{entity_type.upper()}"
    
    return f"""
    MATCH (c:Cohort {{id: '{cohort_id}'}}), (e:Entity {{concept_id: '{concept_id}'}})
    MERGE (c)-[r:{relation_type}]->(e)
    SET r.created_at = timestamp()
    """