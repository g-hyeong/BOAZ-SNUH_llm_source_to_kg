from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

# 진단 결과 관련 모델
class DiagnosticEntity(BaseModel):
    concept_name: str
    condition_category: Optional[str] = None
    severity: Optional[str] = None
    staging: Optional[Dict[str, str]] = None
    risk_factors: Optional[List[str]] = None
    complications: Optional[List[str]] = None
    evidence_level: Optional[str] = None
    source_text: Optional[str] = None

class DiagnosticRelationship(BaseModel):
    source_condition: str
    target_entity: str
    relationship_type: str
    details: Optional[str] = None
    certainty: Optional[str] = None
    evidence: Optional[str] = None

class DiagnosticPathwayStep(BaseModel):
    order: str
    test: str
    target_condition: str
    decision_points: Optional[str] = None
    alternatives: Optional[str] = None

class DiagnosticPathway(BaseModel):
    name: str
    description: str
    steps: List[DiagnosticPathwayStep]
    evidence_level: Optional[str] = None

class DiagnosticCriterion(BaseModel):
    criterion: str
    time_window: Optional[str] = None

class DiagnosticParameter(BaseModel):
    parameter: str
    threshold: Optional[str] = None
    measurement_window: Optional[str] = None

class ConditionOccurrence(BaseModel):
    condition: str
    severity: Optional[str] = None
    duration: Optional[str] = None
    diagnostic_criteria: Optional[List[DiagnosticParameter]] = None

class ConditionCohort(BaseModel):
    name: str
    description: str
    target_population: str
    inclusion_criteria: List[DiagnosticCriterion]
    exclusion_criteria: Optional[List[DiagnosticCriterion]] = None
    condition_occurrences: List[ConditionOccurrence]

class DiagnosticResults(BaseModel):
    condition_entities: List[DiagnosticEntity]
    condition_relationships: List[DiagnosticRelationship]
    diagnostic_pathways: List[DiagnosticPathway]
    condition_cohorts: List[ConditionCohort]
    detailed_analysis: str

# 약물 결과 관련 모델
class DrugDosing(BaseModel):
    amount: Optional[str] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    duration: Optional[str] = None

class DrugEntity(BaseModel):
    concept_name: str
    drug_class: Optional[str] = None
    dosing: Optional[DrugDosing] = None
    indications: Optional[List[str]] = None
    contraindications: Optional[List[str]] = None
    adverse_events: Optional[List[str]] = None
    evidence_level: Optional[str] = None
    source_text: Optional[str] = None

class DrugRelationship(BaseModel):
    source_drug: str
    target_entity: str
    relationship_type: str
    details: Optional[str] = None
    certainty: Optional[str] = None
    evidence: Optional[str] = None

class TreatmentPathwayStep(BaseModel):
    order: str
    intervention: str
    condition: str
    decision_points: Optional[str] = None
    alternatives: Optional[str] = None

class TreatmentPathway(BaseModel):
    name: str
    description: str
    steps: List[TreatmentPathwayStep]
    evidence_level: Optional[str] = None

class DrugCriterion(BaseModel):
    criterion: str
    time_window: Optional[str] = None

class MonitoringParameter(BaseModel):
    parameter: str
    frequency: Optional[str] = None
    threshold: Optional[str] = None

class DrugExposure(BaseModel):
    drug: str
    dose: Optional[str] = None
    duration: Optional[str] = None
    persistence: Optional[str] = None
    monitoring: Optional[List[MonitoringParameter]] = None

class MedicationCohort(BaseModel):
    name: str
    description: str
    target_population: str
    inclusion_criteria: List[DrugCriterion]
    exclusion_criteria: Optional[List[DrugCriterion]] = None
    drug_exposures: List[DrugExposure]

class DrugResults(BaseModel):
    drug_entities: List[DrugEntity]
    drug_relationships: List[DrugRelationship]
    treatment_pathways: List[TreatmentPathway]
    medication_cohorts: List[MedicationCohort]
    detailed_analysis: str

# 검증 결과 관련 모델
class ValidationResult(BaseModel):
    status: str = Field(..., description="검증 상태 ('passed', 'failed', 'needs_review')")
    details: Dict[str, Any] = Field(default_factory=dict, description="검증 결과 상세 정보")
    questions: Optional[List[str]] = None  # 코호트 검증 관련 질문

# KG 노드와 엣지 모델
class KnowledgeGraphNode(BaseModel):
    id: str
    label: str
    properties: Dict[str, Any]

class KnowledgeGraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: Optional[Dict[str, Any]] = None