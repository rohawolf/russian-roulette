# Phase 1. SQLite WAL Sync
- SQLite를 WAL 모드로 실행
- 다수의 Leader / Replica nodes 형태로 구성
- Leader의 WAL 기준으로 Replica sync
- Replica는 read-only
- Leader는 고정으로 시작

## WAL Pull sync vs Stream sync
### Pull sync
Leader node 에게 WAL 상태 조회 후 필요한 WAL chunk (offset 이후 부분)를 Replica node가 가져오는 방식.

#### 장점
- 구현 단순
- 장애 복구에 강함
- 비동기
#### 단점
- 지연 발생가능성이 높음
- 실시간성 보장 X

### Stream sync
Leader node가 WAL 변경을 실시간으로 push

#### 장점
- 상대적으로 낮은 지연시간
- 거의 실시간 consistency 보장

#### 단점
- 구현 난이도 올라감
- 장애 복잡도 증가
- fan-out 시 Leader node의 부하 증가

### 비교
| 항목        | WAL Pull   | WAL Stream |
| --------- | ---------- | ---------- |
| 구현 난이도    | ⭐ 낮음       | 🔥 높음      |
| 지연        | Polling 기준 | 거의 실시간     |
| 장애 복구     | 매우 쉬움      | 복잡         |
| Leader 부하 | 낮음         | 높음         |
| PoC 적합성   | ⭐⭐⭐⭐       | ⭐⭐         |

> 그래서 초반에는 WAL Pull Sync로 진행한다.

### extra
- Pull → Stream 은 고도화 가능
- Stream → Pull 은 거의 불가능
---

## Offset 기반 WAL Pulling 설계

### Offset 기반 WAL Pulling 이란?
Replica가 “나는 WAL을 여기까지 적용했다”라는 위치(offset)를 기억하고
그 이후의 변경분만 Leader에게 요청하는 방식

- WAL 파일 전체 복사 X
- 주기적 snapshot X
- append-only 로그를 따라가는 구조

### SQLite WAL 에서의 offset
SQLite WAL 구조 (개념적)
```
[WAL Header]
[Frame 1]
[Frame 2]
[Frame 3]
...
```
- 단순한 텍스트 로그 X, 고정 포맷의 binary log
- 여러 개의 frame으로 구성됨
- 각 frame은 page number, commit marker, checksum, payload 등의 정보로 구성되어 있다.

초반에는 아래와 같이 정의한 offset을 사용해보려고 한다.
> WAL file byte offset
- "몇 byte까지 읽었다"
- 구현 단순
- resume 쉬움
- frame index 단위로 가도 되지만, 초반이니까..

### Leader node - WAL API 설계
API 를 통해 offset 이후의 WAL chunk 를 제공
#### endpoints
```GET /internal/wal```
#### query parameters
| 파라미터        | 필수 | 설명                                 |
| ----------- | -- | ---------------------------------- |
| `offset`    | ✅  | replica가 마지막으로 적용한 WAL byte offset |
| `max_bytes` | ❌  | 한 번에 받을 최대 byte 수 (기본값 있음)         |
#### request example
```GET /internal/wal?offset=1048576&max_bytes=262144```
> offset - 1048576 이후 최대 262144 byte의 WAL chunk 요청

#### response formats
##### 정상 응답 (200 OK)

Body
- raw binary WAL chunk (byte stream)

Headers
```
X-WAL-Start-Offset: 1048576 # 요청한 offset
X-WAL-End-Offset: 1310719   # 이번 응답의 마지막 offset
X-WAL-Current-Size: 2097152 # leader 기준 WAL 전체 크기
```

##### 더 이상 줄 게 없을 때 (204 No Content)
```
HTTP/1.1 204 No Content
X-WAL-Start-Offset: 1048 # 요청한 offset
X-WAL-Current-Size: 1048 # leader 기준 WAL 최신 offset
```

#### Leader 내부 로직 (구조만..)
```python
def serve_wal(offset, max_bytes):
    wal_path = "sqlite.db-wal"
    wal_size = os.path.getsize(wal_path)

    if offset >= wal_size:
        return 204, None

    read_size = min(max_bytes, wal_size - offset)

    with open(wal_path, "rb") as f:
        f.seek(offset)
        data = f.read(read_size)

    return 200, data + headers
```

### Replica node - WAL Pull Worker 설계
Replica node는 "DB 노드"가 아니라 WAL replay 만 하도록..
- WAL을 따라가기만 한다.
- read-only SQLite 제공
#### **(!) Replica node SQLite 실행 모드**
read-only + WAL 가능 조합을 써야 한다.
##### SQLite Open flags
- ```mode=ro``` (read-only)
- ```journal_mode=WAL```
- ```immutable=1``` X (쓰지 말 것, WAL append 때문)
#### SQLite file tree 및 offset 정보 저장 위치
```
/data/
 ├─ sqlite.db
 ├─ sqlite.db-wal
 ├─ sqlite.db-shm
 └─ wal_offset.meta
```
*wal_offset.meta*
```
1310719
```
- plain text
- fsync 권장
- SQLite 안에 저장 X

#### WAL Pull Loop
```
while True:
  1. offset 로드
    - wal_offset.meta 읽음, 없으면 0
  2. leader node에게 WAL 요청
  3. 응답 처리
    - 200 OK
        - WAL chunk 수신
        - headers 에서 X-WAL-End-Offset 확인
    - 204 No Content
        - 최신 상태
        - sleep
    - Error
        - logging
        - backoff
            - 연속 실패 시
                sleep 시간 증가 (exponential backoff)
            - 성공 시
                sleep 리셋
        - retry
  4. WAL append
    - append mode ( open("sqlite.db-wal", "ab") )
    - fsync
  5. SQLite에 반영 (WAL append 이후 자동 반영)
  6. offset 업데이트
    - X-WAL-End-Offset -> wal_offset.meta
    - fsync
  7. sleep
```

#### 장애 시나리오
##### Replica-node 중단 후 재시작
- ```wal_offset.meta``` 로드
- offset 이후부터 다시 pull

##### Leader-node 일시 장애
- WAL API timeout
- Replica는 read-only 상태 유지
- 데이터는 stale하지만 갠춘

##### Replica-node WAL 파일 손상
- 초기 버전에서는 Replica-node 제거 후 재생성
- 나중에는 snapshot fallback 고려