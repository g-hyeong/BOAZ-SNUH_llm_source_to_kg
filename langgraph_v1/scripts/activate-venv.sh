#!/bin/bash

# 가상환경 경로 설정
VENV_PATH=".venv/llm-source-to-kg"

# 가상환경이 존재하는지 확인
if [ ! -d "$VENV_PATH" ]; then
    echo "가상환경이 존재하지 않습니다. 새로 생성합니다..."
    uv venv -p 3.11.7 "$VENV_PATH"
    
    if [ $? -ne 0 ]; then
        echo "가상환경 생성에 실패했습니다."
        exit 1
    fi
    
    echo "가상환경이 성공적으로 생성되었습니다."
else
    echo "기존 가상환경을 사용합니다."
fi

# 가상환경 활성화
echo "가상환경을 활성화합니다..."
source "$VENV_PATH/bin/activate"

# 활성화 확인
if [ $? -eq 0 ]; then
    echo "가상환경이 활성화되었습니다. ($(python --version))"
    echo "비활성화하려면 'deactivate' 명령어를 사용하세요."
else
    echo "가상환경 활성화에 실패했습니다."
    exit 1
fi
