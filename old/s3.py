import boto3
import os
from datetime import datetime

class S3Manager:
    """S3 버킷 관리를 위한 클래스"""
    
    def __init__(self, bucket_name="guideline-to-kg", timestamp=None, profile_name=None, target_guideline=None):
        """
        S3Manager 초기화
        
        Args:
            bucket_name (str): S3 버킷 이름
            timestamp (str, optional): 파일 저장 시 사용할 타임스탬프
            profile_name (str, optional): 사용할 AWS 프로필 이름
            target_guideline (str, optional): 처리 중인 가이드라인 ID
        """
        self.bucket_name = bucket_name
        self.target_guideline = target_guideline
        
        # timestamp가 제공된 경우 형식 변환 (mmdd_hhmm -> mm/dd/hh_mm)
        self.origin_timestamp = timestamp
        if timestamp and '_' in timestamp:
            try:
                # mmdd_hhmm 형식에서 날짜와 시간 추출
                date_part = timestamp.split('_')[0]  # mmdd
                time_part = timestamp.split('_')[1]  # hhmm
                
                # 날짜와 시간 분리
                month_day = date_part  # mmdd
                hour_min = f"{time_part[:2]}_{time_part[2:]}"  # hh_mm
                
                # S3 경로 구성
                self.timestamp = timestamp
                self.month_day = month_day
                self.hour_min = hour_min
            except:
                # 형식이 맞지 않으면 원래 값 사용
                self.timestamp = timestamp
                self.month_day = datetime.now().strftime("%m%d")
                self.hour_min = datetime.now().strftime("%H_%M")
        else:
            self.timestamp = timestamp
            self.month_day = datetime.now().strftime("%m%d")
            self.hour_min = datetime.now().strftime("%H_%M")
        
        # 프로필 이름이 제공된 경우 해당 프로필로 세션 생성
        if profile_name:
            # 프로필을 사용하여 세션 생성
            session = boto3.Session(profile_name=profile_name)
            # 세션으로부터 S3 클라이언트 생성
            self.s3_client = session.client('s3')
        else:
            # 기본 프로필 사용
            self.s3_client = boto3.client('s3')
        
        # 기본 S3 경로 설정
        if self.timestamp:
            self.default_s3_path = f"{self.month_day}/{self.hour_min}"
        else:
            self.default_s3_path = f"{self.month_day}/{self.hour_min}"
    
    def upload_file(self, local_path, s3_path=None):
        """
        로컬 파일을 S3에 업로드
        
        Args:
            local_path (str): 업로드할 로컬 파일 경로
            s3_path (str, optional): S3에 저장될 경로. 기본값은 None으로 파일명만 사용
            
        Returns:
            bool: 업로드 성공 여부
        """
        try:
            if s3_path is None:
                s3_path = os.path.basename(local_path)
            
            # 파일을 바이너리 모드로 열어서 업로드 (되감기 문제 해결)
            with open(local_path, 'rb') as file_data:
                self.s3_client.upload_fileobj(file_data, self.bucket_name, s3_path)
            return True
        except Exception as e:
            print(f"S3 업로드 중 오류 발생: {e}")
            return False
    
    def upload_code_files(self, code_files, logger=None):
        """
        코드 파일들을 S3에 업로드
        
        Args:
            code_files (list): 업로드할 코드 파일 리스트
            logger (Logger, optional): 로깅을 위한 로거 객체
            
        Returns:
            list: 업로드된 파일 경로 리스트
        """
        uploaded_files = []
        
        for file in code_files:
            if os.path.exists(file):
                # 기본 S3 경로 활용
                s3_path = f"{self.default_s3_path}/codes/{file}"
                
                success = self.upload_file(file, s3_path)
                
                if success:
                    uploaded_files.append(s3_path)
                    message = f"{file}을(를) S3 {s3_path}에 업로드했습니다."
                    
                    if logger:
                        logger.info(message)
                    else:
                        print(message)
        
        return uploaded_files
    
    def upload_requirements_file(self, logger=None, generate_if_missing=False):
        """
        requirements.txt 파일을 S3에 업로드
        
        Args:
            logger (Logger, optional): 로깅을 위한 로거 객체
            generate_if_missing (bool): requirements.txt 파일이 없을 경우 생성 여부
            
        Returns:
            str: 업로드된 S3 경로 또는 None(실패시)
        """
        requirements_file = "requirements.txt"
        
        # 파일이 존재하지 않고 생성 옵션이 켜져 있으면 즉시 생성
        if not os.path.exists(requirements_file) and generate_if_missing:
            # 현재 설치된 패키지 목록 생성
            self._generate_requirements_file(requirements_file, logger)
        
        if not os.path.exists(requirements_file):
            message = f"{requirements_file} 파일이 존재하지 않습니다."
            if logger:
                logger.warning(message)
            else:
                print(message)
            return None
        
        # 기본 S3 경로 활용
        s3_path = f"{self.default_s3_path}/codes/{requirements_file}"
        
        success = self.upload_file(requirements_file, s3_path)
        
        if success:
            message = f"{requirements_file} 파일을 S3 {s3_path}에 업로드했습니다."
            
            if logger:
                logger.info(message)
            else:
                print(message)
            
            return s3_path
        
        return None
    
    def _generate_requirements_file(self, file_path="requirements.txt", logger=None):
        """
        현재 환경의 설치된 패키지 목록을 requirements.txt 파일로 생성
        
        Args:
            file_path (str): 생성할 파일 경로
            logger (Logger, optional): 로깅을 위한 로거 객체
            
        Returns:
            bool: 파일 생성 성공 여부
        """
        try:
            import subprocess
            
            # pip freeze 명령 실행하여 설치된 패키지 목록 가져오기
            process = subprocess.Popen(['pip', 'freeze'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                message = f"패키지 목록 가져오기 실패: {stderr.decode('utf-8')}"
                if logger:
                    logger.error(message)
                else:
                    print(message)
                return False
            
            # requirements.txt 파일 생성
            with open(file_path, 'w') as f:
                f.write(stdout.decode('utf-8'))
            
            message = f"{file_path} 파일을 생성했습니다."
            if logger:
                logger.info(message)
            else:
                print(message)
                
            return True
        
        except Exception as e:
            message = f"requirements.txt 파일 생성 중 오류 발생: {e}"
            if logger:
                logger.error(message)
            else:
                print(message)
            return False
                
    def generate_and_upload_requirements(self, logger=None):
        """
        현재 환경의 패키지 목록을 생성하고 S3에 즉시 업로드
        
        Args:
            logger (Logger, optional): 로깅을 위한 로거 객체
            
        Returns:
            str: 업로드된 S3 경로 또는 None(실패시)
        """
        # requirements.txt 파일 생성
        if self._generate_requirements_file(logger=logger):
            # S3에 업로드
            return self.upload_requirements_file(logger=logger)
        
        return None
    
    def upload_log_files(self, log_dir="logs", logger=None):
        """
        로그 디렉토리의 모든 로그 파일을 S3에 업로드
        
        Args:
            log_dir (str): 로그 파일이 저장된 디렉토리 경로
            logger (Logger, optional): 로깅을 위한 로거 객체
            
        Returns:
            list: 업로드된 파일 경로 리스트
        """
        uploaded_files = []
        timestamp_log_dir = os.path.join(log_dir, self.origin_timestamp)
        
        if not os.path.exists(timestamp_log_dir):
            if logger:
                logger.warning(f"로그 디렉토리 {timestamp_log_dir}가 존재하지 않습니다.")
            return uploaded_files
        
        # 루트 로그 디렉토리의 파일 업로드 (공통 로그 파일)
        for item in os.listdir(timestamp_log_dir):
            item_path = os.path.join(timestamp_log_dir, item)
            
            # 숨김 파일 무시
            if item.startswith('.'):
                continue
            
            # 디렉토리가 아닌 경우 (공통 로그 파일)
            if os.path.isfile(item_path):
                s3_path = f"{self.default_s3_path}/logs/{item}"
                success = self.upload_file(item_path, s3_path)
                
                if success:
                    uploaded_files.append(s3_path)
                    message = f"공통 로그 파일 {item}을 S3 {s3_path}에 업로드했습니다."
                    
                    if logger:
                        logger.info(message)
                    else:
                        print(message)
            
            # 디렉토리인 경우 (가이드라인별 로그 디렉토리)
            elif os.path.isdir(item_path):
                guideline_id = item
                
                for log_file in os.listdir(item_path):
                    # 숨김 파일 무시
                    if log_file.startswith('.'):
                        continue
                        
                    # 로그 파일 업로드
                    log_file_path = os.path.join(item_path, log_file)
                    if os.path.isfile(log_file_path):
                        # S3 경로 설정 (가이드라인 ID 포함)
                        s3_path = f"{self.default_s3_path}/logs/{guideline_id}/{log_file}"
                        success = self.upload_file(log_file_path, s3_path)
                        
                        if success:
                            uploaded_files.append(s3_path)
                            message = f"가이드라인 {guideline_id} 로그 파일 {log_file}을 S3 {s3_path}에 업로드했습니다."
                            
                            if logger:
                                logger.info(message)
                            else:
                                print(message)
        
        return uploaded_files
    
    def upload_result_file(self, result_file_path, logger=None):
        """
        결과 파일을 S3에 업로드
        
        Args:
            result_file_path (str): 업로드할 결과 파일 경로
            logger (Logger, optional): 로깅을 위한 로거 객체
            
        Returns:
            str: 업로드된 S3 경로 또는 None(실패시)
        """
        if os.path.exists(result_file_path):
            # 파일명만 추출 (경로 제외)
            result_filename = os.path.basename(result_file_path)
            
            # S3 경로 설정
            # target_guideline이 제공된 경우 이를 사용, 아니면 파일명 그대로 사용
            if self.target_guideline:
                s3_path = f"{self.default_s3_path}/results/{self.target_guideline}.json"
            else:
                s3_path = f"{self.default_s3_path}/results/{result_filename}"
            
            success = self.upload_file(result_file_path, s3_path)
            
            if success:
                message = f"결과 파일을 S3 {s3_path}에 업로드했습니다."
                
                if logger:
                    logger.info(message)
                else:
                    print(message)
                    
                return s3_path
        
        return None
    
    def upload_pip_requirements_directly(self, logger=None):
        """
        현재 환경의 패키지 목록을 로컬 파일 생성 없이 S3에 직접 업로드
        
        Args:
            logger (Logger, optional): 로깅을 위한 로거 객체
            
        Returns:
            str: 업로드된 S3 경로 또는 None(실패시)
        """
        try:
            import subprocess
            
            # pip freeze 명령 실행하여 설치된 패키지 목록 가져오기
            process = subprocess.Popen(['pip', 'freeze'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                message = f"패키지 목록 가져오기 실패: {stderr.decode('utf-8')}"
                if logger:
                    logger.error(message)
                else:
                    print(message)
                return None
            
            # 패키지 목록 텍스트 얻기
            requirements_content = stdout.decode('utf-8')
            
            # S3에 저장할 경로 설정
            requirements_file = "requirements.txt"
            # 기본 S3 경로 활용
            s3_path = f"{self.default_s3_path}/codes/{requirements_file}"
            
            # 바이트 객체로 변환하여 S3에 직접 업로드
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_path,
                    Body=requirements_content
                )
                
                message = f"패키지 목록을 S3 {s3_path}에 직접 업로드했습니다."
                if logger:
                    logger.info(message)
                else:
                    print(message)
                
                return s3_path
            
            except Exception as e:
                message = f"S3 직접 업로드 중 오류 발생: {e}"
                if logger:
                    logger.error(message)
                else:
                    print(message)
                return None
                
        except Exception as e:
            message = f"패키지 목록 생성 중 오류 발생: {e}"
            if logger:
                logger.error(message)
            else:
                print(message)
            return None

