from logger import LoggerManager
from agents import MultiAgentSystem
import json
import re
import os

from prompts import *

class GuidelineProcessor:
    """가이드라인 처리 클래스"""
    
    def __init__(self, init_logger=True, model_id="deepseek"):
        """가이드라인 처리기 초기화"""
        # 모델 ID 저장
        self.model_id = model_id
        
        # 로거 초기화 여부 확인
        if init_logger:
            # 메인 로거만 초기화 (timestamp 생성 포함)
            self._initialize_main_logger()
        else:
            # 로거를 나중에 초기화할 때 필요한 최소 속성만 설정
            self.timestamp = None
            self.logger = None
            self.prompt_logger = None
            self.response_logger = None
            self.agent_system = None
        
        # 타겟 가이드라인 정보 초기화
        self.current_guideline = None

    def _initialize_main_logger(self, timestamp=None):
        """메인 로거만 초기화하는 함수"""
        # timestamp 지정 시 그 값 사용, 아니면 새로 생성
        self.logger_manager = LoggerManager(timestamp=timestamp)
        self.logger = self.logger_manager.get_logger()
        self.timestamp = self.logger_manager.get_timestamp()
        
        # LLM 로거는 가이드라인별로 나중에 초기화
        self.prompt_logger = None
        self.response_logger = None
        
        # 로거 설정 정보 출력
        model_display = self.model_id
        self.logger.info(f"로거 설정 완료: 메인={self.logger is not None}, 프롬프트={self.prompt_logger is not None}, 응답={self.response_logger is not None}")
        
        # 에이전트 시스템 초기화 - 아직 LLM 로거는 None으로 설정
        self.agent_system = MultiAgentSystem(
            logger=self.logger,
            prompt_logger=None,
            response_logger=None,
            model_name=self.model_id  # 전달된 모델 ID 사용
        )
    
    def initialize_guideline_loggers(self, target_guideline, timestamp=None):
        """특정 가이드라인용 LLM 로거 초기화"""
        # 타임스탬프가 없거나 메인 로거가 없는 경우 메인 로거 먼저 초기화
        if not self.logger or not self.timestamp:
            self._initialize_main_logger(timestamp)
            timestamp = self.timestamp
        elif timestamp is None:
            timestamp = self.timestamp
        
        # 현재 처리 중인 가이드라인 정보 저장
        self.current_guideline = target_guideline
        
        # 가이드라인별 LLM 로거 초기화
        guideline_logger_manager = LoggerManager(
            target_guideline=target_guideline, 
            timestamp=timestamp
        )
        
        # LLM 로거 설정
        self.prompt_logger = guideline_logger_manager.get_prompt_logger()
        self.response_logger = guideline_logger_manager.get_response_logger()
        
        # 로거 설정 확인
        if not self.prompt_logger:
            self.logger.error(f"프롬프트 로거를 가져오지 못했습니다: {target_guideline}")
        
        if not self.response_logger:
            self.logger.error(f"응답 로거를 가져오지 못했습니다: {target_guideline}")
        
        # 정상 설정된 경우 테스트 메시지 기록
        if self.prompt_logger:
            self.prompt_logger.info(f"===== 가이드라인 [{target_guideline}]에 대한 프롬프트 로거 초기화 완료 =====")
        
        if self.response_logger:
            self.response_logger.info(f"===== 가이드라인 [{target_guideline}]에 대한 응답 로거 초기화 완료 =====")
        
        # 에이전트 시스템이 이미 초기화되어 있으면 로거 업데이트
        if self.agent_system:
            # 기존 에이전트 시스템의 로거 참조 업데이트
            self.agent_system.prompt_logger = self.prompt_logger
            self.agent_system.response_logger = self.response_logger
            
            # 모델 이름도 업데이트 (현재 설정된 모델 ID 사용)
            self.agent_system.model_name = self.model_id
            
            # 직접 각 에이전트의 로거도 업데이트
            self.agent_system.manager_agent.prompt_logger = self.prompt_logger
            self.agent_system.manager_agent.response_logger = self.response_logger
            self.agent_system.manager_agent.model_name = self.model_id
            
            self.agent_system.drug_agent.prompt_logger = self.prompt_logger
            self.agent_system.drug_agent.response_logger = self.response_logger
            self.agent_system.drug_agent.model_name = self.model_id
            
            self.agent_system.diagnosis_agent.prompt_logger = self.prompt_logger
            self.agent_system.diagnosis_agent.response_logger = self.response_logger
            self.agent_system.diagnosis_agent.model_name = self.model_id
            
            # 업데이트 확인 로깅
            self.logger.info(f"에이전트 시스템의 로거 업데이트 완료: 프롬프트={self.prompt_logger is not None}, 응답={self.response_logger is not None}")
        else:
            self.logger.error("에이전트 시스템이 초기화되지 않았습니다")
        
        self.logger.info(f"가이드라인 [{target_guideline}]에 대한 LLM 로거 초기화 완료")
        
        return timestamp
    
    def init_logger(self, target_guideline=None, timestamp=None):
        """외부에서 호출할 수 있는 로거 초기화 함수"""
        # 메인 로거가 없는 경우 먼저 초기화
        if not self.logger:
            self._initialize_main_logger(timestamp)
            timestamp = self.timestamp
        
        # 타겟 가이드라인이 있으면 그에 맞는 LLM 로거 초기화
        if target_guideline:
            self.initialize_guideline_loggers(target_guideline, timestamp)
        
        return self.timestamp
    
    def run(self, guideline_path):
        """메인 실행 함수"""
        # 로거 초기화 확인
        if self.logger is None:
            self._initialize_main_logger()
        
        # 가이드라인 파일명에서 target_guideline 추출
        target_guideline = os.path.splitext(os.path.basename(guideline_path))[0]
        
        # 현재 처리 중인 가이드라인이 없거나 다른 가이드라인인 경우 LLM 로거 초기화
        if not self.current_guideline or self.current_guideline != target_guideline:
            self.initialize_guideline_loggers(target_guideline, self.timestamp)
        
        # 가이드라인 처리 시작 로깅
        self.logger.info(f"가이드라인 [{target_guideline}] 처리 시작")
        guideline_data = self.get_guideline_contents(guideline_path)
        
        # 멀티 에이전트 시스템을 사용하여 가이드라인에서 코호트 분석 데이터 추출
        agent_results = self.extract_from_guideline(guideline_data)
        self.logger.info(f"가이드라인 [{target_guideline}] 멀티 에이전트 처리 완료")
        
        # 지식 그래프와 코호트 분석 정보 추출
        knowledge_graph = agent_results.get('knowledge_graph', {})
        cohort_analysis = agent_results.get('cohort_analysis', [])
        
        # 로그 정보 기록
        self.logger.info(f"추출된 엔티티 수: {len(knowledge_graph.get('entities', []))}")
        self.logger.info(f"추출된 관계 수: {len(knowledge_graph.get('relations', []))}")
        self.logger.info(f"생성된 코호트 분석 수: {len(cohort_analysis)}")
        
        # 특정 에이전트 결과 정보 확인
        if 'drug_cohorts' in agent_results:
            self.logger.info(f"약물 코호트 수: {len(agent_results['drug_cohorts'])}")
        
        if 'condition_cohorts' in agent_results:
            self.logger.info(f"질환 코호트 수: {len(agent_results['condition_cohorts'])}")
        
        # 최종 결과 구성
        result = {
            "knowledge_graph": knowledge_graph,
            "cohort_analysis": cohort_analysis,
            "detailed_results": agent_results,  # 에이전트 시스템의 모든 결과 포함
            "processing_timestamp": self.timestamp
        }
        
        self.logger.info("가이드라인 처리 완료")
        return result

    def get_guideline_contents(self, guideline_path):
        """가이드라인 데이터 로드"""
        with open(guideline_path, 'r', encoding='utf-8') as f:
            guideline_data = json.load(f)
        
        return guideline_data
    
    def extract_from_guideline(self, guideline_data):
        """멀티 에이전트 시스템을 통해 가이드라인으로부터 지식 그래프와 코호트 분석 추출"""
        title = guideline_data['title']
        contents = guideline_data['contents']
        
        self.logger.info(f"가이드라인 처리 시작: {title}")
        
        # 멀티 에이전트 시스템을 사용하여 지식 그래프 및 코호트 분석 추출
        results = self.agent_system.extract_kg_and_cohort_analysis(title, contents)
        
        # 메인 로거에 결과 요약 정보 기록
        entity_count = len(results.get('knowledge_graph', {}).get('entities', []))
        relation_count = len(results.get('knowledge_graph', {}).get('relations', []))
        cohort_count = len(results.get('cohort_analysis', []))
        
        self.logger.info(f"가이드라인 멀티 에이전트 처리 완료. 엔티티: {entity_count}, 관계: {relation_count}, 코호트: {cohort_count}")
        
        return results
    
    def extract_json_from_markdown(self, text: str) -> str:
        """마크다운 텍스트에서 JSON 부분을 추출."""
        self.logger.info("마크다운에서 JSON 추출 시작")
        
        # <think> 태그 제거
        think_pattern = r'<think>[\s\S]*?</think>'
        text = re.sub(think_pattern, '', text)

        # 1. JSON 코드 블록 패턴 (```json ... ```)
        json_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        matches = re.findall(json_block_pattern, text)
        
        if matches:
            # 가장 긴 JSON 블록 찾기 (더 완전한 JSON일 가능성이 높음)
            longest_match = max(matches, key=len)
            self.logger.info(f"JSON 코드 블록 패턴 발견: {len(longest_match)} 자")
            
            # JSON 유효성 검사
            try:
                json_obj = json.loads(longest_match)
                return longest_match.strip()
            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON 코드 블록이 유효하지 않음: {e}")
                # 계속 진행하여 다른 방법 시도
        
        # 2. 전체 텍스트가 JSON인지 확인
        try:
            json.loads(text)
            self.logger.info("전체 텍스트가 유효한 JSON")
            return text
        except json.JSONDecodeError:
            # 3. 중괄호로 둘러싸인 가장 큰 블록 찾기
            bracket_pattern = r'(\{[\s\S]*\})'
            bracket_matches = re.findall(bracket_pattern, text)
            
            if bracket_matches:
                # 가장 긴 중괄호 블록 찾기
                longest_bracket = max(bracket_matches, key=len)
                self.logger.info(f"중괄호로 둘러싸인 JSON 패턴 발견: {len(longest_bracket)} 자")
                
                # JSON 유효성 검사
                try:
                    json_obj = json.loads(longest_bracket)
                    return longest_bracket.strip()
                except json.JSONDecodeError as e:
                    self.logger.warning(f"중괄호 블록이 유효하지 않음: {e}")

            # 4. JSON 형식 수정 시도
            try:
                # 따옴표 수정 및 이스케이프 문자 처리
                fixed_text = self._fix_json_syntax(text)
                json_obj = json.loads(fixed_text)
                self.logger.info("JSON 구문 수정 후 유효한 JSON 발견")
                return fixed_text
            except (json.JSONDecodeError, Exception) as e:
                self.logger.warning(f"JSON 구문 수정 실패: {e}")

            # 5. 마지막 수단으로 전체 텍스트 반환
            self.logger.warning("JSON 패턴을 찾을 수 없음, 전체 텍스트 반환")
            return text
    
    def _fix_json_syntax(self, text: str) -> str:
        """JSON 구문 오류를 수정."""
        # 작은따옴표를 큰따옴표로 변환
        text = re.sub(r"'([^']*)':", r'"\1":', text)
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
        
        # 후행 쉼표 제거
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*\]", "]", text)

        # 주석 제거
        text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
        
        return text