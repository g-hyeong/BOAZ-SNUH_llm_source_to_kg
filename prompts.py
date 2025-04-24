from constants import RELATIONSHIP_NAMES, ENTITY_CONCEPT_NAMES


def set_manager_agent_prompt(title, contents):
    return f"""
        IMPORTANT: Provide ONLY the requested JSON output without any explanations, introductions, or additional text.
        Your response must be a SINGLE JSON code block with triple backticks. Do not include multiple code blocks or any text outside the code block.

        ROLE: You are a manager of a team of agents.
        You are an expert in OMOP CDM as well as medications, medical diagnoses. Your main task is to extract 'entities' that can exist in OMOP CDM from the provided document and form relationships for building a knowledge graph.

        According to the OMOP CDM v5.4 framework, you need to extract objects and relationships from the document, and select the next agent to process the document.
        
        # Task: Knowledge Graph Construction & Agent Selection From Clinical Guideline (By OMOP CDM v5.4)
        
        Analyze this clinical guideline: "{title}"
        
        ## Extraction Requirements:
        
        1. ENTITIES (Nodes):
           - Extract ALL possible entities that could exist in the OMOP CDM v5.4 framework from the document
           - Identify all clinically relevant entities from the entire guideline
           - Be comprehensive and thorough in your extraction
        
        2. RELATIONS (Edges):
           - Extract ALL possible relationships that could exist in the OMOP CDM v5.4 framework from the document
           - Establish relationships between entities found in the guideline
           - Capture temporal, causal, hierarchical, and other relevant relationships
        
        3. SELECT AGENT:
           - Propose ALL possible cohort analyses that could be generated from this document
           - Select an agent that can best handle this task (either drug agent or diagnosis agent)
           - Provide rationale for your selection
        
        ## Guideline Text (ANALYZE THE ENTIRE TEXT):
        {contents}
        
        ## Your Output JSON Format:
        
        ```json
        {{
            "entities": [
                {{
                    "concept_name": "entity name following OMOP CDM concept_name",
                    "domain": "OMOP CDM domain",
                    "attributes": {{
                        "value": "numeric value if applicable",
                        "unit": "unit of measurement if applicable",
                        "threshold": "threshold value if applicable"
                    }}
                }}
            ],
            "relations": [
                {{
                    "source": "source entity name",
                    "target": "target entity name",
                    "name": "relationship name",
                    "evidence": "text from guideline supporting this relationship",
                    "certainty": "strong/moderate/weak"
                }}
            ],
            "proposed_cohort_analyses": [
                {{
                    "name": "name of proposed cohort analysis",
                    "description": "brief description of the analysis",
                    "relevance": "why this analysis is important based on the guideline",
                    "selected_agent": "drug_agent or diagnosis_agent",
                    "rationale": "detailed explanation for why this agent is best suited for the task",
                }}
            ],
            "summarized_text": "A concise summary of the key parts of the guideline that informed your entity extraction, relationship identification, agent selection, and cohort analysis recommendations. Include only the most critical information needed for analysis. However, you must use exact sentences from the original document without modification. The summary should be comprehensive enough that one can understand the entire content of the original document just by reading the summary."
        }}
        ```
        
        IMPORTANT NOTES:
        1. ANALYZE THE ENTIRE GUIDELINE TEXT - do not skip any sections
        2. Use EXACT OMOP concept_names whenever possible
        3. Ensure all entities are clinically meaningful and evidence-based
        4. Provide a clear rationale for your agent selection
        5. The selected agent must be either "drug_agent" or "diagnosis_agent"
        6. Make your selection based on the predominant focus of the guideline
        7. In the summarized_text field, include only the most relevant portions of the guideline that directly contributed to your analysis and decisions
        8. Extract only entities, relations, and cohort analyses that are DIRECTLY mentioned or implied in the given text
        9. IMPORTANT:Provide ONLY the requested JSON output without any explanations, introductions, or additional text.
    """

def set_drug_agent_prompt(manager_response):
    return f"""
        IMPORTANT: Provide ONLY the requested JSON output without any explanations, introductions, or additional text.
        Your response must be a SINGLE JSON code block with triple backticks. Do not include multiple code blocks or any text outside the code block.
        
        ROLE: You are a specialized drug agent with expertise in pharmacology, drug interactions, and medication-related clinical guidelines within the OMOP CDM framework.
        
        # Task: Detailed Cohort Analysis for Drug-Related Clinical Guidelines
        
        ## Input from Manager Agent:
        {manager_response}
        
        ## Important Note on Data Sources:
        You have access to both:
        1. The Manager Agent's analysis and summary
        2. The complete original document content
        
        ALWAYS refer to the original document content for your primary analysis to ensure maximum accuracy and comprehensiveness.
        Use the Manager's analysis only as a guide, but perform your own thorough analysis of the original text.
        
        ## Analysis Requirements:
        
        1. DRUG ENTITIES:
           - Identify ALL medications, drug classes, and pharmacological agents mentioned in the guideline
           - Map each drug entity to the appropriate OMOP CDM concept_name
           - Extract dosing information, administration routes, frequencies, and durations
           - Identify contraindications, adverse events, and drug interactions
           - ENSURE ALL DRUG ENTITIES COME DIRECTLY FROM THE ORIGINAL DOCUMENT
        
        2. DRUG-SPECIFIC RELATIONSHIPS:
           - Determine drug-condition relationships (treats, prevents, causes)
           - Identify drug-drug interactions (synergistic, antagonistic)
           - Map medication management pathways and treatment algorithms
           - Extract temporal sequences for drug administration and monitoring
           - CITE SPECIFIC SECTIONS OF THE ORIGINAL DOCUMENT AS EVIDENCE
        
        3. COHORT DEFINITIONS:
           - Create detailed cohort definitions focused on medication exposure
           - Specify precise inclusion/exclusion criteria using OMOP CDM concepts
           - Define drug exposure windows, persistence requirements, and dosing parameters
           - Establish monitoring schedules and therapeutic goals
           - BASE ALL CRITERIA ON EXPLICIT STATEMENTS IN THE ORIGINAL DOCUMENT
        
        ## Output JSON Format:
        
        ```json
        {{
            "drug_entities": [
                {{
                    "concept_name": "OMOP CDM drug concept name",
                    "drug_class": "pharmacological class if specified",
                    "dosing": {{
                        "amount": "dose amount",
                        "unit": "dose unit",
                        "frequency": "dosing frequency",
                        "route": "administration route",
                        "duration": "treatment duration"
                    }},
                    "indications": [
                        "condition for which the drug is indicated"
                    ],
                    "contraindications": [
                        "condition where the drug should not be used"
                    ],
                    "adverse_events": [
                        "potential side effects or adverse reactions"
                    ],
                    "evidence_level": "strength of recommendation (high/moderate/low)",
                    "source_text": "text from guideline mentioning this drug"
                }}
            ],
            "drug_relationships": [
                {{
                    "source_drug": "source drug concept_name",
                    "target_entity": "target entity (drug or condition) concept_name",
                    "relationship_type": "treats/prevents/interacts_with/etc.",
                    "details": "specific details about the relationship",
                    "certainty": "high/moderate/low",
                    "evidence": "text from guideline supporting this relationship"
                }}
            ],
            "treatment_pathways": [
                {{
                    "name": "name of treatment pathway",
                    "description": "description of the treatment algorithm or pathway",
                    "steps": [
                        {{
                            "order": "step number in sequence",
                            "intervention": "drug or procedure concept_name",
                            "condition": "condition to be addressed",
                            "decision_points": "criteria for moving to next step",
                            "alternatives": "alternative options at this step"
                        }}
                    ],
                    "evidence_level": "strength of recommendation (high/moderate/low)"
                }}
            ],
            "medication_cohorts": [
                {{
                    "name": "medication-focused cohort name",
                    "description": "detailed description of cohort purpose",
                    "target_population": "population for which this treatment is relevant",
                    "inclusion_criteria": [
                        {{
                            "criterion": "inclusion criterion using OMOP concept_name",
                            "time_window": "relevant time window if applicable"
                        }}
                    ],
                    "exclusion_criteria": [
                        {{
                            "criterion": "exclusion criterion using OMOP concept_name",
                            "time_window": "relevant time window if applicable"
                        }}
                    ],
                    "drug_exposures": [
                        {{
                            "drug": "drug concept_name",
                            "dose": "dose specification",
                            "duration": "exposure duration",
                            "persistence": "persistence definition (max allowed gap)",
                            "monitoring": [
                                {{
                                    "parameter": "what to monitor",
                                    "frequency": "how often to monitor",
                                    "threshold": "threshold for intervention"
                                }}
                            ]
                        }}
                    ]
                }}
            ],
            "detailed_analysis": "A comprehensive analysis of all drug-related aspects of the document, including identified medications, treatment strategies, and rationale for cohort definitions. This should directly reference the original document and be specific to the current cohort focus area."
        }}
        ```
        
        IMPORTANT NOTES:
        1. Always PRIORITIZE the ORIGINAL DOCUMENT CONTENT over the Manager's summary in your analysis
        2. Focus specifically on the current cohort analysis task when extracting information
        3. Include only medications, relationships, and cohort criteria that are explicitly mentioned in the document
        4. Provide source evidence from the original text for all entities and relationships
        5. Be comprehensive but precise in your extraction
        6. Ensure all JSON fields are properly populated based on available information
    """

def set_diagnosis_agent_prompt(manager_response):
    return f"""
        IMPORTANT: Provide ONLY the requested JSON output without any explanations, introductions, or additional text.
        Your response must be a SINGLE JSON code block with triple backticks. Do not include multiple code blocks or any text outside the code block.
        
        ROLE: You are a specialized diagnosis agent with expertise in clinical conditions, diagnostic criteria, and disease-related clinical guidelines within the OMOP CDM framework.
        
        # Task: Detailed Cohort Analysis for Disease and Diagnostic-Related Clinical Guidelines
        
        ## Input from Manager Agent:
        {manager_response}
        
        ## Important Note on Data Sources:
        You have access to both:
        1. The Manager Agent's analysis and summary
        2. The complete original document content
        
        ALWAYS refer to the original document content for your primary analysis to ensure maximum accuracy and comprehensiveness.
        Use the Manager's analysis only as a guide, but perform your own thorough analysis of the original text.
        
        ## Analysis Requirements:
        
        1. CONDITION ENTITIES:
           - Identify ALL diseases, disorders, symptoms, and clinical findings mentioned in the guideline
           - Map each condition entity to the appropriate OMOP CDM concept_name
           - Extract severity levels, stages, and classification systems where available
           - Identify risk factors, complications, and associated conditions
           - ENSURE ALL CONDITION ENTITIES COME DIRECTLY FROM THE ORIGINAL DOCUMENT
        
        2. CONDITION-SPECIFIC RELATIONSHIPS:
           - Determine condition-condition relationships (causes, complicates, is_stage_of)
           - Identify condition-procedure relationships (diagnosed_by, treated_by, screened_by)
           - Map diagnostic algorithms and disease management pathways
           - Extract temporal sequences and progression patterns
           - CITE SPECIFIC SECTIONS OF THE ORIGINAL DOCUMENT AS EVIDENCE
        
        3. COHORT DEFINITIONS:
           - Create detailed cohort definitions focused on disease states and conditions
           - Specify precise inclusion/exclusion criteria using OMOP CDM concepts
           - Define condition occurrence parameters, severity thresholds, and temporal constraints
           - Establish diagnostic criteria and assessment methods
           - BASE ALL CRITERIA ON EXPLICIT STATEMENTS IN THE ORIGINAL DOCUMENT
        
        ## Output JSON Format:
        
        ```json
        {{
            "condition_entities": [
                {{
                    "concept_name": "OMOP CDM condition concept name",
                    "condition_category": "disease category if specified",
                    "severity": "severity levels if mentioned",
                    "staging": {{
                        "system": "staging or classification system name",
                        "stage_value": "specific stage",
                        "criteria": "criteria for this staging"
                    }},
                    "risk_factors": [
                        "factors that increase risk for this condition"
                    ],
                    "complications": [
                        "conditions that can result from this condition"
                    ],
                    "evidence_level": "strength of evidence (high/moderate/low)",
                    "source_text": "text from guideline mentioning this condition"
                }}
            ],
            "condition_relationships": [
                {{
                    "source_condition": "source condition concept_name",
                    "target_entity": "target entity (condition or procedure) concept_name",
                    "relationship_type": "causes/complicates/diagnosed_by/etc.",
                    "details": "specific details about the relationship",
                    "certainty": "high/moderate/low",
                    "evidence": "text from guideline supporting this relationship"
                }}
            ],
            "diagnostic_pathways": [
                {{
                    "name": "name of diagnostic pathway",
                    "description": "description of the diagnostic algorithm or pathway",
                    "steps": [
                        {{
                            "order": "step number in sequence",
                            "test": "diagnostic test or assessment concept_name",
                            "target_condition": "condition being assessed",
                            "decision_points": "criteria for moving to next step",
                            "alternatives": "alternative diagnostic options at this step"
                        }}
                    ],
                    "evidence_level": "strength of recommendation (high/moderate/low)"
                }}
            ],
            "condition_cohorts": [
                {{
                    "name": "condition-focused cohort name",
                    "description": "detailed description of cohort purpose",
                    "target_population": "population for which this condition is relevant",
                    "inclusion_criteria": [
                        {{
                            "criterion": "inclusion criterion using OMOP concept_name",
                            "time_window": "relevant time window if applicable"
                        }}
                    ],
                    "exclusion_criteria": [
                        {{
                            "criterion": "exclusion criterion using OMOP concept_name",
                            "time_window": "relevant time window if applicable"
                        }}
                    ],
                    "condition_occurrences": [
                        {{
                            "condition": "condition concept_name",
                            "severity": "required severity level if applicable",
                            "duration": "minimum duration if applicable",
                            "diagnostic_criteria": [
                                {{
                                    "parameter": "diagnostic test or finding",
                                    "threshold": "threshold for diagnosis",
                                    "measurement_window": "time window for measurement"
                                }}
                            ]
                        }}
                    ]
                }}
            ],
            "detailed_analysis": "A comprehensive analysis of all condition-related aspects of the document, including identified diseases, diagnostic approaches, and rationale for cohort definitions. This should directly reference the original document and be specific to the current cohort focus area."
        }}
        ```
        
        IMPORTANT NOTES:
        1. Always PRIORITIZE the ORIGINAL DOCUMENT CONTENT over the Manager's summary in your analysis
        2. Focus specifically on the current cohort analysis task when extracting information
        3. Include only conditions, relationships, and cohort criteria that are explicitly mentioned in the document
        4. Provide source evidence from the original text for all entities and relationships
        5. Be comprehensive but precise in your extraction
        6. Ensure all JSON fields are properly populated based on available information
    """

def set_verify_cohort_prompt(cohort):
    return f"""
        IMPORTANT: Create only five questions.

        Claim: Viral image stated on June 8, 2020 in post on Facebook: Cops in Norway: require 3 years of training, 4 people killed since 2002. Cops in Finland: require 2 years of training, 7 people killed since 2000. Cops in Iceland: require 2 years of training, 1 person killed since ever. Cops in the U.S.: require 21 weeks of training, 8,000+ people killed since 2001.

        Suppose you are a fact-checker, generate several yes or no quesons to help me answer if this claim is true or false.

        Questions:
        Does Norway require 3 years of training for cops?
        Have Norwegian cops killed 4 people since the early 2000's?
        Does Finland require only 2 years of training for police?

        Claim: Barry DuVal stated on September 25, 2015 in an interview: We're the only major oil-producing naon in the world with a self-imposed ban on exporng our crude oil to other naons.

        Suppose you are a fact-checker, generate several yes or no quesons to help me answer if this claim is true or false.

        Questions:
        Is the U.S. the only major oil-producing naon to ban exports of crude oil?
        Is the self-imposed ban on crude oil export of U.S a complete ban?

        Claim: William Barr stated on September 2, 2020 in a CNN interview: We indicted someone in Texas, 1,700 ballots collected from people who could vote, he made them out and voted for the person he wanted to.

        Suppose you are a fact-checker, generate several yes or no quesons to help me answer if this claim is true or false.

        Questions:
        Were 1700 mail-in ballots invesgated for fraud in Texas during the 2020 elecon?
        Did the Justice Department indict someone in Texas for voter fraud?
        Did widespread mail-in order fraud happen in Texas during the 2020 elecon?

        Claim: {cohort}
        Suppose you are a fact-checker, generate several yes or no quesons to help me answer if this claim is true or false.

        Questions:
    """