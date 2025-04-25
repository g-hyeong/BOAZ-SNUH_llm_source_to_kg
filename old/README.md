# 가이드라인 지식 그래프 및 코호트 분석 시스템

## 1. 프로젝트 개요

이 프로젝트는 의료 가이드라인 문서를 분석하여 지식 그래프(Knowledge Graph)와 코호트 분석(Cohort Analysis)을 자동으로 추출하는 시스템입니다. 멀티 에이전트 접근법을 사용하여 의료 가이드라인에서 의미있는 엔티티, 관계, 그리고 분석 정보를 추출합니다.

## 2. 핵심 구성 요소

### 2.1 주요 모듈

1. **GuidelineProcessor (`processor.py`)**:
   - 전체 가이드라인 처리 과정을 관리
   - 문서 로딩, 로깅, 멀티 에이전트 시스템 초기화 담당

2. **MultiAgentSystem (`agents.py`)**:
   - 여러 전문화된 에이전트 조정
   - 상태 그래프(State Graph)를 사용하여 에이전트 간 작업 흐름 관리

3. **BaseAgent와 특수 에이전트들 (`agents.py`)**:
   - ManagerAgent: 가이드라인 분석 및 작업 할당
   - DrugAgent: 약물 관련 정보 분석
   - DiagnosisAgent: 질병 및 진단 관련 정보 분석

4. **LoggerManager (`logger.py`)**:
   - 다양한 로깅 레벨 및 형식 지원
   - 가이드라인별 로깅 관리

5. **S3Manager (`s3.py`)**:
   - 처리 결과, 로그 및 코드를 AWS S3에 저장
   - 타임스탬프 기반 디렉토리 구조 관리

6. **LLM 인터페이스 (`llm_interface.py`)**:
   - 다양한 LLM 백엔드(Ollama, Bedrock, Gemini) 통합 관리
   - 통일된 인터페이스를 통한 모델 호출

### 2.2 주요 데이터

1. **상수 및 참조 데이터 (`constants.py`)**:
   - OMOP CDM 엔티티 개념명
   - 관계 이름 목록

2. **프롬프트 (`prompts.py`)**:
   - 다양한 에이전트용 구조화된 프롬프트 템플릿
   - 전문화된 지시사항과 출력 형식 정의

## 3. 데이터 흐름 및 프로세스

### 3.1 기본 실행 과정

1. **초기화**:
   - `main.py`에서 `GuidelineProcessor` 인스턴스 생성
   - 타임스탬프 기반 로깅 시스템 초기화

2. **가이드라인 처리**:
   - 입력 폴더(`datasets/guideline/contents`)에서 지정된 가이드라인 파일 로드
   - 가이드라인별 전용 로거 초기화
   - 멀티 에이전트 시스템을 사용한 문서 분석

3. **결과 저장**:
   - JSON 형식으로 분석 결과 저장
   - 타임스탬프 기반 디렉토리(`results/[timestamp]`)에 저장
   - S3 버킷에 결과, 로그, 코드 파일 업로드

### 3.2 멀티 에이전트 처리 과정

1. **문서 초기 분석**:
   - ManagerAgent가 가이드라인 문서 분석
   - 엔티티와 관계 식별, 코호트 분석 제안, 다음 에이전트 선택

2. **전문 분석**:
   - DrugAgent: 약물 관련 엔티티, 관계, 치료 경로, 약물 코호트 분석
   - DiagnosisAgent: 질병 관련 엔티티, 관계, 진단 경로, 질병 코호트 분석

3. **결과 종합**:
   - 지식 그래프: 엔티티와 관계 정보 종합
   - 코호트 분석: 코호트 정의 및 분석 정보 종합

## 4. 주요 기술 및 도구

1. **LLM 기반 처리**:
   - 기본 모델: "deepseek-r1:14b"
   - 지원 모델:
     - Ollama: deepseek, deepseek-coder, dolphin, mixtral, vicuna, llama2
     - Bedrock: claude, llama
     - Gemini: gemini-2.5, gemini-2.0
   - 프롬프트 엔지니어링으로 구조화된 응답 생성

2. **자연어 처리**:
   - NLTK 라이브러리 사용
   - BM25 기반 문서 검색 알고리즘

3. **로깅 시스템**:
   - 계층적 로깅 구조
   - 프롬프트와 응답 로깅 분리

4. **클라우드 통합**:
   - AWS S3를 사용한 결과 및 로그 저장
   - 프로필 기반 인증 지원

## 5. 결과 출력 형식

1. **지식 그래프**:
   - 엔티티: OMOP CDM 컨셉 이름, 도메인, 속성
   - 관계: 소스 엔티티, 타겟 엔티티, 관계 이름, 근거 텍스트, 확실성

2. **코호트 분석**:
   - 약물 코호트: 약물 엔티티, 용량, 투약 방법, 적응증, 금기사항
   - 질병 코호트: 질병 엔티티, 심각도, 진단 기준, 스테이징 정보
   - 치료/진단 경로: 순차적 단계, 의사결정 지점, 대안

## 6. 특별한 기능

1. **자동 문서 증거 검증**:
   - 코호트 정의 검증을 위한 예/아니오 질문 생성
   - 문서 내 관련 증거 검색 및 평가

2. **S3 통합**:
   - 모든 처리 결과 및 로그의 자동 업로드
   - 코드 파일 및 의존성 라이브러리 목록 업로드

3. **확장 가능한 아키텍처**:
   - 에이전트 추가 용이
   - 상태 그래프 기반 워크플로우 관리

## 7. 실행 방법

### 7.1 기본 실행

```bash
# 기본 모델(deepseek)로 실행
python main.py

# 특정 모델 지정
python main.py claude      # AWS Bedrock Claude 3.7 Sonnet 모델
python main.py gemini-2.5  # Google Gemini 2.5 Pro 모델
python main.py gemini-2.0  # Google Gemini 2.0 Flash 모델

# 도움말 표시
python main.py --help
```

### 7.2 Gemini 모델 사용 설정

1. **필수 패키지 설치**:
   ```bash
   pip install google-generativeai
   ```

2. **API 키 설정**:
   ```bash
   # Gemini API 키 설정
   export GEMINI_API_KEY='your_api_key_here'
   ```

3. **단독 Gemini 테스트**:
   ```bash
   # Gemini 2.5 Pro 모델 테스트
   python test_gemini.py gemini-2.5
   
   # Gemini 2.0 Flash 모델 테스트
   python test_gemini.py gemini-2.0
   ```

### 7.3 모델별 환경 변수

- **Gemini 모델**: `GEMINI_API_KEY` - Google AI API 키
- **Bedrock 모델**: `AWS_PROFILE` - AWS 프로필 (기본값: "boaz-snuh")
- **Ollama 모델**: 로컬 Ollama 서버 실행 필요
