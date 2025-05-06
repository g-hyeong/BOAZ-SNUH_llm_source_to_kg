from typing import TypedDict, Optional, Literal

# omop parent
class OMOPSchema(TypedDict, total=False):
    concept_name: str
    concept_id: int
    domain_id: str
    vocabulary_id: str
    concept_code: str
    standard_concept: Literal['S', 'C']
    mapping_confidence: Optional[float]
    
# 도메인별로
class DrugSchema(OMOPSchema):
    drug_name: Optional[str]

class DiagnosticSchema(OMOPSchema):
    icd_code: Optional[str]
    snomed_code: Optional[str]

class MedicalTestSchema(OMOPSchema):
    test_name: str
    operator: Literal['=', '>', '>=', '<', '<=']
    value: float
    unit: str

class SurgerySchema(OMOPSchema):
    surgery_name: str
    
# analysis
class AnalysisSchema(TypedDict, total=False):
    drug: Optional[DrugSchema]
    diagnostic: Optional[DiagnosticSchema]
    test: Optional[MedicalTestSchema]
    surgery: Optional[SurgerySchema]
    etc: Optional[str]
    temporal_relation: Optional[str]
    source_text_span: Optional[str]