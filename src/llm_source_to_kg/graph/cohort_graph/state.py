from schema.state import *
from typing import List, Dict, Any, Annotated
import operator

    
class CohortGraphState(TypedDict):
    context: Annotated[str, operator.add]
    question: Annotated[str, 'cohort extraction prompt']
    answer: Annotated[str, 'llm answer']
    is_valid: Annotated[bool, 'whether cohort validation was successful']
    retries: Annotated[int, 'retry count']
    source_reference_number: Annotated[str, 'NICE Guideline referece Number']
    source_contents: Annotated[str, 'NICE Guideline contents']
    cohort_result: Annotated[List[Dict[str, Any]], 'cohort Result']
