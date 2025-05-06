from ..schema.types import *
from typing import List, Dict, Any, Annotated
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
    
class CohortGraphState(TypedDict):
    context: Annotated[str, operator.add]
    question: Annotated[str, 'cohort extraction prompt']
    answer: Annotated[str, 'llm answer']
    is_valid: Annotated[bool, 'whether cohort validation was successful']
    retries: Annotated[int, 'retry count']
    source_reference_number: Annotated[str, 'NICE Guideline referece Number']
    source_contents: Annotated[str, 'NICE Guideline contents']
    cohort_result: Annotated[List[Dict[str, Any]], 'cohort Result']
