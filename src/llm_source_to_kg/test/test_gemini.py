import asyncio
import sys
import os
# 프로젝트 루트 디렉토리를 sys.path에 추가하는 코드는 필요 없음
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# pyproject.toml 패키지 설정에 맞는 import
from llm_source_to_kg.llm.gemini import GeminiLLM
from llm_source_to_kg.llm.common_llm_interface import LLMMessage, LLMRole


async def test_call_llm():
    """
    단일 프롬프트 호출 테스트
    """
    print("=== 단일 프롬프트 호출 테스트 ===")
    
    # GeminiLLM 인스턴스 생성
    gemini_llm = GeminiLLM()
    
    # 간단한 프롬프트 전송
    prompt = "안녕하세요, 당신은 누구인가요?"
    print(f"프롬프트: {prompt}")
    
    # call_llm 메서드 호출
    response = await gemini_llm.call_llm(prompt)
    
    # 응답 출력
    print(f"응답: {response.content}")
    print(f"모델: {response.model}")
    print(f"토큰 사용량: {response.usage}")
    print()
    print(f"Gemini call raw request prompt: {prompt}")
    print(f"Gemini call raw response: {response}")



async def test_chat_llm():
    """
    채팅 메시지 목록 호출 테스트
    """
    print("=== 채팅 메시지 목록 호출 테스트 ===")
    
    # GeminiLLM 인스턴스 생성
    gemini_llm = GeminiLLM()
    
    # 테스트 메시지 생성
    messages = [
        LLMMessage(role=LLMRole.SYSTEM, content="당신은 도움이 되는 AI 어시스턴트입니다."),
        LLMMessage(role=LLMRole.USER, content="파이썬에 대해 간단히 설명해주세요."),
        LLMMessage(role=LLMRole.ASSISTANT, content="파이썬은 읽기 쉽고 배우기 쉬운 고급 프로그래밍 언어입니다."), # llm 응답 임의 생성
        LLMMessage(role=LLMRole.USER, content="너가 방금 내가 물어본 게 배우기 쉽다고 했어 어렵다고 했어??")
    ]
    
    # 채팅 히스토리 출력
    print("채팅 히스토리:")
    for i, message in enumerate(messages):
        print(f"[{i+1}] {message.role.value}: {message.content}")
    
    # chat_llm 메서드 호출
    response = await gemini_llm.chat_llm(messages)
    
    # 응답 출력
    print("\n응답:")
    print(response.content)
    print(f"모델: {response.model}")
    print(f"토큰 사용량: {response.usage}")


    print(f"Gemini chat raw request: {messages}")
    print(f"Gemini chat raw response: {response}")


async def async_main():
    """
    비동기 메인 함수
    """
    # 단일 프롬프트 호출 테스트
    await test_call_llm()
    
    # 채팅 메시지 목록 호출 테스트
    await test_chat_llm()


# poetry run test-gemini 명령으로 실행할 수 있는 진입점 함수
def main():
    """
    poetry 스크립트 진입점
    """
    asyncio.run(async_main())


# 직접 실행 시 테스트 실행
if __name__ == "__main__":
    asyncio.run(async_main())
