"""
문서 로딩을 처리하는 모듈입니다.
"""

import os
import json
from typing import Dict, Any, Optional
import re
from pathlib import Path

from src.common.utils import get_logger

logger = get_logger(__name__)

def load_document(input_source: str) -> str:
    """
    소스에서 문서 내용을 로드합니다.
    
    Args:
        input_source: 입력 소스 경로 (파일 경로 또는 S3 URI)
        
    Returns:
        로드된 문서 내용
    """
    logger.info(f"문서 로딩: {input_source}")
    
    # S3 URI 패턴 확인
    s3_pattern = r'^s3://([^/]+)/(.+)$'
    s3_match = re.match(s3_pattern, input_source)
    
    if s3_match:
        # S3에서 로드
        bucket_name = s3_match.group(1)
        object_key = s3_match.group(2)
        return load_from_s3(bucket_name, object_key)
    else:
        # 로컬 파일에서 로드
        return load_from_file(input_source)

def load_from_file(file_path: str) -> str:
    """
    로컬 파일에서 문서 내용을 로드합니다.
    
    Args:
        file_path: 파일 경로
        
    Returns:
        로드된 문서 내용
    """
    # 파일 존재 확인
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일이 존재하지 않습니다: {file_path}")
    
    # 파일 확장자에 따라 다른 처리
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    if ext == '.txt':
        # 텍스트 파일
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    
    elif ext == '.json':
        # JSON 파일
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 콘텐츠 필드 추출 (예상 구조에 따라 변경 필요)
        if isinstance(data, dict) and 'content' in data:
            return data['content']
        else:
            # JSON을 문자열로 변환
            return json.dumps(data, ensure_ascii=False)
    
    elif ext in ['.docx', '.doc']:
        # Word 문서
        try:
            import docx
            doc = docx.Document(file_path)
            content = "\n".join([para.text for para in doc.paragraphs])
            return content
        except ImportError:
            logger.warning("python-docx 패키지가 설치되지 않았습니다. 텍스트로 처리합니다.")
            with open(file_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='ignore')
            return content
    
    elif ext == '.pdf':
        # PDF 문서
        try:
            import PyPDF2
            content = ""
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page_num in range(len(reader.pages)):
                    content += reader.pages[page_num].extract_text() + "\n"
            return content
        except ImportError:
            logger.warning("PyPDF2 패키지가 설치되지 않았습니다. 바이너리로 처리합니다.")
            with open(file_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='ignore')
            return content
    
    else:
        # 기타 파일 형식
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
        return content

def load_from_s3(bucket_name: str, object_key: str) -> str:
    """
    S3에서 문서 내용을 로드합니다.
    
    Args:
        bucket_name: S3 버킷 이름
        object_key: S3 객체 키
        
    Returns:
        로드된 문서 내용
    """
    try:
        import boto3
        
        logger.info(f"S3에서 로딩: {bucket_name}/{object_key}")
        
        # S3 클라이언트 생성
        s3_client = boto3.client('s3')
        
        # 객체 다운로드
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read().decode('utf-8')
        
        return content
    except ImportError:
        logger.error("boto3 패키지가 설치되지 않았습니다.")
        raise ImportError("S3에서 로드하려면 boto3 패키지를 설치하세요: pip install boto3")
    except Exception as e:
        logger.error(f"S3에서 로드 중 오류 발생: {str(e)}")
        raise 