# Phase 2. Raft 기반 Leader 선출

## 역할, 범위, 그리고 설계

Leader 선출만 Raft 기반 방식 Control plane의 역할만 고려
- 데이터 복제와는 무관, "누가 write가 가능한가" 만 합의
- Leader 장애 시, 나머지 Replica 중 하나가 자동으로 승격
- 데이터 복제는 Phase 1 방식을 유지 

따라서 Phase 2에서의 구현 범위는
- 구현 범위
  - Raft API 설계 (heartbeat + vote for Leader election)
  - API endpoint to check leader
  - SQLite read-only <-> read-write 전환
  - nginx write proxying
  - node 수는 3개로 일단 고정..

- PoC 수준에서 고려 대상 X
  - log replication
  - snapshot
  - WAL truncate / checkpoint coordination

### 전체 Architecture
```
┌──────────┐      WAL Pull     ┌──────────┐
│ Leader   │  ─────────────>   │ Replica  │
│ SQLite   │                   │ SQLite   │
└────┬─────┘                   └────┬─────┘
     │                              │
     │ write                        │ read
     ▼                              ▼
┌──────────────────────────────────────────┐
│                  nginx                   │
│  POST/PUT  → leader                      │
│  GET       → replicas                    │
└──────────────────────────────────────────┘
 ---------------------------------- phase 1
        ▲
        │ Raft (Control Plane)
        ▼

┌────────┬────────┬────────┐
│ Node A │ Node B │ Node C │
│ raftd  │ raftd  │ raftd  │
└────────┴────────┴────────┘
```
각 컨테이너는 아래와 같은 요소로 구성
- SQLite
- WAL Pull Worker
- Raft Agent (sidecar or embedded)

### Leader node 선출 흐름
Leader node가 정상일 때
- Leader node가 주기적으로 heartbeat 전송
- 각 Follower node는 leader_id 유지

Leader node가 비정상일 때
- heartbeat timeout
- follower node의 role 변경 (follower -> candidate)
- RequestVote(term, node_id)
- 과반수 득표 한 candidate node만 leader role, 나머지는 다시 follower

### 새로운 Leader node가 될 수 있는 조건
Leader의 조건
- SQLite WAL이 항상 가장 최신
- 다른 node보다 항상 큰 offset
---

## Raft API

각 노드는 아래 상태를 메모리 + 최소 파일 저장로 갖고 있어야 함
```python
node_id: str

current_term: int
voted_for: Optional[str]

role: "follower" | "candidate" | "leader"
leader_id: Optional[str]

last_heartbeat_ts: float

```

### endpoints
#### `POST /raft/heartbeat`
Leader node가 다른 각 node로 주기적으로 호출

ex) **request**
```json
{"term": 3, "leader_id": "node-a"}
```
ex) **response (success)**
```json
{"term": 3, "success": true}
```
처리 규칙
1. term < current_term → reject
2. term = current_term
   - current_term = term
   - leader_id = leader_id
   - role = follower
2. term > current_term
   - last_heartbeat_ts = now


#### `POST /raft/request_vote`
cadidate node가 다른 각 node로 선거 시작 요청

ex) **request**
```json
{
  "term": 4,
  "candidate_id": "node-b",
  "wal_offset": 8192
}
```
ex) **response (success)**
```json
{
  "term": 4,
  "vote_granted": true
}
```
##### vote 승인 규칙
follower node는 아래 조건을 만족할 때만 선거를 허용

1. term >= local.current_term

2. local.voted_for is None or local.voted_for == candidate_id

3. wal_offset >= local.wal_offset

#### `GET /raft/state`
상태 확인 용 (디버깅 목적)

ex) **response (success)**
```json
{
  "node_id": "node-b",
  "role": "leader",
  "term": 4,
  "leader_id": "node-b",
  "wal_offset": 8192
}
```

#### `GET /raft/leader`
nginx 연동 용

ex) **response (success)**
```json
{
  "term": 4,
  "leader_id": "node-b"
}
```