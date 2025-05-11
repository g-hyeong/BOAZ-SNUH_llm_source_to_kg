<<<<<<< HEAD
from src.llm_source_to_kg.schema.types import *
from typing import Dict, Any, Annotated
=======
from schema.state import *
from typing import List, Dict, Any, Annotated
>>>>>>> 1ec1faa (Chore: src를 프로젝트 루트 디렉터리로 설정. import 구문 간단하게 변경)
import operator


class AnalysisGraphState(TypedDict):
    context: Annotated[str, operator.add]
    question: Annotated[str, "user question"]
    answer: Annotated[str, "llm answer"]
    source_reference_number: Annotated[str, "NICE Guideline reference Number"]
    is_valid: Annotated[bool, "Whether analysis validation was successful"]
    retries: Annotated[int, "Retry count"]
    cohort: Annotated[Dict[str, Any], "Each cohort analysis result from CohortGraphState"]
    analysis: Annotated[AnalysisSchema, "Analysis result"]
