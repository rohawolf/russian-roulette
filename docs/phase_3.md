# Phase 3. Nginx 레벨 Write Proxing
- 모든 노드는 동일한 엔드포인트 제공
- Nginx 가 요청 분기
  - GET -> 로컬 처리
  - POST / PUT / DELETE -> Leader 노드로 Proxy
- application은 변경 X