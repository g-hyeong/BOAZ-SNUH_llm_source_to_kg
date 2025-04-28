#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
로깅 설정 모듈
- 메인 로거
- LLM 프롬프트 로거
- LLM 응답 로거
- SQL 쿼리 로거
"""

import os
import logging
from datetime import datetime

class LoggerManager:
    """로깅 관리 클래스"""
    
    def __init__(self, log_dir="logs", target_guideline=None, timestamp=None):
        """로거 초기화"""
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 타임스탬프가 외부에서 제공되었으면 사용, 아니면 현재 시간 기준으로 생성
        if timestamp:
            self.timestamp = timestamp
        else:
            # 현재 시간을 기반으로 로그 파일명 생성
            self.timestamp = datetime.now().strftime("%m%d_%H%M")
        
        # 타임스탬프 기반 로그 디렉토리 생성
        self.timestamp_log_dir = os.path.join(self.log_dir, self.timestamp)
        os.makedirs(self.timestamp_log_dir, exist_ok=True)
        
        # 공통 로그 파일 경로 설정 (모든 가이드라인을 위한 하나의 로그)
        self.common_log_filename = f"{self.timestamp_log_dir}/guideline_processing.log"
        
        # target_guideline이 제공된 경우 해당 가이드라인 별도 디렉토리 생성
        self.target_guideline = target_guideline
        if target_guideline:
            self.log_guideline_dir = os.path.join(self.timestamp_log_dir, target_guideline)
            os.makedirs(self.log_guideline_dir, exist_ok=True)
            
            # 가이드라인별 LLM 로그 파일 경로 설정
            self.prompt_log_filename = f"{self.log_guideline_dir}/llm_prompts.log"
            self.response_log_filename = f"{self.log_guideline_dir}/llm_responses.log"
        else:
            # 가이드라인이 지정되지 않은 경우 루트 타임스탬프 디렉토리에 LLM 로그 파일 설정
            # (이 파일들은 실제로 사용되지 않을 예정)
            self.prompt_log_filename = f"{self.timestamp_log_dir}/llm_prompts.log"
            self.response_log_filename = f"{self.timestamp_log_dir}/llm_responses.log"
        
        # 로거 설정
        self._setup_loggers()
    
    def _setup_loggers(self):
        """로거 설정"""
        # 메인 로거 설정 (모든 가이드라인에 공통으로 사용)
        self.logger = logging.getLogger("GuidlineProcessor")
        
        # 메인 로거가 이미 핸들러를 가지고 있는지 확인
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            file_handler = logging.FileHandler(self.common_log_filename, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(stream_handler)
        
        # 가이드라인별 LLM 프롬프트 로거 설정
        if self.target_guideline:
            # 가이드라인별 고유 이름으로 로거 생성
            logger_name = f"LLM_Prompts_{self.target_guideline}"
            self.prompt_logger = logging.getLogger(logger_name)
            
            # 기존 핸들러 제거 (동일 로거에 추가 핸들러가 붙는 것을 방지)
            if self.prompt_logger.handlers:
                for handler in self.prompt_logger.handlers[:]:
                    self.prompt_logger.removeHandler(handler)
            
            self.prompt_logger.setLevel(logging.INFO)
            prompt_handler = logging.FileHandler(self.prompt_log_filename, encoding='utf-8')
            prompt_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
            self.prompt_logger.addHandler(prompt_handler)
            
            # propagate를 명확하게 설정
            # True로 설정하면 상위 로거로 로그가 전달됨, False로 설정하면 전달되지 않음
            # 프롬프트는 별도로 저장되어야 하므로 False로 설정
            self.prompt_logger.propagate = False
            
            # 가이드라인별 LLM 응답 로거 설정
            logger_name = f"LLM_Responses_{self.target_guideline}"
            self.response_logger = logging.getLogger(logger_name)
            
            # 기존 핸들러 제거
            if self.response_logger.handlers:
                for handler in self.response_logger.handlers[:]:
                    self.response_logger.removeHandler(handler)
            
            self.response_logger.setLevel(logging.INFO)
            response_handler = logging.FileHandler(self.response_log_filename, encoding='utf-8')
            response_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
            self.response_logger.addHandler(response_handler)
            
            # propagate를 명확하게 설정
            # 응답도 별도로 저장되어야 하므로 False로 설정
            self.response_logger.propagate = False
        else:
            # 가이드라인이 지정되지 않은 경우 빈 로거 생성 (실제로 사용되지 않음)
            self.prompt_logger = logging.getLogger("LLM_Prompts_Default")
            self.prompt_logger.setLevel(logging.INFO)
            
            # 핸들러 제거
            if self.prompt_logger.handlers:
                for handler in self.prompt_logger.handlers[:]:
                    self.prompt_logger.removeHandler(handler)
                
            # propagate 설정
            self.prompt_logger.propagate = False
            
            self.response_logger = logging.getLogger("LLM_Responses_Default")
            self.response_logger.setLevel(logging.INFO)
            
            # 핸들러 제거
            if self.response_logger.handlers:
                for handler in self.response_logger.handlers[:]:
                    self.response_logger.removeHandler(handler)
                
            # propagate 설정
            self.response_logger.propagate = False
        
        print(f"로거 설정 완료: 메인={bool(self.logger)}, 프롬프트={bool(self.prompt_logger)}, 응답={bool(self.response_logger)}")
        if self.target_guideline:
            print(f"가이드라인 [{self.target_guideline}]에 대한 로그 파일 경로:")
            print(f"- 프롬프트 로그: {self.prompt_log_filename}")
            print(f"- 응답 로그: {self.response_log_filename}")
        print(f"- 공통 로그: {self.common_log_filename}")
    
    def get_logger(self):
        """메인 로거 반환"""
        return self.logger
    
    def get_prompt_logger(self):
        """프롬프트 로거 반환"""
        return self.prompt_logger
    
    def get_response_logger(self):
        """응답 로거 반환"""
        return self.response_logger
    
    def get_timestamp(self):
        """타임스탬프 반환"""
        return self.timestamp