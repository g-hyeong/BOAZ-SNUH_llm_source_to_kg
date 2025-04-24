"""
멀티 에이전트 LLM 관리 모듈
- LangChain과 LangGraph를 활용한 에이전트 구성
- 에이전트 간 작업 조율 및 상태 관리
- 프롬프트 생성 및 응답 처리
"""

import os
import time
import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
import llm_interface
from langgraph.graph import StateGraph

# 프롬프트 모듈 임포트
from prompts import set_manager_agent_prompt, set_drug_agent_prompt, set_diagnosis_agent_prompt


class AgentState(TypedDict):
    """에이전트 상태 정의"""
    messages: List[BaseMessage]
    next_agent: Optional[str]
    results: Dict[str, Any]
    title: str  # 문서 제목
    contents: str  # 문서 내용
    manager_response: Optional[str]  # 매니저 에이전트의 응답
    chat_history: List[Dict[str, Any]]  # 채팅 기록 (메모리)


class BaseAgent:
    """기본 에이전트 클래스"""
    
    def __init__(self, logger, prompt_logger=None, response_logger=None, model_name="deepseek-r1:14b", temperature=0.1):
        """에이전트 초기화"""
        self.logger = logger
        self.prompt_logger = prompt_logger  # 프롬프트 로거 추가
        self.response_logger = response_logger  # 응답 로거 추가
        self.model_name = model_name
        self.temperature = temperature
    
    def create_prompt(self, state: AgentState) -> str:
        """상태를 바탕으로 프롬프트 생성"""
        raise NotImplementedError("Subclasses must implement create_prompt")
    
    def process(self, state: AgentState) -> AgentState:
        """상태를 받아 처리하고 업데이트된 상태 반환"""
        raise NotImplementedError("Subclasses must implement process")

    def call_llm(self, prompt: str, stop: Optional[List[str]] = None) -> Tuple[str, bool]:
        """LLM API 호출 및 응답 처리"""
        self.logger.info(f"LLM API 호출 시작: 모델={self.model_name}, 프롬프트 길이={len(prompt)}")
        start_time = time.time()
        
        # 프롬프트 로깅 (프롬프트 로거가 있는 경우)
        if self.prompt_logger:
            self.prompt_logger.info(f"[LLM 요청] 모델: {self.model_name}")
            self.prompt_logger.info(f"[LLM 요청] 프롬프트:\n{prompt}")
        else:
            self.logger.warning("프롬프트 로거가 없어 요청 내용을 기록할 수 없습니다.")
        
        try:
            # llm_interface.call_llm을 사용하여 LLM 호출
            response_content, success = llm_interface.call_llm(
                prompt=prompt,
                temperature=self.temperature,
                stop=stop
            )
            
            # 응답 처리 로직은 그대로 유지
            elapsed_time = time.time() - start_time
            self.logger.info(f"LLM API 호출 완료: 응답 길이={len(response_content)}, 소요 시간={elapsed_time:.2f}초")
            
            # 응답 로깅 (응답 로거가 있는 경우)
            if self.response_logger:
                self.response_logger.info(f"[LLM 응답] 모델: {self.model_name}")
                self.response_logger.info(f"[LLM 응답] 내용:\n{response_content}")
            else:
                self.logger.warning("응답 로거가 없어 응답 내용을 기록할 수 없습니다.")
            
            return response_content, success
            
        except Exception as e:
            error_message = f"LLM API 호출 중 오류 발생: {e}"
            self.logger.error(error_message)
            
            # 응답 로거가 있는 경우 오류도 기록
            if self.response_logger:
                self.response_logger.error(f"[LLM 오류] {error_message}")
            
            return f"오류: {str(e)}", False
    
    def extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """LLM 응답에서 JSON 부분 추출"""
        try:
            # 먼저 응답이 이미 JSON 객체인지 확인
            if isinstance(response, dict):
                return response
                
            # JSON 형식 찾기 (마크다운 코드 블록 또는 일반 텍스트에서)
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```|(\{[\s\S]*\})', response)
            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else json_match.group(2)
                return json.loads(json_str)
            else:
                self.logger.error("응답에서 JSON 형식을 찾을 수 없음")
                return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 오류: {e}")
            return {}


class ManagerAgent(BaseAgent):
    """작업 관리 및 에이전트 선택을 담당하는 Manager 에이전트"""
    
    def create_prompt(self, state: AgentState) -> str:
        """Manager 에이전트용 프롬프트 생성"""
        title = state["title"]
        contents = state["contents"]
        
        # 채팅 기록을 프롬프트에 포함
        chat_history_context = ""
        if "chat_history" in state and state["chat_history"]:
            chat_history_context = "\n\n## Previous Analysis:\n"
            for entry in state["chat_history"]:
                if "agent" in entry and "summary" in entry:
                    chat_history_context += f"- {entry['agent']}: {entry['summary']}\n"
        
        # 기본 프롬프트 가져오기
        prompt = set_manager_agent_prompt(title, contents)
        
        # 채팅 기록이 있으면 추가
        if chat_history_context:
            # 기존 텍스트와 Guideline Text 섹션 사이에 채팅 기록 컨텍스트 삽입
            prompt_parts = prompt.split("## Guideline Text (ANALYZE THE ENTIRE TEXT):")
            if len(prompt_parts) == 2:
                prompt = prompt_parts[0] + chat_history_context + "\n## Guideline Text (ANALYZE THE ENTIRE TEXT):" + prompt_parts[1]
        
        return prompt
    
    def process(self, state: AgentState) -> AgentState:
        """상태를 받아 처리하고 다음 에이전트 결정"""
        # 프롬프트 생성
        prompt = self.create_prompt(state)
        
        # 특정 지시를 강조하기 위한 중지 토큰
        stop_tokens = ["IMPORTANT:", "ROLE:", "##", "```"]
        
        # LLM 호출
        response, success = self.call_llm(prompt, stop=stop_tokens)
        
        if not success:
            self.logger.error("Manager 에이전트 처리 중 오류 발생")
            state["next_agent"] = "end"
            state["messages"].append(AIMessage(content="에이전트 처리 중 오류가 발생했습니다."))
            return state
        
        # 응답에서 JSON 파싱
        analysis_result = self.extract_json_from_response(response)
        
        # 결과 없으면 종료
        if not analysis_result:
            self.logger.error("Manager 에이전트에서 유효한 JSON 응답을 받지 못함")
            state["next_agent"] = "end"
            state["messages"].append(AIMessage(content="응답 처리 중 오류가 발생했습니다."))
            return state
        
        # 결과 저장
        state["results"]["manager_analysis"] = analysis_result
        
        # 다음 에이전트 선택을 위한 처리 - 새로운 형식에 맞게 수정
        # 프롬프트 형식이 변경되어 agent_selection이 아닌 proposed_cohort_analyses에 에이전트 정보가 포함됨
        if "proposed_cohort_analyses" in analysis_result:
            cohort_analyses = analysis_result["proposed_cohort_analyses"]
            
            # cohort_analyses가 리스트인지 확인하고 처리
            if isinstance(cohort_analyses, list) and cohort_analyses:
                # 선택된 에이전트 정보 추출 및 정리
                agent_selections = []
                processed_cohorts = {}  # 이미 처리된 코호트 분석 추적
                
                for analysis in cohort_analyses:
                    if "selected_agent" in analysis and "name" in analysis:
                        cohort_name = analysis["name"]
                        agent_type = analysis["selected_agent"]
                        
                        # 각 코호트 분석에서 선택된 에이전트 정보를 추출하여 저장
                        # 각 코호트 분석마다 개별적으로 처리될 수 있도록 코호트 이름도 저장
                        agent_entry = {
                            "selected_agent": agent_type,
                            "rationale": analysis.get("rationale", "No rationale provided"),
                            "cohort_name": cohort_name,
                            "description": analysis.get("description", ""),
                            "relevance": analysis.get("relevance", ""),
                            "queued_at": time.time()
                        }
                        
                        # 이미 동일한 에이전트-코호트 조합이 있는지 확인
                        if f"{agent_type}:{cohort_name}" not in processed_cohorts:
                            processed_cohorts[f"{agent_type}:{cohort_name}"] = True
                            agent_selections.append(agent_entry)
                
                # 선택된 에이전트가 있는지 확인
                if agent_selections:
                    # agent_selection 필드 추가 (이전 형식 호환성 유지)
                    analysis_result["agent_selection"] = agent_selections
                    
                    # 첫 번째 에이전트를 다음에 실행할 에이전트로 설정
                    state["next_agent"] = agent_selections[0]["selected_agent"]
                    state["current_cohort"] = agent_selections[0]["cohort_name"]  # 현재 처리 중인 코호트 이름 저장
                    
                    # 나머지 에이전트 목록을 저장 (순차적 실행을 위함)
                    state["pending_agents"] = []
                    state["pending_cohorts"] = []
                    for i in range(1, len(agent_selections)):
                        state["pending_agents"].append(agent_selections[i]["selected_agent"])
                        state["pending_cohorts"].append(agent_selections[i]["cohort_name"])
                    
                    # 실행 계획 로깅
                    total_cohorts = len(agent_selections)
                    pending_cohorts = len(state["pending_agents"])
                    
                    self.logger.info(f"다음 에이전트: {state['next_agent']} (코호트: {state['current_cohort']}), 총 코호트 수: {total_cohorts}, 대기 중인 코호트: {pending_cohorts}개")
                    
                    # 코호트별 실행 계획 상세 로깅
                    for i, agent_info in enumerate(agent_selections):
                        status = "다음 실행" if i == 0 else f"대기 중 ({i}번째)"
                        self.logger.info(f"코호트 '{agent_info['cohort_name']}': {agent_info['selected_agent']} ({status})")
                else:
                    self.logger.error("선택된 에이전트 정보를 찾을 수 없음")
                    state["next_agent"] = "end"
            else:
                self.logger.error("코호트 분석 정보가 비어있거나 올바른 형식이 아님")
                state["next_agent"] = "end"
        else:
            self.logger.error("코호트 분석 정보를 찾을 수 없음")
            state["next_agent"] = "end"
        
        # 매니저 응답 저장 (다음 에이전트에서 사용)
        state["manager_response"] = response
        
        # 채팅 기록에 추가
        if "chat_history" not in state:
            state["chat_history"] = []
        
        # 요약 생성
        summary = "분석 완료 및 다음 에이전트 선택"
        if "summarized_text" in analysis_result:
            summary = analysis_result["summarized_text"][:200] + "..." if len(analysis_result["summarized_text"]) > 200 else analysis_result["summarized_text"]
        
        # 처리 정보
        cohort_count = len(cohort_analyses) if "proposed_cohort_analyses" in analysis_result and isinstance(cohort_analyses, list) else 0
        entity_count = len(analysis_result.get("entities", []))
        relation_count = len(analysis_result.get("relations", []))
        
        state["chat_history"].append({
            "agent": "manager",
            "timestamp": time.time(),
            "action": "분석 및 에이전트 선택",
            "summary": summary,
            "next_agent": state["next_agent"],
            "current_cohort": state.get("current_cohort", ""),
            "pending_agents": state.get("pending_agents", []),
            "pending_cohorts": state.get("pending_cohorts", []),
            "stats": {
                "cohort_count": cohort_count,
                "entity_count": entity_count,
                "relation_count": relation_count
            }
        })
        
        # 메시지 추가
        agent_name = "약물 에이전트" if state["next_agent"] == "drug_agent" else "진단 에이전트" if state["next_agent"] == "diagnosis_agent" else "종료"
        cohort_info = f" (코호트: {state.get('current_cohort', '알 수 없음')})"
        pending_info = ""
        if state.get("pending_agents"):
            pending_count = len(state["pending_agents"])
            pending_info = f" (추가로 {pending_count}개 코호트 분석이 대기 중입니다)"
        
        ai_message = AIMessage(content=f"분석 완료: 다음 작업은 {agent_name}{cohort_info}에게 전달됩니다{pending_info}.")
        state["messages"].append(ai_message)
        
        self.logger.info(f"Manager 에이전트 처리 완료: 다음 에이전트={state['next_agent']}, 코호트={state.get('current_cohort', '없음')}")
        
        return state


class DrugAgent(BaseAgent):
    """약물 관련 분석 및 처리를 담당하는 Drug 에이전트"""
    
    def create_prompt(self, state: AgentState) -> str:
        """Drug 에이전트용 프롬프트 생성"""
        manager_response = state["manager_response"]
        title = state["title"]
        contents = state["contents"]
        
        # 채팅 기록을 프롬프트에 포함
        chat_history_context = ""
        if "chat_history" in state and state["chat_history"]:
            chat_history_context = "\n\n## Previous Analysis Context:\n"
            for entry in state["chat_history"]:
                if entry["agent"] == "manager":
                    chat_history_context += f"- Manager selected drug_agent because: {entry.get('summary', 'No summary available')}\n"
        
        # 현재 코호트 정보 추가
        current_cohort = state.get("current_cohort", "Unknown cohort")
        chat_history_context += f"\n## Current Analysis Focus:\n- Target cohort: {current_cohort}\n"
        
        # 원본 문서 정보 추가
        document_context = f"\n\n## Original Document Title:\n{title}\n\n## Original Document Content:\n{contents}..."
        
        # 기본 프롬프트 가져오기
        prompt = set_drug_agent_prompt(manager_response)
        
        # 채팅 기록과 원본 문서 내용을 추가
        # 분석 요구사항 섹션 앞에 컨텍스트 삽입
        prompt_parts = prompt.split("## Analysis Requirements:")
        if len(prompt_parts) == 2:
            prompt = prompt_parts[0] + chat_history_context + document_context + "\n## Analysis Requirements:" + prompt_parts[1]
        
        return prompt
    
    def process(self, state: AgentState) -> AgentState:
        """약물 관련 상태 처리"""
        # 프롬프트 생성
        prompt = self.create_prompt(state)
        
        # 현재 처리 중인 코호트 이름 가져오기
        current_cohort = state.get("current_cohort", "Unknown cohort")
        
        # 특정 지시를 강조하기 위한 중지 토큰
        stop_tokens = ["IMPORTANT:", "ROLE:", "##", "```"]
        
        # LLM 호출
        response, success = self.call_llm(prompt, stop=stop_tokens)
        
        if not success:
            self.logger.error(f"Drug 에이전트 처리 중 오류 발생 (코호트: {current_cohort})")
            state["next_agent"] = "end"
            state["messages"].append(AIMessage(content=f"약물 에이전트 처리 중 오류가 발생했습니다. (코호트: {current_cohort})"))
            return state
        
        # 응답에서 JSON 파싱
        drug_analysis = self.extract_json_from_response(response)
        
        # 결과 없으면 종료
        if not drug_analysis:
            self.logger.error(f"Drug 에이전트에서 유효한 JSON 응답을 받지 못함 (코호트: {current_cohort})")
            state["next_agent"] = "end"
            state["messages"].append(AIMessage(content=f"응답 처리 중 오류가 발생했습니다. (코호트: {current_cohort})"))
            return state
        
        # 결과에 현재 코호트 정보 추가
        drug_analysis["cohort_name"] = current_cohort
        drug_analysis["processed_timestamp"] = time.time()
        
        # 결과 저장 - 현재 코호트 정보를 키로 사용
        if "drug_analyses" not in state["results"]:
            state["results"]["drug_analyses"] = {}
        state["results"]["drug_analyses"][current_cohort] = drug_analysis
        
        # 이전 버전과의 호환성을 위해 drug_analysis도 유지
        state["results"]["drug_analysis"] = drug_analysis
        
        # 다음 에이전트 설정 (대기 중인 에이전트가 있으면 가져오고, 아니면 종료)
        if "pending_agents" in state and state["pending_agents"] and "pending_cohorts" in state and state["pending_cohorts"]:
            # 대기 중인 첫 번째 에이전트를 다음 에이전트로 설정
            state["next_agent"] = state["pending_agents"].pop(0)
            state["current_cohort"] = state["pending_cohorts"].pop(0)
            
            # 남은 대기 에이전트 수 계산
            remaining = len(state["pending_agents"])
            remaining_info = f"남은 대기 에이전트: {remaining}"
            
            self.logger.info(f"약물 에이전트 처리 완료 (코호트: {current_cohort}), 다음 에이전트: {state['next_agent']} (코호트: {state['current_cohort']}), {remaining_info}")
        else:
            # 대기 중인 에이전트가 없으면 종료
            state["next_agent"] = "end"
            state["current_cohort"] = ""
            self.logger.info(f"약물 에이전트 처리 완료 (코호트: {current_cohort}), 다음 에이전트 없음")
        
        # 채팅 기록에 추가
        summary = f"약물 관련 분석 완료 (코호트: {current_cohort})"
        if "detailed_analysis" in drug_analysis:
            summary = drug_analysis["detailed_analysis"][:200] + "..." if len(drug_analysis["detailed_analysis"]) > 200 else drug_analysis["detailed_analysis"]
        
        state["chat_history"].append({
            "agent": "drug_agent",
            "timestamp": time.time(),
            "action": f"약물 분석 (코호트: {current_cohort})",
            "summary": summary,
            "next_agent": state["next_agent"],
            "current_cohort": state.get("current_cohort", ""),
            "pending_agents": state.get("pending_agents", []),
            "pending_cohorts": state.get("pending_cohorts", [])
        })
        
        # 메시지 추가
        agent_info = ""
        if state["next_agent"] != "end":
            next_agent_name = "약물 에이전트" if state["next_agent"] == "drug_agent" else "진단 에이전트" if state["next_agent"] == "diagnosis_agent" else "알 수 없는 에이전트"
            cohort_info = f" (코호트: {state.get('current_cohort', '알 수 없음')})"
            pending_info = ""
            if "pending_agents" in state and state["pending_agents"]:
                pending_info = f", 추가로 {len(state['pending_agents'])}개 코호트 분석이 대기 중"
            agent_info = f" 다음 작업은 {next_agent_name}{cohort_info}에게 전달됩니다{pending_info}."
        
        ai_message = AIMessage(content=f"약물 관련 분석이 완료되었습니다 (코호트: {current_cohort}).{agent_info}")
        state["messages"].append(ai_message)
        
        self.logger.info(f"Drug 에이전트 처리 완료 (코호트: {current_cohort})")
        
        return state


class DiagnosisAgent(BaseAgent):
    """진단 관련 분석 및 처리를 담당하는 Diagnosis 에이전트"""
    
    def create_prompt(self, state: AgentState) -> str:
        """Diagnosis 에이전트용 프롬프트 생성"""
        manager_response = state["manager_response"]
        title = state["title"]
        contents = state["contents"]
        
        # 채팅 기록을 프롬프트에 포함
        chat_history_context = ""
        if "chat_history" in state and state["chat_history"]:
            chat_history_context = "\n\n## Previous Analysis Context:\n"
            for entry in state["chat_history"]:
                if entry["agent"] == "manager":
                    chat_history_context += f"- Manager selected diagnosis_agent because: {entry.get('summary', 'No summary available')}\n"
        
        # 현재 코호트 정보 추가
        current_cohort = state.get("current_cohort", "Unknown cohort")
        chat_history_context += f"\n## Current Analysis Focus:\n- Target cohort: {current_cohort}\n"
        
        # 원본 문서 정보 추가
        document_context = f"\n\n## Original Document Title:\n{title}\n\n## Original Document Content:\n{contents}..."
        
        # 기본 프롬프트 가져오기
        prompt = set_diagnosis_agent_prompt(manager_response)
        
        # 채팅 기록과 원본 문서 내용을 추가
        # 분석 요구사항 섹션 앞에 컨텍스트 삽입
        prompt_parts = prompt.split("## Analysis Requirements:")
        if len(prompt_parts) == 2:
            prompt = prompt_parts[0] + chat_history_context + document_context + "\n## Analysis Requirements:" + prompt_parts[1]
        
        return prompt
    
    def process(self, state: AgentState) -> AgentState:
        """진단 관련 상태 처리"""
        # 프롬프트 생성
        prompt = self.create_prompt(state)
        
        # 현재 처리 중인 코호트 이름 가져오기
        current_cohort = state.get("current_cohort", "Unknown cohort")
        
        # 특정 지시를 강조하기 위한 중지 토큰
        stop_tokens = ["IMPORTANT:", "ROLE:", "##", "```"]
        
        # LLM 호출
        response, success = self.call_llm(prompt, stop=stop_tokens)
        
        if not success:
            self.logger.error(f"Diagnosis 에이전트 처리 중 오류 발생 (코호트: {current_cohort})")
            state["next_agent"] = "end"
            state["messages"].append(AIMessage(content=f"진단 에이전트 처리 중 오류가 발생했습니다. (코호트: {current_cohort})"))
            return state
        
        # 응답에서 JSON 파싱
        diagnosis_analysis = self.extract_json_from_response(response)
        
        # 결과 없으면 종료
        if not diagnosis_analysis:
            self.logger.error(f"Diagnosis 에이전트에서 유효한 JSON 응답을 받지 못함 (코호트: {current_cohort})")
            state["next_agent"] = "end"
            state["messages"].append(AIMessage(content=f"응답 처리 중 오류가 발생했습니다. (코호트: {current_cohort})"))
            return state
        
        # 결과에 현재 코호트 정보 추가
        diagnosis_analysis["cohort_name"] = current_cohort
        diagnosis_analysis["processed_timestamp"] = time.time()
        
        # 결과 저장 - 현재 코호트 정보를 키로 사용
        if "diagnosis_analyses" not in state["results"]:
            state["results"]["diagnosis_analyses"] = {}
        state["results"]["diagnosis_analyses"][current_cohort] = diagnosis_analysis
        
        # 이전 버전과의 호환성을 위해 diagnosis_analysis도 유지
        state["results"]["diagnosis_analysis"] = diagnosis_analysis
        
        # 다음 에이전트 설정 (대기 중인 에이전트가 있으면 가져오고, 아니면 종료)
        if "pending_agents" in state and state["pending_agents"] and "pending_cohorts" in state and state["pending_cohorts"]:
            # 대기 중인 첫 번째 에이전트를 다음 에이전트로 설정
            state["next_agent"] = state["pending_agents"].pop(0)
            state["current_cohort"] = state["pending_cohorts"].pop(0)
            
            # 남은 대기 에이전트 수 계산
            remaining = len(state["pending_agents"])
            remaining_info = f"남은 대기 에이전트: {remaining}"
            
            self.logger.info(f"진단 에이전트 처리 완료 (코호트: {current_cohort}), 다음 에이전트: {state['next_agent']} (코호트: {state['current_cohort']}), {remaining_info}")
        else:
            # 대기 중인 에이전트가 없으면 종료
            state["next_agent"] = "end"
            state["current_cohort"] = ""
            self.logger.info(f"진단 에이전트 처리 완료 (코호트: {current_cohort}), 다음 에이전트 없음")
        
        # 채팅 기록에 추가
        summary = f"진단 관련 분석 완료 (코호트: {current_cohort})"
        if "detailed_analysis" in diagnosis_analysis:
            summary = diagnosis_analysis["detailed_analysis"][:200] + "..." if len(diagnosis_analysis["detailed_analysis"]) > 200 else diagnosis_analysis["detailed_analysis"]
        
        state["chat_history"].append({
            "agent": "diagnosis_agent",
            "timestamp": time.time(),
            "action": f"진단 분석 (코호트: {current_cohort})",
            "summary": summary,
            "next_agent": state["next_agent"],
            "current_cohort": state.get("current_cohort", ""),
            "pending_agents": state.get("pending_agents", []),
            "pending_cohorts": state.get("pending_cohorts", [])
        })
        
        # 메시지 추가
        agent_info = ""
        if state["next_agent"] != "end":
            next_agent_name = "약물 에이전트" if state["next_agent"] == "drug_agent" else "진단 에이전트" if state["next_agent"] == "diagnosis_agent" else "알 수 없는 에이전트"
            cohort_info = f" (코호트: {state.get('current_cohort', '알 수 없음')})"
            pending_info = ""
            if "pending_agents" in state and state["pending_agents"]:
                pending_info = f", 추가로 {len(state['pending_agents'])}개 코호트 분석이 대기 중"
            agent_info = f" 다음 작업은 {next_agent_name}{cohort_info}에게 전달됩니다{pending_info}."
        
        ai_message = AIMessage(content=f"진단 관련 분석이 완료되었습니다 (코호트: {current_cohort}).{agent_info}")
        state["messages"].append(ai_message)
        
        self.logger.info(f"Diagnosis 에이전트 처리 완료 (코호트: {current_cohort})")
        
        return state


class MultiAgentSystem:
    """멀티 에이전트 시스템 관리 클래스"""
    
    def __init__(self, logger, prompt_logger=None, response_logger=None, model_name="deepseek-r1:14b"):
        """멀티 에이전트 시스템 초기화"""
        self.logger = logger
        
        # 프롬프트 로거와 응답 로거 설정
        self.prompt_logger = prompt_logger
        self.response_logger = response_logger
        
        # 로그 설정 정보 출력
        self.logger.info(f"멀티 에이전트 시스템 초기화: 모델={model_name}")
        self.logger.info(f"로거 설정: 메인={logger is not None}, 프롬프트={prompt_logger is not None}, 응답={response_logger is not None}")
        
        self.model_name = model_name
        
        # 에이전트 초기화 (로거 직접 전달)
        self.manager_agent = ManagerAgent(
            logger=logger,
            prompt_logger=prompt_logger,  # 명시적으로 전달
            response_logger=response_logger,  # 명시적으로 전달
            model_name=model_name
        )
        self.drug_agent = DrugAgent(
            logger=logger,
            prompt_logger=prompt_logger,  # 명시적으로 전달
            response_logger=response_logger,  # 명시적으로 전달
            model_name=model_name
        )
        self.diagnosis_agent = DiagnosisAgent(
            logger=logger,
            prompt_logger=prompt_logger,  # 명시적으로 전달
            response_logger=response_logger,  # 명시적으로 전달
            model_name=model_name
        )
        
        # 그래프 생성
        self.graph = self._create_agent_graph()
    
    def _create_agent_graph(self) -> StateGraph:
        """에이전트 그래프 생성"""
        # 상태 타입 정의 및 그래프 초기화
        workflow = StateGraph(AgentState)
        
        # 노드 추가
        workflow.add_node("manager", self.manager_agent.process)
        workflow.add_node("drug_agent", self.drug_agent.process)
        workflow.add_node("diagnosis_agent", self.diagnosis_agent.process)
        
        # 종료 노드 추가
        def end_processing(state: AgentState) -> AgentState:
            """워크플로우 종료 처리"""
            self.logger.info("워크플로우 종료")
            return state
        
        workflow.add_node("end", end_processing)
        
        # 라우팅 조건 함수 정의
        def router(state: AgentState):
            return state["next_agent"]
        
        # 엣지 및 라우팅 로직 설정
        workflow.add_conditional_edges(
            "manager",
            router,
            {
                "drug_agent": "drug_agent",
                "diagnosis_agent": "diagnosis_agent",
                "end": "end"
            }
        )
        workflow.add_conditional_edges(
            "drug_agent", 
            router,
            {
                "drug_agent": "drug_agent",        # 대기 중인 에이전트가 drug_agent인 경우
                "diagnosis_agent": "diagnosis_agent",  # 대기 중인 에이전트가 diagnosis_agent인 경우
                "end": "end"
            }
        )
        workflow.add_conditional_edges(
            "diagnosis_agent", 
            router,
            {
                "drug_agent": "drug_agent",        # 대기 중인 에이전트가 drug_agent인 경우
                "diagnosis_agent": "diagnosis_agent",  # 대기 중인 에이전트가 diagnosis_agent인 경우
                "end": "end"
            }
        )
        
        # 시작 노드 설정
        workflow.set_entry_point("manager")
        
        return workflow.compile()
    
    def process_document(self, title: str, contents: str) -> Dict[str, Any]:
        """문서 처리 및 멀티 에이전트 시스템 실행"""
        initial_state = {
            "messages": [HumanMessage(content=f"다음 문서를 분석해주세요: {title}")],
            "next_agent": "manager",
            "results": {},
            "title": title,
            "contents": contents,
            "manager_response": None,
            "chat_history": []  # 채팅 기록 초기화
        }
        
        # 처리 시작 로그
        self.logger.info(f"문서 처리 시작: 제목={title}, 내용 길이={len(contents)}")
        start_time = time.time()
        
        try:
            # 그래프 실행
            result = self.graph.invoke(initial_state)
            
            # 처리 완료 로그
            elapsed_time = time.time() - start_time
            self.logger.info(f"문서 처리 완료: 소요 시간={elapsed_time:.2f}초")
            
            return result
        except Exception as e:
            self.logger.error(f"문서 처리 중 오류 발생: {e}")
            return {
                "messages": [
                    HumanMessage(content=f"다음 문서를 분석해주세요: {title}"), 
                    AIMessage(content=f"오류 발생: {str(e)}")
                ],
                "next_agent": "end",
                "results": {"error": str(e)},
                "title": title,
                "contents": contents,
                "manager_response": None,
                "chat_history": []
            }
    
    def extract_kg_and_cohort_analysis(self, title: str, contents: str) -> Dict[str, Any]:
        """문서로부터 지식 그래프 구성 요소와 코호트 분석 추출"""
        result = self.process_document(title, str(contents))
        
        # 현재 시간을 ISO 형식으로 변환
        import datetime
        current_time = datetime.datetime.now()
        iso_timestamp = current_time.isoformat()
        file_timestamp = current_time.strftime("%Y%m%d_%H%M%S")  # 파일명용 타임스탬프
        
        # 결과 요약 및 정리
        final_result = {
            "knowledge_graph": {
                "entities": [],
                "relations": []
            },
            "cohort_analysis": [],
            "summarized_text": "",
            "processing_history": [],  # 처리 이력 추가
            "selected_agents": [],     # 선택된 에이전트 목록 추가
            "cohort_results": {},      # 코호트별 분석 결과 저장
            "detailed_results": {},    # 상세 분석 결과를 저장할 필드 추가
            "processing_timestamp": iso_timestamp,  # 타임스탬프를 ISO 형식으로 저장
            "file_timestamp": file_timestamp,  # 파일명용 타임스탬프 (YYYYMMDD_HHMMSS)
            "document_info": {
                "title": title,
                "content_length": len(contents)
            }
        }
        
        # 채팅 기록 통합
        if "chat_history" in result:
            final_result["processing_history"] = result["chat_history"]
        
        # Manager 에이전트 결과 통합
        if "manager_analysis" in result["results"]:
            manager_analysis = result["results"]["manager_analysis"]
            
            # 엔티티와 관계 추출
            if "entities" in manager_analysis:
                final_result["knowledge_graph"]["entities"] = manager_analysis["entities"]
            if "relations" in manager_analysis:
                final_result["knowledge_graph"]["relations"] = manager_analysis["relations"]
            
            # 요약 텍스트
            if "summarized_text" in manager_analysis:
                final_result["summarized_text"] = manager_analysis["summarized_text"]
            
            # 코호트 분석 정보 추출 (새로운 형식에 맞게 수정)
            if "proposed_cohort_analyses" in manager_analysis:
                cohort_analyses = manager_analysis["proposed_cohort_analyses"]
                if isinstance(cohort_analyses, list):
                    # 코호트 분석 정보 저장
                    final_result["cohort_analysis"] = cohort_analyses
                    
                    # 선택된 에이전트 정보 추출 및 코호트별 결과 초기화
                    selected_agents = []
                    for analysis in cohort_analyses:
                        if "selected_agent" in analysis and "name" in analysis:
                            agent = analysis["selected_agent"]
                            cohort_name = analysis["name"]
                            
                            # 코호트별 결과 딕셔너리 초기화
                            if cohort_name not in final_result["cohort_results"]:
                                final_result["cohort_results"][cohort_name] = {
                                    "selected_agent": agent,
                                    "description": analysis.get("description", ""),
                                    "rationale": analysis.get("rationale", ""),
                                    "results": {}
                                }
                            
                            if agent not in selected_agents:
                                selected_agents.append(agent)
                    
                    final_result["selected_agents"] = selected_agents
            
            # 에이전트 선택 정보 (이전 형식 호환성을 위해 유지)
            if "agent_selection" in manager_analysis:
                agent_selections = manager_analysis["agent_selection"]
                if isinstance(agent_selections, list):
                    # 이미 선택된 에이전트 목록이 없는 경우에만 업데이트
                    if not final_result["selected_agents"]:
                        for agent in agent_selections:
                            if "selected_agent" in agent:
                                if agent["selected_agent"] not in final_result["selected_agents"]:
                                    final_result["selected_agents"].append(agent["selected_agent"])
        
        # Drug 에이전트 결과 통합 (실행된 경우)
        # 여러 코호트에 걸친 약물 에이전트 결과를 통합
        drug_entities_all = []
        drug_relationships_all = []
        
        # 개별 코호트의 약물 분석 결과가 있는 경우
        if "drug_analyses" in result["results"]:
            drug_analyses = result["results"]["drug_analyses"]
            
            for cohort_name, drug_analysis in drug_analyses.items():
                # 해당 코호트 결과에 약물 분석 결과 저장
                if cohort_name in final_result["cohort_results"]:
                    final_result["cohort_results"][cohort_name]["results"]["drug_analysis"] = drug_analysis
                
                # 약물 코호트 정보 추가
                if "medication_cohorts" in drug_analysis:
                    if "drug_cohorts" not in final_result:
                        final_result["drug_cohorts"] = []
                    final_result["drug_cohorts"].extend(drug_analysis["medication_cohorts"])
                
                # 약물 경로 정보 추가
                if "treatment_pathways" in drug_analysis:
                    if "treatment_pathways" not in final_result:
                        final_result["treatment_pathways"] = []
                    final_result["treatment_pathways"].extend(drug_analysis["treatment_pathways"])
                
                # 약물 엔티티와 관계 집계
                if "drug_entities" in drug_analysis and drug_analysis["drug_entities"]:
                    drug_entities_all.extend(drug_analysis["drug_entities"])
                
                if "drug_relationships" in drug_analysis and drug_analysis["drug_relationships"]:
                    drug_relationships_all.extend(drug_analysis["drug_relationships"])
            
            # 호환성을 위한 단일 drug_analysis 결과도 저장
            if "drug_analysis" in result["results"]:
                final_result["drug_analysis"] = result["results"]["drug_analysis"]
        
        # 레거시 지원 - 단일 Drug 에이전트 결과
        elif "drug_analysis" in result["results"]:
            drug_analysis = result["results"]["drug_analysis"]
            
            # 약물 코호트 정보 추가
            if "medication_cohorts" in drug_analysis:
                final_result["drug_cohorts"] = drug_analysis["medication_cohorts"]
            
            # 약물 경로 정보 추가
            if "treatment_pathways" in drug_analysis:
                final_result["treatment_pathways"] = drug_analysis["treatment_pathways"]
            
            # 약물 엔티티와 관계 집계
            if "drug_entities" in drug_analysis and drug_analysis["drug_entities"]:
                drug_entities_all.extend(drug_analysis["drug_entities"])
            
            if "drug_relationships" in drug_analysis and drug_analysis["drug_relationships"]:
                drug_relationships_all.extend(drug_analysis["drug_relationships"])
                
            # 레거시 필드 유지
            final_result["drug_analysis"] = drug_analysis
        
        # 집계된 약물 엔티티와 관계 처리
        if drug_entities_all:
            # 중복 제거 (concept_name 기준)
            seen_entities = set()
            unique_drug_entities = []
            
            for entity in drug_entities_all:
                if isinstance(entity, dict) and "concept_name" in entity:
                    entity_key = entity["concept_name"]
                    if entity_key not in seen_entities:
                        seen_entities.add(entity_key)
                        unique_drug_entities.append(entity)
            
            # 약물 엔티티 정보 추가
            final_result["drug_entities"] = unique_drug_entities
            
            # 지식 그래프에도 통합
            for entity in unique_drug_entities:
                if "id" in entity and not any(e.get("id") == entity["id"] for e in final_result["knowledge_graph"]["entities"]):
                    final_result["knowledge_graph"]["entities"].append(entity)
                elif "concept_name" in entity and not any(e.get("concept_name") == entity["concept_name"] for e in final_result["knowledge_graph"]["entities"]):
                    final_result["knowledge_graph"]["entities"].append(entity)
        
        if drug_relationships_all:
            # 중복 제거 (source, target, relationship_type 기준)
            seen_relations = set()
            unique_drug_relations = []
            
            for relation in drug_relationships_all:
                if isinstance(relation, dict) and "source_drug" in relation and "target_entity" in relation:
                    relation_key = f"{relation['source_drug']}|{relation['target_entity']}|{relation.get('relationship_type', 'unknown')}"
                    if relation_key not in seen_relations:
                        seen_relations.add(relation_key)
                        unique_drug_relations.append(relation)
            
            # 약물 관계 정보 추가
            final_result["drug_relationships"] = unique_drug_relations
            
            # 지식 그래프에도 통합
            for relation in unique_drug_relations:
                if not any(
                    r.get("source") == relation.get("source_drug") and 
                    r.get("target") == relation.get("target_entity") and
                    r.get("name") == relation.get("relationship_type") 
                    for r in final_result["knowledge_graph"]["relations"]
                ):
                    # 지식 그래프 형식으로 변환
                    kg_relation = {
                        "source": relation.get("source_drug"),
                        "target": relation.get("target_entity"),
                        "name": relation.get("relationship_type", "unknown"),
                        "evidence": relation.get("evidence", relation.get("details", "")),
                        "certainty": relation.get("certainty", "unknown")
                    }
                    final_result["knowledge_graph"]["relations"].append(kg_relation)
        
        # Diagnosis 에이전트 결과 통합 (실행된 경우)
        # 여러 코호트에 걸친 진단 에이전트 결과를 통합
        condition_entities_all = []
        condition_relationships_all = []
        
        # 개별 코호트의 진단 분석 결과가 있는 경우
        if "diagnosis_analyses" in result["results"]:
            diagnosis_analyses = result["results"]["diagnosis_analyses"]
            
            for cohort_name, diagnosis_analysis in diagnosis_analyses.items():
                # 해당 코호트 결과에 진단 분석 결과 저장
                if cohort_name in final_result["cohort_results"]:
                    final_result["cohort_results"][cohort_name]["results"]["diagnosis_analysis"] = diagnosis_analysis
                
                # 질환 코호트 정보 추가
                if "condition_cohorts" in diagnosis_analysis:
                    if "condition_cohorts" not in final_result:
                        final_result["condition_cohorts"] = []
                    final_result["condition_cohorts"].extend(diagnosis_analysis["condition_cohorts"])
                
                # 진단 경로 정보 추가
                if "diagnostic_pathways" in diagnosis_analysis:
                    if "diagnostic_pathways" not in final_result:
                        final_result["diagnostic_pathways"] = []
                    final_result["diagnostic_pathways"].extend(diagnosis_analysis["diagnostic_pathways"])
                
                # 진단 엔티티와 관계 집계
                if "condition_entities" in diagnosis_analysis and diagnosis_analysis["condition_entities"]:
                    condition_entities_all.extend(diagnosis_analysis["condition_entities"])
                
                if "condition_relationships" in diagnosis_analysis and diagnosis_analysis["condition_relationships"]:
                    condition_relationships_all.extend(diagnosis_analysis["condition_relationships"])
            
            # 호환성을 위한 단일 diagnosis_analysis 결과도 저장
            if "diagnosis_analysis" in result["results"]:
                final_result["diagnosis_analysis"] = result["results"]["diagnosis_analysis"]
        
        # 레거시 지원 - 단일 Diagnosis 에이전트 결과
        elif "diagnosis_analysis" in result["results"]:
            diagnosis_analysis = result["results"]["diagnosis_analysis"]
            
            # 질환 코호트 정보 추가
            if "condition_cohorts" in diagnosis_analysis:
                final_result["condition_cohorts"] = diagnosis_analysis["condition_cohorts"]
            
            # 진단 경로 정보 추가
            if "diagnostic_pathways" in diagnosis_analysis:
                final_result["diagnostic_pathways"] = diagnosis_analysis["diagnostic_pathways"]
            
            # 진단 엔티티와 관계 집계
            if "condition_entities" in diagnosis_analysis and diagnosis_analysis["condition_entities"]:
                condition_entities_all.extend(diagnosis_analysis["condition_entities"])
            
            if "condition_relationships" in diagnosis_analysis and diagnosis_analysis["condition_relationships"]:
                condition_relationships_all.extend(diagnosis_analysis["condition_relationships"])
                
            # 레거시 필드 유지
            final_result["diagnosis_analysis"] = diagnosis_analysis
        
        # 집계된 진단 엔티티와 관계 처리
        if condition_entities_all:
            # 중복 제거 (concept_name 기준)
            seen_entities = set()
            unique_condition_entities = []
            
            for entity in condition_entities_all:
                if isinstance(entity, dict) and "concept_name" in entity:
                    entity_key = entity["concept_name"]
                    if entity_key not in seen_entities:
                        seen_entities.add(entity_key)
                        unique_condition_entities.append(entity)
            
            # 질환 엔티티 정보 추가
            final_result["condition_entities"] = unique_condition_entities
            
            # 지식 그래프에도 통합
            for entity in unique_condition_entities:
                if "id" in entity and not any(e.get("id") == entity["id"] for e in final_result["knowledge_graph"]["entities"]):
                    final_result["knowledge_graph"]["entities"].append(entity)
                elif "concept_name" in entity and not any(e.get("concept_name") == entity["concept_name"] for e in final_result["knowledge_graph"]["entities"]):
                    final_result["knowledge_graph"]["entities"].append(entity)
        
        if condition_relationships_all:
            # 중복 제거 (source, target, relationship_type 기준)
            seen_relations = set()
            unique_condition_relations = []
            
            for relation in condition_relationships_all:
                if isinstance(relation, dict) and "source_condition" in relation and "target_entity" in relation:
                    relation_key = f"{relation['source_condition']}|{relation['target_entity']}|{relation.get('relationship_type', 'unknown')}"
                    if relation_key not in seen_relations:
                        seen_relations.add(relation_key)
                        unique_condition_relations.append(relation)
            
            # 질환 관계 정보 추가
            final_result["condition_relationships"] = unique_condition_relations
            
            # 지식 그래프에도 통합
            for relation in unique_condition_relations:
                if not any(
                    r.get("source") == relation.get("source_condition") and 
                    r.get("target") == relation.get("target_entity") and
                    r.get("name") == relation.get("relationship_type") 
                    for r in final_result["knowledge_graph"]["relations"]
                ):
                    # 지식 그래프 형식으로 변환
                    kg_relation = {
                        "source": relation.get("source_condition"),
                        "target": relation.get("target_entity"),
                        "name": relation.get("relationship_type", "unknown"),
                        "evidence": relation.get("evidence", relation.get("details", "")),
                        "certainty": relation.get("certainty", "unknown")
                    }
                    final_result["knowledge_graph"]["relations"].append(kg_relation)
        
        # 상세 결과 정보 구성 - 모든 최종 결과를 detailed_results에 복제
        final_result["detailed_results"] = {
            "knowledge_graph": final_result["knowledge_graph"].copy(),
            "cohort_analysis": final_result["cohort_analysis"].copy(),
            "summarized_text": final_result["summarized_text"],
            "processing_history": final_result["processing_history"].copy(),
            "selected_agents": final_result["selected_agents"].copy(),
            "cohort_results": final_result["cohort_results"].copy()
        }
        
        # 약물 관련 결과가 있으면 detailed_results에 추가
        if "drug_entities" in final_result:
            final_result["detailed_results"]["drug_entities"] = final_result["drug_entities"].copy()
        if "drug_relationships" in final_result:
            final_result["detailed_results"]["drug_relationships"] = final_result["drug_relationships"].copy()
        if "drug_cohorts" in final_result:
            final_result["detailed_results"]["drug_cohorts"] = final_result["drug_cohorts"].copy() 
        if "treatment_pathways" in final_result:
            final_result["detailed_results"]["treatment_pathways"] = final_result["treatment_pathways"].copy()
        if "drug_analysis" in final_result:
            final_result["detailed_results"]["drug_analysis"] = final_result["drug_analysis"].copy()
            
        # 질환 관련 결과가 있으면 detailed_results에 추가
        if "condition_entities" in final_result:
            final_result["detailed_results"]["condition_entities"] = final_result["condition_entities"].copy()
        if "condition_relationships" in final_result:
            final_result["detailed_results"]["condition_relationships"] = final_result["condition_relationships"].copy()
        if "condition_cohorts" in final_result:
            final_result["detailed_results"]["condition_cohorts"] = final_result["condition_cohorts"].copy()
        if "diagnostic_pathways" in final_result:
            final_result["detailed_results"]["diagnostic_pathways"] = final_result["diagnostic_pathways"].copy()
        if "diagnosis_analysis" in final_result:
            final_result["detailed_results"]["diagnosis_analysis"] = final_result["diagnosis_analysis"].copy()
        
        # 결과 통계 수집
        cohort_count = len(final_result["cohort_results"])
        entity_count = len(final_result["knowledge_graph"]["entities"])
        relation_count = len(final_result["knowledge_graph"]["relations"])
        
        # 코호트 처리 결과 통계 추가
        cohort_stats = {}
        for cohort_name, cohort_data in final_result["cohort_results"].items():
            agent_type = cohort_data.get("selected_agent", "unknown")
            if agent_type not in cohort_stats:
                cohort_stats[agent_type] = 0
            cohort_stats[agent_type] += 1
        
        # 코호트 분석 결과의 수 확인 및 로그 출력
        self.logger.info(f"결과 처리 완료: 코호트 수={cohort_count}, 엔티티 수={entity_count}, 관계 수={relation_count}")
        
        # 통계 정보도 로깅
        agent_stats_str = ", ".join([f"{agent}={count}" for agent, count in cohort_stats.items()])
        self.logger.info(f"에이전트별 코호트 분석: {agent_stats_str}")
        
        # 요약 통계 정보를 결과에 포함
        final_result["stats"] = {
            "cohort_count": cohort_count,
            "entity_count": entity_count,
            "relation_count": relation_count,
            "agent_distribution": cohort_stats
        }
        
        return final_result