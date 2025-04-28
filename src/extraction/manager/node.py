from common.llm.getter import get_llm
from typing import List, Dict, Any
from pathlib import Path
import json
from jinja2 import Template
from config import settings
from common.logging import get_logger

logger = get_logger("main")

class ManagerNode:
    def __init__(self, llm_type: str, llm_config: Dict[str, Any], command: str, targets: List[str] = None):
        """
        ManagerNode 클래스 생성자

        Args:
            llm_type: 사용할 LLM 유형 ("gemini" 등)
            llm_config: LLM 설정
            command: 처리할 명령어 ("all", "select", 파일명)
            targets: 선택적으로 처리할 대상 파일 목록
        """
        self.llm = get_llm(llm_type, llm_config)
        self.command = command
        self.targets = targets

    def run(self):
        """
        매니저 노드 실행 메서드
        대상 소스 파일을 가져와 각각에 대해 LLM 요청을 수행

        Yields:
            각 대상 소스 파일에 대한 LLM 응답
        """
        targets = self.get_target_sources(self.command, self.targets)
        for target in targets:
            result = self.manager_request(target)
            yield result

    def manager_request(self, target: Path) -> Dict[str, Any]:
        """
        특정 대상 파일에 대해 LLM 요청을 수행하는 메서드

        Args:
            target: 처리할 대상 파일 경로

        Returns:
            LLM 응답 결과
        """
        prompt = self.set_prompt(target)
        logger.info(f"LLM 요청 시작: 타겟={target.name}, 프롬프트 길이={len(prompt)}")
        # 문자열 프롬프트를 Gemini LLM에 전달
        response = self.llm.chat(prompt)
        logger.info(f"LLM 응답 수신: 응답 길이={len(response)}")
        
        # 반환 형식이 str일 경우 딕셔너리로 변환
        if isinstance(response, str):
            return {
                "response": response,
                "metadata": {"file": target.name}
            }
        
        return response
    
    def get_target_sources(self, command: str, targets: List[str] = None) -> List[Path]:
        """
        명령어에 따라 처리할 타겟 소스 파일들의 경로 목록을 반환
        
        Args:
            command: 명령행 인자로 받은 명령어 (all, select, 파일명)
            targets: 선택된 타겟 파일 목록 (command가 "select"인 경우)
            
        Returns:
            처리할 소스 파일들의 경로 리스트
        
        Raises:
            FileNotFoundError: 지정된 파일이 존재하지 않을 경우
            ValueError: 적절하지 않은 명령어가 입력된 경우
        """
        guideline_dir = settings.guideline_dir
        
        if command == "all":
            # guideline_dir의 모든 json 파일 반환
            return list(guideline_dir.glob("*.json"))
        
        elif command == "select":
            # targets에 명시된 파일들만 반환
            result = []
            for filename in targets:
                file_path = guideline_dir / filename
                if file_path.exists():
                    result.append(file_path)
                else:
                    logger.warning(f"선택된 소스 파일 '{filename}'이 존재하지 않습니다.")
            return result
        
        else:
            # 특정 파일명이 입력된 경우 (확장자 처리)
            filename = command if command.endswith(".json") else f"{command}.json"
            file_path = guideline_dir / filename
            
            if not file_path.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
            return [file_path]

    def set_prompt(self, target: Path) -> str:
        """
        타겟 파일에 대한 프롬프트를 생성합니다. Jinja2 템플릿을 사용하여 prompt.txt 파일을 렌더링합니다.
        
        Args:
            target: 가이드라인 파일의 경로
            
        Returns:
            렌더링된 프롬프트 문자열
            
        Raises:
            FileNotFoundError: prompt.txt 파일이 존재하지 않을 경우
            JSONDecodeError: 타겟 파일이 유효한 JSON 형식이 아닐 경우
        """
        # 프롬프트 템플릿 파일 경로
        prompt_path = Path(__file__).parent / "prompt.txt"
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"프롬프트 템플릿 파일을 찾을 수 없습니다: {prompt_path}")
        
        # 타겟 파일에서 JSON 데이터 로드
        try:
            with open(target, 'r', encoding='utf-8') as f:
                guideline_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"타겟 파일 '{target}'이 유효한 JSON 형식이 아닙니다: {e}")
            raise
        
        # 프롬프트 템플릿 로드
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Jinja2 템플릿 렌더링
        template = Template(template_content)
        rendered_prompt = template.render(
            title=guideline_data.get('title', '제목 없음'),
            contents=guideline_data.get('contents', '')
        )
        
        return rendered_prompt