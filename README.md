# BOAZ-SNUH LLM Source to Knowledge Graph

> [SNOMED-BOAZ | LLM-Source-To_KG](https://github.com/SNOMED-BOAZ/LLM-Source-To-KG) repository 변경됐습니다.

이 프로젝트에 대한 협업 규칙은 [CONVENTION.md](./CONVENTION.md)를 참조하세요.

## 프로젝트 개요

이 프로젝트는 소스 코드를 분석하여 LLM(Large Language Model)을 활용해 지식 그래프(Knowledge Graph)를 생성합니다.

## 환경 설정 가이드

이 프로젝트는 Python 3.11 이상 및 Poetry를 사용하여 의존성을 관리합니다. 아래 단계를 따라 개발 환경을 설정하세요.

### 사전 요구사항

- Python 3.11 이상
- Poetry 설치

### 1. Poetry 설치

#### macOS / Linux
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

#### Windows
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### 2. 프로젝트 클론

```bash
git clone https://github.com/GU-0/BOAZ-SNUH_llm_source_to_kg.git
cd BOAZ-SNUH_llm_source_to_kg
```

### 3. Poetry 환경 설정

```bash
# Poetry 가상 환경 생성 및 의존성 설치
poetry install

# 가상 환경 활성화
poetry shell
```

### 4. 프로젝트 실행

Poetry 환경이 활성화된 상태에서 프로젝트를 실행할 수 있습니다:

```bash
# 예시 실행 명령어 (프로젝트 실행 방식에 따라 수정 필요)
python -m src.llm_source_to_kg
```

## 프로젝트 구조

```
.
├── pyproject.toml         # Poetry 프로젝트 설정 파일
├── CONVENTION.md          # 협업 규칙 및 컨벤션 문서
├── prompts/               # LLM 프롬프트 템플릿 디렉토리
│   └── sample.txt         # 샘플 프롬프트 파일
├── src/                   # 소스 코드
│   └── llm_source_to_kg/  # 메인 패키지
│       ├── __init__.py    # 패키지 초기화 파일
│       ├── config.py      # 프로젝트 설정 파일
│       ├── graph/         # 그래프 관련 모듈
│       │   ├── orchestrator.py  # 그래프 생성 오케스트레이터
│       │   ├── cohort_graph/    # 코호트 그래프 관련 모듈
│       │   │   ├── __init__.py
│       │   │   ├── orchestrator.py  # 코호트 그래프 생성 오케스트레이터
│       │   │   ├── state.py         # 코호트 그래프 상태 관리
│       │   │   ├── utils.py         # 코호트 그래프 유틸리티
│       │   │   └── nodes/           # 코호트 그래프 노드 관련 클래스
│       │   ├── analysis_graph/   # 분석 그래프 관련 모듈
│       │   │   ├── __init__.py
│       │   │   ├── orchestrator.py  # 분석 그래프 생성 오케스트레이터
│       │   │   ├── state.py         # 분석 그래프 상태 관리
│       │   │   └── nodes/           # 분석 그래프 노드 관련 클래스
│       ├── llm/           # LLM 관련 모듈
│       │   ├── common_llm_interface.py  # LLM 공통 인터페이스
│       │   └── gemini.py              # Gemini 모델 구현
│       ├── schema/        # 스키마 정의
│       │   └── types.py   # 타입 정의
│       └── utils/         # 유틸리티 함수
│           └── util.py    # 유틸리티 구현
└── datasets/              # 데이터셋 디렉토리
    ├── omop/              # OMOP 데이터셋
    ├── guideline/         # 가이드라인 데이터셋
    └── csv_to_db.py       # CSV를 데이터베이스로 변환하는 스크립트
```
