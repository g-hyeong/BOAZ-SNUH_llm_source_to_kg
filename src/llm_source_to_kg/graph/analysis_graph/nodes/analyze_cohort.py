from src.llm_source_to_kg.graph.analysis_graph.state import AnalysisGraphState
from src.llm_source_to_kg.schema.types import AnalysisSchema
from src.llm_source_to_kg.llm.client import get_llm_client
import json
import asyncio
import os
from pathlib import Path
from typing import Dict, Any


def load_prompt_template(template_name: str) -> str:
    """프롬프트 템플릿 파일을 로드합니다."""
    current_dir = Path(__file__).parent
    prompt_path = current_dir / "prompts" / f"{template_name}.txt"
    
    with open(prompt_path, 'r', encoding='utf-8') as file:
        return file.read()

async def analyze_cohort(state: AnalysisGraphState) -> AnalysisGraphState:
    """
    코호트 데이터를 분석하여 medical entities를 추출합니다.
    
    Args:
        state: 현재 그래프 상태
        
    Returns:
        업데이트된 그래프 상태 (analysis 필드 포함)
    """
    cohort_data = state["cohort"]
    
    # LLM 클라이언트 초기화
    llm_client = get_llm_client()
    
    # 프롬프트 템플릿 로드
    prompt_template = load_prompt_template("extract_analysis")
    
    # 코호트별로 분석 수행
    analysis_results = {}
    
    for cohort_id, cohort_content in cohort_data.items():
        # 프롬프트 구성
        prompt = prompt_template.format(cohort_content=cohort_content)
        
        try:
            # LLM 호출
            response = await llm_client.generate(prompt)
            
            # JSON 파싱 시도
            if isinstance(response, str):
                # LLM 응답에서 JSON 부분만 추출 (```json ... ``` 제거)
                response_cleaned = response.strip()
                if response_cleaned.startswith('```json'):
                    response_cleaned = response_cleaned[7:]
                if response_cleaned.endswith('```'):
                    response_cleaned = response_cleaned[:-3]
                if response_cleaned.startswith('```'):
                    response_cleaned = response_cleaned[3:]
                response_cleaned = response_cleaned.strip()
                
                extracted_entities = json.loads(response_cleaned)
            else:
                extracted_entities = response
                
            # 엔티티 검증 및 정리
            validated_entities = validate_extracted_entities(extracted_entities)
                
            analysis_results[cohort_id] = {
                "entities": validated_entities,
                "status": "success",
                "cohort_content": cohort_content,
                "raw_response": response[:500]  # 원본 응답 일부 저장
            }
            
        except json.JSONDecodeError as e:
            # JSON 파싱 실패시 더미 응답 사용
            dummy_entities = generate_dummy_entities(cohort_content)
            analysis_results[cohort_id] = {
                "entities": dummy_entities,
                "status": "error_fallback",
                "error": f"JSON 파싱 오류: {str(e)}",
                "cohort_content": cohort_content,
                "raw_response": response[:500] if 'response' in locals() else ""
            }
        except Exception as e:
            analysis_results[cohort_id] = {
                "entities": {},
                "status": "error", 
                "error": f"분석 오류: {str(e)}",
                "cohort_content": cohort_content
            }
    
    # AnalysisSchema 형태로 변환
    analysis_schema = AnalysisSchema(
        cohort_analyses=analysis_results,
        summary={
            "total_cohorts": len(cohort_data),
            "successful_analyses": len([r for r in analysis_results.values() if r["status"] == "success"]),
            "failed_analyses": len([r for r in analysis_results.values() if r["status"] == "error"]),
            "fallback_analyses": len([r for r in analysis_results.values() if r["status"] == "error_fallback"])
        }
    )
    
    # 상태 업데이트
    state["analysis"] = analysis_schema
    state["retries"] = state.get("retries", 0)
    
    return state

def validate_extracted_entities(entities: Dict[str, Any]) -> Dict[str, list]:
    """추출된 엔티티를 검증하고 정리합니다."""
    expected_keys = ["drug", "diagnostic", "medicalTest", "surgery", "symptoms", "procedures"]
    validated = {}
    
    for key in expected_keys:
        if key in entities and isinstance(entities[key], list):
            # 빈 문자열이나 None 제거, 중복 제거
            validated[key] = list(set([
                item.strip() for item in entities[key] 
                if item and isinstance(item, str) and item.strip()
            ]))
        else:
            validated[key] = []
    
    return validated

def generate_dummy_entities(cohort_content: str) -> Dict[str, list]:
    """코호트 내용 기반 더미 엔티티 생성 (LLM 실패시 폴백용)"""
    # 간단한 키워드 매칭으로 더미 데이터 생성
    dummy_entities = {
        "drug": [],
        "diagnostic": [],
        "medicalTest": [],
        "surgery": [],
        "symptoms": [],
        "procedures": []
    }
    
    # 기본적인 키워드 매칭 (실제 환경에서는 더 정교한 방법 필요)
    content_lower = cohort_content.lower()
    
    if any(keyword in content_lower for keyword in ["당뇨", "diabetes"]):
        dummy_entities["diagnostic"].append("당뇨병")
        dummy_entities["drug"].append("메트포르민")
        dummy_entities["medicalTest"].append("혈당검사")
    
    if any(keyword in content_lower for keyword in ["고혈압", "hypertension"]):
        dummy_entities["diagnostic"].append("고혈압")
        dummy_entities["medicalTest"].append("혈압측정")
    
    return dummy_entities