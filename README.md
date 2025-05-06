# BOAZ-SNUH LLM Source to Knowledge Graph

BOAZ-SNUH 프로젝트의 LLM 기반 소스 코드에서 지식 그래프를 추출하는 도구입니다.

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
├── pyproject.toml    # Poetry 프로젝트 설정
├── src/              # 소스 코드
│   └── llm_source_to_kg/
│       ├── graph/    # 그래프 관련 모듈
│       ├── llm/      # LLM 관련 모듈
│       ├── schema/   # 스키마 정의
│       └── utils/    # 유틸리티 함수
└── datasets/         # 데이터셋 디렉토리
```

## 추가 설정 (필요한 경우)

### 환경 변수 설정

프로젝트에 필요한 API 키나 환경 변수가 있다면 `.env` 파일을 생성하여 설정하세요:

```bash
# .env 파일 생성
touch .env

# 예시 환경 변수
# OPENAI_API_KEY=your_api_key_here
```

### 추가 패키지 설치

필요한 추가 패키지가 있다면 다음과 같이 설치할 수 있습니다:

```bash
poetry add 패키지명
```

## 문제 해결

- **Poetry 명령어가 인식되지 않는 경우**: PATH에 Poetry가 추가되었는지 확인하세요.
- **의존성 충돌**: `poetry update` 명령어로 의존성을 업데이트해 보세요.
- **가상 환경 문제**: `poetry env info`로 현재 가상 환경 정보를 확인하세요. 