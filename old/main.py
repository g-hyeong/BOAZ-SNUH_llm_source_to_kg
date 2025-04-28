from processor import GuidelineProcessor
import os
import json
import sys
import llm_interface
from s3 import S3Manager
from datetime import datetime
import glob
import importlib.util

guideline_base_path = "datasets/guideline/contents"
target_guidelines = ['ng239']

# 기본 모델 설정
DEFAULT_MODEL_ID = "deepseek"

def upload_results_to_s3(processor, output_files, bucket_name="guideline-to-kg", profile_name="boaz-snuh"):
    """모든 처리 결과와 로그를 S3에 업로드"""
    # S3Manager 인스턴스 생성 (프로세서의 타임스탬프와 프로필 이름 전달)
    s3_manager = S3Manager(
        bucket_name=bucket_name, 
        timestamp=processor.timestamp,
        profile_name=profile_name
    )
    
    # 모든 Python 파일을 자동으로 찾아 업로드
    # 현재 디렉토리의 모든 .py 파일 찾기
    code_files = glob.glob("*.py")
    
    # 중요 파일이 목록에 없으면 추가
    important_files = ["main.py", "processor.py", "agents.py", "llm_interface.py", "call_bedrock.py", "call_gemini.py"]
    for file in important_files:
        if file not in code_files and os.path.exists(file):
            code_files.append(file)
            
    print(f"업로드할 코드 파일: {code_files}")
    
    s3_manager.upload_code_files(code_files, logger=processor.logger)
    
    # requirements.txt 파일 생성 없이 패키지 목록 직접 업로드
    s3_manager.upload_pip_requirements_directly(logger=processor.logger)
    
    # 로그 파일 업로드 (통합 로그와 각 가이드라인별 로그 포함)
    s3_manager.upload_log_files(log_dir="logs", logger=processor.logger)
    
    # 결과 파일 업로드 - 각 가이드라인별 결과 파일 개별 업로드
    for output_file in output_files:
        # 가이드라인 ID 추출 (파일 경로에서 파일명을 추출한 후 확장자 제거)
        target_guideline = os.path.splitext(os.path.basename(output_file))[0]
        
        # 타겟 가이드라인 정보를 갖는 새 S3Manager 생성
        target_s3_manager = S3Manager(
            bucket_name=bucket_name, 
            timestamp=processor.timestamp,
            profile_name=profile_name,
            target_guideline=target_guideline
        )
        # 결과 파일 업로드
        target_s3_manager.upload_result_file(output_file, logger=processor.logger)

def check_dependencies_for_model(model_id):
    """모델 ID에 따라 필요한 의존성 패키지를 확인합니다."""
    
    # Gemini 모델 의존성 확인
    if model_id in ['gemini-2.5', 'gemini-2.0']:
        if importlib.util.find_spec("google.generativeai") is None:
            print("Gemini 모델 사용을 위해 'google-generativeai' 패키지가 필요합니다.")
            print("pip install google-generativeai 명령으로 설치할 수 있습니다.")
            return False
        
        # 환경 변수 확인
        if not os.environ.get("GEMINI_API_KEY"):
            print("경고: GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
            print("export GEMINI_API_KEY='your_api_key' 명령으로 설정해주세요.")
            return False
    
    return True

def show_usage():
    """명령줄 사용법을 출력합니다."""
    print("\n사용법: python main.py [모델_ID]")
    print("\n사용 가능한 모델:")
    
    # 사용 가능한 모델 목록 가져오기
    available_models = llm_interface.get_available_models()
    
    # 모델 유형별로 그룹화
    model_groups = {
        "Ollama": [m for m in available_models if llm_interface.MODEL_MAPPING[m]["backend"] == llm_interface.LLM_TYPE_OLLAMA],
        "Bedrock": [m for m in available_models if llm_interface.MODEL_MAPPING[m]["backend"] == llm_interface.LLM_TYPE_BEDROCK],
        "Gemini": [m for m in available_models if llm_interface.MODEL_MAPPING[m]["backend"] == llm_interface.LLM_TYPE_GEMINI]
    }
    
    # 그룹별로 출력
    for group_name, models in model_groups.items():
        if models:
            print(f"\n-- {group_name} 모델 --")
            for model in models:
                details = llm_interface.MODEL_MAPPING[model]
                actual_model = details.get("model_id") or details.get("model_key")
                print(f"  {model}: {actual_model}")
    
    print(f"\n기본 모델: {DEFAULT_MODEL_ID}")
    print("\n예시:")
    print("  python main.py gemini-2.5  # Gemini 2.5 Pro 모델 사용")
    print("  python main.py gemini-2.0  # Gemini 2.0 Flash 모델 사용")
    print("  python main.py claude      # Claude 3.7 Sonnet 모델 사용\n")

def main():
    """메인 실행 함수"""
    # 명령줄 인자 처리
    model_id = DEFAULT_MODEL_ID
    if len(sys.argv) > 1:
        # 도움말 표시
        if sys.argv[1] in ['-h', '--help', 'help']:
            show_usage()
            return
        model_id = sys.argv[1]
    
    # 사용 가능한 모델 목록 확인
    available_models = llm_interface.get_available_models()
    if model_id not in available_models:
        print(f"오류: 지원되지 않는 모델 ID '{model_id}'")
        show_usage()
        return
    
    # 모델별 필요한 의존성 확인
    if not check_dependencies_for_model(model_id):
        return
    
    # LLM 인터페이스 초기화
    try:
        llm_info = llm_interface.setup_llm(model_id)
        print(f"LLM 설정 완료: {llm_info['type']} 백엔드, 모델 ID: {model_id}")
    except Exception as e:
        print(f"LLM 설정 중 오류 발생: {e}")
        return
    
    # 메인 로거만 초기화 (타임스탬프 생성)
    processor = GuidelineProcessor(init_logger=True, model_id=model_id)
    timestamp = processor.timestamp
    print(f"메인 프로세서 초기화 완료. 타임스탬프: {timestamp}")
    
    # 결과 파일 리스트 추적
    output_files = []
    
    # 타임스탬프 기반 결과 디렉토리 생성
    output_base_dir = f"results/{timestamp}"
    os.makedirs(output_base_dir, exist_ok=True)
    print(f"결과 디렉토리 생성: {output_base_dir}")
    
    for i, target_guideline in enumerate(target_guidelines):
        print(f"\n===== 가이드라인 {i+1}/{len(target_guidelines)}: {target_guideline} 처리 시작 =====")
        
        # 가이드라인 경로 설정
        guideline_path = os.path.join(guideline_base_path, f"{target_guideline}.json")
        
        # 각 가이드라인 처리 전 해당 가이드라인에 맞는 LLM 로거 초기화
        print(f"가이드라인 [{target_guideline}]에 대한 LLM 로거 초기화...")
        processor.initialize_guideline_loggers(target_guideline=target_guideline, timestamp=timestamp)
        
        # 가이드라인 처리
        print(f"가이드라인 [{target_guideline}] 처리 중...")
        result = processor.run(guideline_path)
        
        # 결과 파일 경로 설정
        output_file = f"{output_base_dir}/{target_guideline}.json"
        
        # 결과 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"가이드라인 [{target_guideline}] 결과 저장 완료: {output_file}")
        processor.logger.info(f"최종 결과가 {output_file}에 저장되었습니다.")
        
        # 결과 파일 리스트에 추가
        output_files.append(output_file)
        print(f"===== 가이드라인 {i+1}/{len(target_guidelines)}: {target_guideline} 처리 완료 =====\n")
    
    # S3에 결과 업로드
    print(f"\n모든 가이드라인 처리 완료. S3에 결과 업로드 중...")
    upload_results_to_s3(processor, output_files)
    print("S3 업로드 완료.")

if __name__ == "__main__":
    main()
