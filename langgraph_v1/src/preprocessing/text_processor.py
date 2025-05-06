"""
텍스트 전처리를 수행하는 모듈입니다.
"""

import re
from typing import List, Optional
import unicodedata

from src.common.utils import get_logger

logger = get_logger(__name__)

def clean_text(text: str) -> str:
    """
    텍스트를 정제합니다.
    
    Args:
        text: 정제할 텍스트
        
    Returns:
        정제된 텍스트
    """
    if not text:
        return ""
    
    logger.info("텍스트 정제 시작")
    
    # 유니코드 정규화
    text = unicodedata.normalize('NFC', text)
    
    # 여러 공백을 하나의 공백으로 변환
    text = re.sub(r'\s+', ' ', text)
    
    # 불필요한 특수문자 제거 (의미 있는 특수문자는 유지)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
    
    # 여러 줄바꿈을 하나의 줄바꿈으로 변환
    text = re.sub(r'\n+', '\n', text)
    
    # 텍스트 앞뒤 공백 제거
    text = text.strip()
    
    logger.info("텍스트 정제 완료")
    
    return text

def split_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    텍스트를 일정한 크기의 청크로 분할합니다.
    
    Args:
        text: 분할할 텍스트
        chunk_size: 청크 크기 (문자 수)
        overlap: 청크 간 겹치는 부분의 크기 (문자 수)
        
    Returns:
        분할된 텍스트 청크 목록
    """
    if not text:
        return []
    
    logger.info(f"텍스트 청크 분할 시작: chunk_size={chunk_size}, overlap={overlap}")
    
    # 텍스트가 충분히 짧으면 하나의 청크로 반환
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # 청크 끝 위치 계산
        end = start + chunk_size
        
        if end >= len(text):
            # 마지막 청크
            chunks.append(text[start:])
            break
        
        # 청크 경계를 의미 있는 위치로 조정 (문장 또는 단락 끝)
        # 문장 끝 (., !, ?, 등)
        sentence_end = find_sentence_boundary(text, end)
        
        # 문단 끝 (\n)
        paragraph_end = text.rfind('\n', start, end)
        
        # 의미 있는 경계 선택
        if sentence_end > 0 and (sentence_end - start) >= chunk_size / 2:
            # 문장 끝 사용
            chunk_end = sentence_end
        elif paragraph_end > 0 and (paragraph_end - start) >= chunk_size / 3:
            # 문단 끝 사용
            chunk_end = paragraph_end
        else:
            # 단어 경계 사용
            space_position = text.rfind(' ', start, end)
            if space_position > start:
                chunk_end = space_position
            else:
                # 적절한 경계를 찾을 수 없으면 원래 청크 크기 사용
                chunk_end = end
        
        # 청크 추가
        chunks.append(text[start:chunk_end])
        
        # 다음 청크의 시작 위치 계산 (overlap 고려)
        start = max(start + (chunk_end - start) - overlap, start + 1)
    
    logger.info(f"텍스트 청크 분할 완료: {len(chunks)}개 청크 생성")
    
    return chunks

def find_sentence_boundary(text: str, position: int) -> int:
    """
    주어진 위치 근처에서 문장 경계를 찾습니다.
    
    Args:
        text: 대상 텍스트
        position: 검색 시작 위치
        
    Returns:
        문장 경계 위치 (문장 끝 문자 위치)
    """
    # 문장 끝 문자 정의
    sentence_endings = ['.', '!', '?', '。', '!', '？']
    
    # 위치부터 역방향 검색
    for i in range(min(position, len(text) - 1), max(0, position - 200), -1):
        if text[i] in sentence_endings:
            # 약어 등에 유의 (예: "Dr.", "U.S.")
            if i + 1 < len(text) and text[i + 1].isspace():
                return i + 1
    
    # 문장 경계를 찾지 못한 경우
    return -1

def extract_entities(text: str) -> List[str]:
    """
    텍스트에서 간단한 엔티티를 추출합니다.
    (이 함수는 실제 구현에서는 NER 모델 등을 사용해야 합니다)
    
    Args:
        text: 대상 텍스트
        
    Returns:
        추출된 엔티티 목록
    """
    # 예시용 간단한 패턴 매칭 (실제로는 NER 모델 사용)
    entities = []
    
    # 대문자로 시작하는 연속된 단어 (간단한 명사구) 추출
    proper_noun_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
    for match in re.finditer(proper_noun_pattern, text):
        entities.append(match.group(0))
    
    # 숫자와 단위 패턴 추출
    measurement_pattern = r'\b\d+(?:\.\d+)?\s*(?:mg|kg|ml|g|mm|cm|mcg)\b'
    for match in re.finditer(measurement_pattern, text, re.IGNORECASE):
        entities.append(match.group(0))
    
    return list(set(entities))  # 중복 제거 