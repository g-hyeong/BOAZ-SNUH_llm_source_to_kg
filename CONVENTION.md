# BOAZ-SNUH LLM Source to Knowledge Graph - Collaboration Convention

## 협업 컨벤션

이 프로젝트는 다음과 같은 협업 방식과 컨벤션을 따릅니다:

### 이슈 기반 작업

- 모든 작업은 Issue를 기반으로 진행합니다.
- 작업할 디렉터리나 파일을 이슈에 명시하여 작업 영역이 겹치지 않도록 합니다.
- 지정한 디렉터리/파일 외 다른 파일을 수정할 경우:
  - Issue 페이지에서 전체 팀원을 언급하거나
  - PR 시 전체 팀원을 Reviewer로 등록해야 합니다.

### 브랜치 컨벤션

브랜치명은 작업 종류와 이슈 번호를 포함해야 합니다:

```
{작업유형}/{이슈번호}-{브랜치명}
```

예시:
- `feat/13-add-graph-parser`
- `refactor/27-optimize-llm-module`
- `fix/42-memory-leak`

### 커밋 컨벤션

커밋 메시지에는 이슈 번호를 포함해야 합니다:

```bash
git commit -m "Feat: {commit_message}" -m "Refs: #{issue_number}"
```

예시:
```bash
git commit -m "Feat: 그래프 파서 구현" -m "Refs: #13"
```

### PR(Pull Request) 컨벤션

PR 제목에는 이슈 번호를 명시해야 합니다:

```
[#{issue_number}] {PR_title}
```

예시:
- `[#17] LLM 프롬프트 최적화 구현`
