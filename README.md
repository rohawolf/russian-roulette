# russian-roulette

> 여러 개의 서버 컨테이너는 각각 로컬 SQLite 파일을 갖고 있지만, 외부에서는 하나의 SQLite 데이터베이스를 활용하는 것처럼 만들어보기

(.feat ChatGPT-5)

## 시스템 관점에서의 구조
각 컨테이너는:
- 자체적인 sqlite.db 보유
- 동일한 application 실행
- 동일한 HTTP API 노출

그러나 시스템 전체에서는:
- **동시에 write 가능한 노드는 하나**
- 나머지는 read-only Replica
- write 요청은 자동으로 Leader로 전달
- 데이터 복제는 application 과 무관

## Phase 1
[SQLite WAL Sync](./docs/phase_1.md)

## Phase 2
[Raft 기반 Leader 선출](./docs/phase_2.md)

## Phase 3
[Nginx 레벨 Write Proxing](./docs/phase_3.md)