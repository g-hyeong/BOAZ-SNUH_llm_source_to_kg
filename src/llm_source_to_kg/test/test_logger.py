# poetry run test-logger

from llm_source_to_kg.utils.logger import get_logger

def test_logger():
    logger = get_logger() # 메인 로거 (logs/MMDDHHMM/main.log 파일에 저장)

    logger.info("메인 로거 테스트")
    logger.debug("디버그 로그")
    logger.warning("경고 로그")
    logger.error("에러 로그")
    logger.critical("치명적 에러 로그")


    doc_logger = get_logger(name="문서번호") # logs/MMDDHHMM/문서번호.log 파일에 저장
    doc_logger.info("문서 로거 테스트")
    doc_logger.debug("디버그 로그")
    doc_logger.warning("경고 로그")
    doc_logger.error("에러 로그")
    doc_logger.critical("치명적 에러 로그")

    doc_logger.close()  # 임시 로거 다 쓰면 지워주기

    custom_logger = get_logger(name="별도 로거 생성") # logs/MMDDHHMM/별도 로거 생성.log 파일에 저장
    custom_logger.info("별도 로거 테스트")
    custom_logger.debug("디버그 로그")
    custom_logger.warning("경고 로그")
    custom_logger.error("에러 로그")
    custom_logger.critical("치명적 에러 로그")

    custom_logger.close()  # 임시 로거 다 쓰면 지워주기



    logger.info("로거 테스트 완료")
    logger.close()  # 메인 로거 닫기

def main():
    test_logger()

if __name__ == "__main__":
    main()
