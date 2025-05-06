"""
지식 그래프 생성 및 저장을 위한 모듈입니다.
"""

import os
import json
from typing import Dict, List, Any
from datetime import datetime
import uuid
from pathlib import Path

from src.graph.state import KnowledgeGraphNode, KnowledgeGraphEdge
from src.common.utils import get_logger, save_json

# 로거 초기화
logger = get_logger(__name__)

def generate_knowledge_graph(aggregated_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    통합 결과에서 지식 그래프를 생성합니다.
    
    Args:
        aggregated_results: 통합된 추출 결과
        
    Returns:
        노드와 엣지로 구성된 지식 그래프
    """
    logger.info("지식 그래프 생성 시작")
    
    nodes = []
    edges = []
    
    # 노드 ID 맵핑 (엔티티 이름 -> ID)
    entity_id_map = {}
    
    # 진단 엔티티 처리
    if "diagnostic" in aggregated_results and "condition_entities" in aggregated_results["diagnostic"]:
        condition_entities = aggregated_results["diagnostic"]["condition_entities"]
        
        for entity in condition_entities:
            # 노드 ID 생성
            entity_name = entity.get("concept_name", "")
            if not entity_name:
                continue
                
            node_id = f"condition_{str(uuid.uuid4())[:8]}"
            entity_id_map[entity_name] = node_id
            
            # 노드 생성
            node = KnowledgeGraphNode(
                id=node_id,
                label="Condition",
                properties={
                    "name": entity_name,
                    "category": entity.get("condition_category", ""),
                    "severity": entity.get("severity", ""),
                    "evidence_level": entity.get("evidence_level", "")
                }
            )
            nodes.append(node)
    
    # 약물 엔티티 처리
    if "drug" in aggregated_results and "drug_entities" in aggregated_results["drug"]:
        drug_entities = aggregated_results["drug"]["drug_entities"]
        
        for entity in drug_entities:
            # 노드 ID 생성
            entity_name = entity.get("concept_name", "")
            if not entity_name:
                continue
                
            node_id = f"drug_{str(uuid.uuid4())[:8]}"
            entity_id_map[entity_name] = node_id
            
            # 노드 생성
            node = KnowledgeGraphNode(
                id=node_id,
                label="Drug",
                properties={
                    "name": entity_name,
                    "drug_class": entity.get("drug_class", ""),
                    "evidence_level": entity.get("evidence_level", "")
                }
            )
            nodes.append(node)
            
            # 용법 정보가 있는 경우 추가 노드 생성
            if "dosing" in entity and entity["dosing"]:
                dosing = entity["dosing"]
                if any(dosing.values()):
                    dosing_id = f"dosing_{str(uuid.uuid4())[:8]}"
                    
                    # 용법 노드
                    dosing_node = KnowledgeGraphNode(
                        id=dosing_id,
                        label="Dosing",
                        properties={k: v for k, v in dosing.items() if v}
                    )
                    nodes.append(dosing_node)
                    
                    # 약물-용법 엣지
                    edge = KnowledgeGraphEdge(
                        source=node_id,
                        target=dosing_id,
                        type="HAS_DOSING"
                    )
                    edges.append(edge)
    
    # 관계 처리
    # 진단 관계
    if "diagnostic" in aggregated_results and "condition_relationships" in aggregated_results["diagnostic"]:
        relationships = aggregated_results["diagnostic"]["condition_relationships"]
        
        for rel in relationships:
            source_name = rel.get("source_condition", "")
            target_name = rel.get("target_entity", "")
            relationship_type = rel.get("relationship_type", "")
            
            if not source_name or not target_name or not relationship_type:
                continue
            
            # 소스와 타겟 ID 찾기
            source_id = entity_id_map.get(source_name)
            target_id = entity_id_map.get(target_name)
            
            if source_id and target_id:
                edge = KnowledgeGraphEdge(
                    source=source_id,
                    target=target_id,
                    type=relationship_type.upper(),
                    properties={
                        "details": rel.get("details", ""),
                        "certainty": rel.get("certainty", "")
                    }
                )
                edges.append(edge)
    
    # 약물 관계
    if "drug" in aggregated_results and "drug_relationships" in aggregated_results["drug"]:
        relationships = aggregated_results["drug"]["drug_relationships"]
        
        for rel in relationships:
            source_name = rel.get("source_drug", "")
            target_name = rel.get("target_entity", "")
            relationship_type = rel.get("relationship_type", "")
            
            if not source_name or not target_name or not relationship_type:
                continue
            
            # 소스와 타겟 ID 찾기
            source_id = entity_id_map.get(source_name)
            target_id = entity_id_map.get(target_name)
            
            if source_id and target_id:
                edge = KnowledgeGraphEdge(
                    source=source_id,
                    target=target_id,
                    type=relationship_type.upper(),
                    properties={
                        "details": rel.get("details", ""),
                        "certainty": rel.get("certainty", "")
                    }
                )
                edges.append(edge)
    
    logger.info(f"지식 그래프 생성 완료: 노드 {len(nodes)}개, 엣지 {len(edges)}개")
    
    return {
        "nodes": nodes,
        "edges": edges
    }

def save_results(results: Dict[str, Any]) -> str:
    """
    결과를 파일로 저장합니다.
    
    Args:
        results: 저장할 결과 데이터
        
    Returns:
        저장된 파일 경로
    """
    # 결과 저장 디렉토리 생성
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # 타임스탬프를 포함한 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"kg_results_{timestamp}.json"
    
    # 결과 저장
    save_json(results, str(filepath))
    
    logger.info(f"결과 저장 완료: {filepath}")
    
    return str(filepath)

def save_to_neo4j(nodes: List[KnowledgeGraphNode], edges: List[KnowledgeGraphEdge]) -> bool:
    """
    지식 그래프를 Neo4j 데이터베이스에 저장합니다.
    이 함수는 Neo4j 데이터베이스가 구성되어 있을 때 사용합니다.
    
    Args:
        nodes: 그래프 노드 목록
        edges: 그래프 엣지 목록
        
    Returns:
        성공 여부
    """
    try:
        from neo4j import GraphDatabase
        
        # Neo4j 설정 - 실제 구현에서는 환경 변수나 설정 파일에서 로드
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        username = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "password")
        
        # Neo4j 연결
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            # 노드 생성
            for node in nodes:
                properties_str = ", ".join([f"`{k}`: ${k}" for k in node.properties.keys()])
                query = f"CREATE (n:`{node.label}` {{{properties_str}, id: $id}})"
                session.run(query, id=node.id, **node.properties)
            
            # 엣지 생성
            for edge in edges:
                if edge.properties:
                    properties_str = ", ".join([f"`{k}`: ${k}" for k in edge.properties.keys()])
                    query = f"""
                    MATCH (a), (b)
                    WHERE a.id = $source_id AND b.id = $target_id
                    CREATE (a)-[r:`{edge.type}` {{{properties_str}}}]->(b)
                    """
                    session.run(query, source_id=edge.source, target_id=edge.target, **edge.properties)
                else:
                    query = f"""
                    MATCH (a), (b)
                    WHERE a.id = $source_id AND b.id = $target_id
                    CREATE (a)-[r:`{edge.type}`]->(b)
                    """
                    session.run(query, source_id=edge.source, target_id=edge.target)
        
        driver.close()
        logger.info(f"Neo4j 저장 완료: 노드 {len(nodes)}개, 엣지 {len(edges)}개")
        return True
        
    except ImportError:
        logger.error("Neo4j 드라이버가 설치되지 않았습니다.")
        return False
    except Exception as e:
        logger.error(f"Neo4j 저장 중 오류 발생: {str(e)}")
        return False 