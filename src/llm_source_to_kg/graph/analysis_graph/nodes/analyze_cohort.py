from src.llm_source_to_kg.graph.analysis_graph.state import AnalysisGraphState
from src.llm_source_to_kg.schema.types import AnalysisSchema
import json
import asyncio
from typing import Dict, Any

# LLM 클라이언트 (예: OpenAI, Claude 등)
# from your_llm_client import llm_client

async def analyze_cohort(state: AnalysisGraphState) -> AnalysisGraphState:
    """
    코호트 데이터를 분석하여 medical entities를 추출합니다.
    
    Args:
        state: 현재 그래프 상태
        
    Returns:
        업데이트된 그래프 상태 (analysis 필드 포함)
    """
    cohort_data = state["cohort"]
    
    # 코호트별로 분석 수행
    analysis_results = {}
    
    for cohort_id, cohort_content in cohort_data.items():
        # LLM 프롬프트 구성
        prompt = f"""
        
        아래 코호트 설명에서 의료 관련 엔티티들을 추출해주세요.
        JSON 형태로만 답변해주세요.
        
        코호트 내용: {cohort_content}
        
        추출할 정보:
        {{
            "drug": ["약물명1", "약물명2", ...],
            "diagnostic": ["진단명1", "진단명2", ...],
            "medicalTest": ["검사명1", "검사명2", ...],
            "surgery": ["수술명1", "수술명2", ...],
            "symptoms": ["증상1", "증상2", ...],
            "procedures": ["시술명1", "시술명2", ...]
        }}
        """
        
        try:
            # LLM 호출 (실제 구현시 LLM 클라이언트 사용)
            # response = await llm_client.generate(prompt)
            
            # 더미 응답 (개발/테스트용)
            dummy_response = {
                "drug": ["메트포르민", "인슐린"],
                "diagnostic": ["당뇨병", "고혈압"],
                "medicalTest": ["혈당검사", "헤모글로빈A1c"],
                "surgery": [],
                "symptoms": ["다뇨", "다음", "체중감소"],
                "procedures": ["혈압측정", "체중측정"]
            }
            
            # JSON 파싱 시도
            if isinstance(dummy_response, str):
                extracted_entities = json.loads(dummy_response)
            else:
                extracted_entities = dummy_response
                
            analysis_results[cohort_id] = {
                "entities": extracted_entities,
                "status": "success",
                "cohort_content": cohort_content
            }
            
        except json.JSONDecodeError as e:
            analysis_results[cohort_id] = {
                "entities": {},
                "status": "error",
                "error": f"JSON 파싱 오류: {str(e)}",
                "cohort_content": cohort_content
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
            "failed_analyses": len([r for r in analysis_results.values() if r["status"] == "error"])
        }
    )
    
    # 상태 업데이트
    state["analysis"] = analysis_schema
    state["retries"] = state.get("retries", 0)
    
    return state