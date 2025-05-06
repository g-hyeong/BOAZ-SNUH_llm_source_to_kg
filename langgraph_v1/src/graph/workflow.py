"""
LangGraph를 활용한 문서 분석 워크플로우 구현

이 모듈은 LangGraph를 사용하여 진단 및 약물 정보를 추출하는 
워크플로우를 정의합니다.
"""

import json
from typing import Dict, List, Any, Annotated, Tuple
from pathlib import Path
import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from common.llm.gemini_llm import GeminiLLM
from common.logging import get_logger
from config import settings
from pydantic_types.graph_state import DiagnosticResults, DrugResults, ValidationResult
from graph.state import GraphState

# 로거 설정
logger = get_logger("graph_workflow")

def create_workflow(llm_config: Dict[str, Any]) -> StateGraph:
    """
    LangGraph 워크플로우 생성
    
    Args:
        llm_config: LLM 설정 정보
        
    Returns:
        StateGraph: 설정된 LangGraph 워크플로우
    """
    # LLM 인스턴스 생성
    llm = GeminiLLM(**llm_config)
    
    # 워크플로우 그래프 생성
    workflow = StateGraph(GraphState)
    
    # 1. 문서 내용 로딩 노드
    def load_document(state: GraphState) -> GraphState:
        try:
            logger.info(f"문서 로딩 시작: {state.input_source}")
            target_path = Path(state.input_source)
            
            if not target_path.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {target_path}")
            
            # JSON 파일 로드
            with open(target_path, 'r', encoding='utf-8') as f:
                guideline_data = json.load(f)
            
            # 제목과 내용 추출
            title = guideline_data.get('title', '제목 없음')
            contents = guideline_data.get('contents', '')
            
            # contents가 딕셔너리인 경우 문자열로 변환
            if isinstance(contents, dict):
                # 딕셔너리의 모든 섹션을 연결
                content_text = ""
                for section, text in contents.items():
                    content_text += f"## {section}\n\n{text}\n\n"
                contents = content_text
            
            # 문서 내용 설정
            state.document_content = f"# {title}\n\n{contents}"
            
            # 간단한 청킹 (실제 구현에서는 더 복잡할 수 있음)
            chunks = contents.split('\n\n')
            state.document_chunks = [chunk for chunk in chunks if chunk.strip()]
            
            logger.info(f"문서 로딩 완료: 제목=\"{title}\", 청크 수={len(state.document_chunks or [])}")
            
            # 현재 단계 업데이트
            state.current_step = "load_document"
            return state
            
        except Exception as e:
            logger.error(f"문서 로딩 중 오류 발생: {str(e)}")
            state.error_message = f"문서 로딩 오류: {str(e)}"
            return state
    
    # 2. 분석 유형 결정 노드
    def determine_analysis_type(state: GraphState) -> GraphState:
        try:
            logger.info("분석 유형 결정 시작")
            
            # 문서 내용 확인
            if not state.document_content or not state.document_chunks:
                raise ValueError("문서 내용이 없습니다. 먼저 문서를 로드하세요.")
            
            # 분석 유형 결정 프롬프트 생성
            system_prompt = """당신은 의료 가이드라인 분석 전문가입니다. 다음 의료 가이드라인 문서를 분석하여 가장 적합한 분석 유형을 결정하세요.

분석 유형 옵션:
1. diagnostic - 진단 관련 정보가 주로 포함된 경우
2. drug - 약물 관련 정보가 주로 포함된 경우
3. both - 진단과 약물 정보가 모두 중요하게 포함된 경우

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명은 포함하지 마세요:
{"analysis_type": "<결정된 유형>", "explanation": "<결정 이유>"}"""
            
            # 문서의 처음 부분만 사용 (토큰 제한 고려)
            document_sample = state.document_content[:10000] + "..."
            
            # 단일 프롬프트로 변경
            prompt = f"{system_prompt}\n\n{document_sample}"
            
            # LLM 호출
            response = llm.chat(prompt)
            
            # 응답 로깅
            logger.info(f"LLM 분석 유형 응답: {response}")
            
            # JSON 응답 추출
            try:
                # 응답이 문자열, LLMResult 객체, 또는 다른 형태일 수 있으므로 적절히 처리
                if isinstance(response, str):
                    response_text = response
                elif hasattr(response, "response"):
                    response_text = response.response
                else:
                    response_text = str(response)
                
                # JSON 블록 추출 시도 (```json ... ``` 형식으로 응답했을 수 있음)
                if "```json" in response_text and "```" in response_text.split("```json", 1)[1]:
                    json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                    result = json.loads(json_str)
                elif "{" in response_text and "}" in response_text:
                    # { } 블록 추출 시도
                    json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
                    result = json.loads(json_str)
                else:
                    result = json.loads(response_text)
                
                analysis_type = result.get("analysis_type", "both")
                explanation = result.get("explanation", "")
                
                # 유효한 분석 유형 확인
                if analysis_type not in ["diagnostic", "drug", "both"]:
                    logger.warning(f"유효하지 않은 분석 유형: {analysis_type}, 기본값 'both'로 설정")
                    analysis_type = "both"
                
                state.analysis_type = analysis_type
                logger.info(f"분석 유형 결정 완료: {analysis_type} - {explanation}")
                
            except json.JSONDecodeError:
                logger.warning("JSON 파싱 실패, 기본값 'both'로 설정")
                state.analysis_type = "both"
            
            # 현재 단계 업데이트
            state.current_step = "determine_analysis_type"
            return state
            
        except Exception as e:
            logger.error(f"분석 유형 결정 중 오류 발생: {str(e)}")
            state.error_message = f"분석 유형 결정 오류: {str(e)}"
            return state
    
    # 3. 진단 정보 추출 노드
    def extract_diagnostic_info(state: GraphState) -> GraphState:
        try:
            # 분석 유형 확인
            if state.analysis_type not in ["diagnostic", "both"]:
                logger.info("진단 정보 추출 건너뜀 (분석 유형이 'drug'임)")
                return state
            
            logger.info("진단 정보 추출 시작")
            
            # 프롬프트 생성
            system_prompt = """의료 가이드라인에서 진단 관련 정보를 추출하세요. 다음 정보를 포함해야 합니다:
- 질병/상태 엔티티
- 진단 관계
- 진단 경로
- 조건 코호트

JSON 형식으로 응답하세요."""
            
            # 단일 프롬프트로 변경
            prompt = f"{system_prompt}\n\n{state.document_content}"
            
            # LLM 호출
            response = llm.chat(prompt)
            
            # JSON 응답 추출 시도
            try:
                # 응답이 문자열, LLMResult 객체, 또는 다른 형태일 수 있으므로 적절히 처리
                if isinstance(response, str):
                    response_text = response
                elif hasattr(response, "response"):
                    response_text = response.response
                else:
                    response_text = str(response)
                
                diagnostic_json = json.loads(response_text)
                
                # DiagnosticResults 모델로 변환
                diagnostic_results = DiagnosticResults(
                    condition_entities=diagnostic_json.get("condition_entities", []),
                    condition_relationships=diagnostic_json.get("condition_relationships", []),
                    diagnostic_pathways=diagnostic_json.get("diagnostic_pathways", []),
                    condition_cohorts=diagnostic_json.get("condition_cohorts", []),
                    detailed_analysis=diagnostic_json.get("detailed_analysis", "")
                )
                
                state.diagnostic_results = diagnostic_results
                logger.info(f"진단 정보 추출 완료: {len(diagnostic_results.condition_entities)} 엔티티 발견")
                
            except (json.JSONDecodeError, Exception) as e:
                logger.error(f"진단 정보 파싱 오류: {str(e)}")
                state.error_message = f"진단 정보 추출 오류: {str(e)}"
            
            # 현재 단계 업데이트
            state.current_step = "extract_diagnostic_info"
            return state
            
        except Exception as e:
            logger.error(f"진단 정보 추출 중 오류 발생: {str(e)}")
            state.error_message = f"진단 정보 추출 오류: {str(e)}"
            return state
    
    # 4. 약물 정보 추출 노드
    def extract_drug_info(state: GraphState) -> GraphState:
        try:
            # 분석 유형 확인
            if state.analysis_type not in ["drug", "both"]:
                logger.info("약물 정보 추출 건너뜀 (분석 유형이 'diagnostic'임)")
                return state
            
            logger.info("약물 정보 추출 시작")
            
            # 프롬프트 생성
            system_prompt = """의료 가이드라인에서 약물 관련 정보를 추출하세요. 다음 정보를 포함해야 합니다:
- 약물 엔티티
- 약물 관계
- 치료 경로
- 약물 코호트

JSON 형식으로 응답하세요."""
            
            # 단일 프롬프트로 변경
            prompt = f"{system_prompt}\n\n{state.document_content}"
            
            # LLM 호출
            response = llm.chat(prompt)
            
            # JSON 응답 추출 시도
            try:
                # 응답이 문자열, LLMResult 객체, 또는 다른 형태일 수 있으므로 적절히 처리
                if isinstance(response, str):
                    response_text = response
                elif hasattr(response, "response"):
                    response_text = response.response
                else:
                    response_text = str(response)
                
                drug_json = json.loads(response_text)
                
                # DrugResults 모델로 변환
                drug_results = DrugResults(
                    drug_entities=drug_json.get("drug_entities", []),
                    drug_relationships=drug_json.get("drug_relationships", []),
                    treatment_pathways=drug_json.get("treatment_pathways", []),
                    medication_cohorts=drug_json.get("medication_cohorts", []),
                    detailed_analysis=drug_json.get("detailed_analysis", "")
                )
                
                state.drug_results = drug_results
                logger.info(f"약물 정보 추출 완료: {len(drug_results.drug_entities)} 엔티티 발견")
                
            except (json.JSONDecodeError, Exception) as e:
                logger.error(f"약물 정보 파싱 오류: {str(e)}")
                state.error_message = f"약물 정보 추출 오류: {str(e)}"
            
            # 현재 단계 업데이트
            state.current_step = "extract_drug_info"
            return state
            
        except Exception as e:
            logger.error(f"약물 정보 추출 중 오류 발생: {str(e)}")
            state.error_message = f"약물 정보 추출 오류: {str(e)}"
            return state
    
    # 5. 결과 집계 노드
    def aggregate_results(state: GraphState) -> GraphState:
        try:
            logger.info("결과 집계 시작")
            
            # 진단 및 약물 결과 확인
            has_diagnostic = state.diagnostic_results is not None
            has_drug = state.drug_results is not None
            
            if not has_diagnostic and not has_drug:
                logger.warning("진단 및 약물 추출 결과가 모두 없습니다.")
                state.error_message = "진단 및 약물 추출 결과가 모두 없습니다."
                return state
            
            # 집계된 결과 생성
            aggregated_results = {
                "analysis_type": state.analysis_type,
                "timestamp": time.time(),
                "source": Path(state.input_source).name
            }
            
            # 진단 정보 추가
            if has_diagnostic:
                diagnostic_info = {
                    "entity_count": len(state.diagnostic_results.condition_entities),
                    "relationship_count": len(state.diagnostic_results.condition_relationships),
                    "pathway_count": len(state.diagnostic_results.diagnostic_pathways),
                    "cohort_count": len(state.diagnostic_results.condition_cohorts)
                }
                aggregated_results["diagnostic_info"] = diagnostic_info
            
            # 약물 정보 추가
            if has_drug:
                drug_info = {
                    "entity_count": len(state.drug_results.drug_entities),
                    "relationship_count": len(state.drug_results.drug_relationships),
                    "pathway_count": len(state.drug_results.treatment_pathways),
                    "cohort_count": len(state.drug_results.medication_cohorts)
                }
                aggregated_results["drug_info"] = drug_info
            
            # 결과 저장
            state.aggregated_results = aggregated_results
            logger.info(f"결과 집계 완료: {aggregated_results}")
            
            # 현재 단계 업데이트
            state.current_step = "aggregate_results"
            return state
            
        except Exception as e:
            logger.error(f"결과 집계 중 오류 발생: {str(e)}")
            state.error_message = f"결과 집계 오류: {str(e)}"
            return state
    
    # 6. 결과 저장 노드
    def save_results(state: GraphState) -> GraphState:
        try:
            logger.info("결과 저장 시작")
            
            # 결과 확인
            if not state.aggregated_results:
                logger.warning("저장할 집계 결과가 없습니다.")
                state.error_message = "저장할 집계 결과가 없습니다."
                return state
            
            # 결과 디렉토리 생성
            results_dir = settings.result_dir
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # 파일명 생성
            source_name = Path(state.input_source).stem
            timestamp = int(time.time())
            output_file = results_dir / f"{source_name}_results_{timestamp}.json"
            
            # 최종 결과 생성
            final_results = {
                "metadata": {
                    "source": state.input_source,
                    "timestamp": timestamp,
                    "analysis_type": state.analysis_type
                },
                "aggregated_results": state.aggregated_results
            }
            
            # 진단 결과 추가
            if state.diagnostic_results:
                final_results["diagnostic_results"] = state.diagnostic_results.model_dump()
            
            # 약물 결과 추가
            if state.drug_results:
                final_results["drug_results"] = state.drug_results.model_dump()
            
            # 오류 메시지 추가
            if state.error_message:
                final_results["error"] = state.error_message
            
            # 결과 저장
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(final_results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"결과 저장 완료: {output_file}")
            
            # 결과 저장 정보 추가
            state.total_results = final_results
            
            # 현재 단계 업데이트
            state.current_step = "save_results"
            return state
            
        except Exception as e:
            logger.error(f"결과 저장 중 오류 발생: {str(e)}")
            state.error_message = f"결과 저장 오류: {str(e)}"
            return state
    
    # 워크플로우 노드 등록
    workflow.add_node("load_document", load_document)
    workflow.add_node("determine_analysis_type", determine_analysis_type)
    workflow.add_node("extract_diagnostic_info", extract_diagnostic_info)
    workflow.add_node("extract_drug_info", extract_drug_info)
    workflow.add_node("aggregate_results", aggregate_results)
    workflow.add_node("save_results", save_results)
    
    # 엣지 연결
    workflow.add_edge("load_document", "determine_analysis_type")
    workflow.add_edge("determine_analysis_type", "extract_diagnostic_info")
    workflow.add_edge("extract_diagnostic_info", "extract_drug_info")
    workflow.add_edge("extract_drug_info", "aggregate_results")
    workflow.add_edge("aggregate_results", "save_results")
    workflow.add_edge("save_results", END)
    
    # 시작점 설정
    workflow.set_entry_point("load_document")
    
    # 워크플로우 컴파일
    return workflow.compile()

def process_source(
    source_path: str, 
    llm_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    특정 소스 파일을 처리하는 함수
    
    Args:
        source_path: 소스 파일 경로
        llm_config: LLM 설정
        
    Returns:
        Dict[str, Any]: 처리 결과
    """
    # 워크플로우 생성
    workflow = create_workflow(llm_config)
    
    # 초기 상태 설정
    initial_state = GraphState(input_source=source_path)
    
    # 워크플로우 실행
    logger.info(f"워크플로우 실행 시작: {source_path}")
    try:
        final_state = workflow.invoke(initial_state)
        logger.info(f"워크플로우 실행 완료: {source_path}")
        
        # 에러 확인 (AddableValuesDict에서 error_message 속성 접근 방식 수정)
        error_message = final_state.get("error_message") if hasattr(final_state, "get") else None
        
        # 결과 반환
        return {
            "success": error_message is None,
            "error": error_message,
            "results": final_state.get("total_results") if hasattr(final_state, "get") else None
        }
        
    except Exception as e:
        logger.error(f"워크플로우 실행 중 예외 발생: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "results": None
        } 