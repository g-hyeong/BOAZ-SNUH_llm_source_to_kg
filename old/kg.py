import json

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

output = json.load(open('results/guideline_to_kg_20250325_013225.json', 'r', encoding='utf-8'))

cohort = output['cohort_data']



# Neo4j 연결 설정
class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        self.driver.close()
        
    def query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]
        
    def clear_database(self, conn):
        query = "MATCH (n) DETACH DELETE n"
        conn.query(query)
        print("데이터베이스를 초기화했습니다.")

    def create_entities(self, conn, entities):
        for entity in entities:
            # 엔티티 생성 시 라벨을 domain으로 사용하고 공백을 언더스코어로 대체
            query = """
            MERGE (e:`%s` {
                concept_name: $concept_name,
                concept_id: $concept_id,
                type: 'entity'
            })
            """ % entity['domain']
            
            conn.query(query, {
                'concept_name': entity['concept_name'],
                'concept_id': entity['concept_id']
            })
        print(f"{len(entities)}개의 개체를 생성했습니다.")

    def create_relations(self, conn, relations):
        for relation in relations:
            # 공백을 언더스코어로 대체하여 관계 생성
            query = """
            MATCH (source:`%s` {concept_name: $source})
            MATCH (target:`%s` {concept_name: $target})
            CREATE (source)-[r:`%s` {
                name: $name,
                evidence: $evidence,
                certainty: $certainty
            }]->(target)
            """ % (
                'Drug' if relation['source'] == 'Statins' else 'Measurement',
                'Measurement',
                relation['name'].upper()
            )
            
            conn.query(query, {
                'source': relation['source'],
                'target': relation['target'],
                'name': relation['name'],
                'evidence': relation['evidence'],
                'certainty': relation['certainty']
            })
        print(f"{len(relations)}개의 관계를 생성했습니다.")

    def create_cohorts(self, conn, cohorts):
        for cohort in cohorts:
            # 코호트 생성
            query = """
            CREATE (c:Cohort {
                name: $name,
                description: $description,
                primary_outcome: $primary_outcome
            })
            """
            
            conn.query(query, {
                'name': cohort['name'],
                'description': cohort['description'],
                'primary_outcome': cohort['primary_outcome']
            })

            # Inclusion Criteria 생성
            for criterion in cohort['inclusion_criteria']:
                query = """
                MATCH (c:Cohort {name: $cohort_name})
                CREATE (i:Criterion {
                    type: 'inclusion',
                    condition: $condition,
                    temporal_window: $temporal_window
                })
                CREATE (c)-[:HAS_INCLUSION_CRITERION]->(i)
                """
                
                conn.query(query, {
                    'cohort_name': cohort['name'],
                    'condition': criterion['condition'],
                    'temporal_window': criterion['temporal_window']
                })

            # Exclusion Criteria 생성
            for criterion in cohort['exclusion_criteria']:
                query = """
                MATCH (c:Cohort {name: $cohort_name})
                CREATE (e:Criterion {
                    type: 'exclusion',
                    condition: $condition,
                    temporal_window: $temporal_window
                })
                CREATE (c)-[:HAS_EXCLUSION_CRITERION]->(e)
                """
                
                conn.query(query, {
                    'cohort_name': cohort['name'],
                    'condition': criterion['condition'],
                    'temporal_window': criterion['temporal_window']
                })

            # Follow-up 생성
            for follow in cohort['follow_up']:
                query = """
                MATCH (c:Cohort {name: $cohort_name})
                CREATE (f:FollowUp {
                    measurement: $measurement,
                    timeframe: $timeframe
                })
                CREATE (c)-[:HAS_FOLLOW_UP]->(f)
                """
                
                conn.query(query, {
                    'cohort_name': cohort['name'],
                    'measurement': follow['measurement'],
                    'timeframe': follow['timeframe']
                })

        print(f"{len(cohorts)}개의 코호트와 관련 기준들을 생성했습니다.")

    # 지식그래프 생성 함수
    def create_knowledge_graph(self, conn, cohort_data):
        # 기존 데이터 삭제
        self.clear_database(conn)

        # 개체 생성
        self.create_entities(conn, cohort_data['entities'])

        # 관계 생성
        self.create_relations(conn, cohort_data['relations'])

        # 코호트 생성
        self.create_cohorts(conn, cohort_data['cohorts'])

        print("지식그래프 생성이 완료되었습니다!")




conn = Neo4jConnection(
    uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    user=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD")
)


conn.create_knowledge_graph(conn, cohort)
conn.close()