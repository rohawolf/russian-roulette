# Phase 2. Raft 기반 Leader 선출
- 데이터 복제와는 무관, "누가 write가 가능한가" 만 합의
- Leader 장애 시, 나머지 Replica 중 하나가 자동으로 승격
