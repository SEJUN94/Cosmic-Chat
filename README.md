# Cosmic Chat 🌌

FastAPI, Redis Pub/Sub, Apache Kafka, 그리고 Oracle DB를 활용한 대규모 확장형 실시간 채팅 서비스입니다.

---

## 1. 설계 및 기술 스택 선정 배경

실시간 채팅 서비스의 안정적인 실시간성 보장과 무중단 수평 확장을 고려하여 설계되었습니다.

### 🚀 FastAPI & WebSockets
* **선정 배경**: Python 진영의 비동기(Asynchronous) 프레임워크 중 최고 수준의 속도를 제공하며, WebSockets 프로토콜을 네이티브로 완벽하게 지원합니다.
* **적용 목적**: 실시간 양방향 통신을 처리하기 위해 비동기 I/O를 적극 활용하여, 동시 접속자 수가 많아도 최소한의 리소스로 연결을 유지할 수 있습니다.

### 🔴 Redis Pub/Sub & In-Memory Cache
* **선정 배경**: 웹소켓 서버를 다중 인스턴스로 수평 확장(Scale-out)할 때, 서로 다른 인스턴스에 접속한 유저 간에 메시지를 라우팅해주는 메시지 브로커가 필요합니다.
* **적용 목적**:
  1. **Pub/Sub**: `chat:*` 채널을 구독하여 다중 서버 구조에서도 모든 접속자에게 실시간 메시지를 원활하게 브로드캐스팅합니다.
  2. **List (최근 내역 캐싱)**: 채팅방 진입 시 직전 메시지 100개를 빠르게 로드하기 위해 Redis List 자료구조를 활용해 인메모리 캐싱을 수행합니다 (`LTRIM`으로 최대 100개 유지). 이를 통해 데이터베이스 조회를 최소화하고 지연 시간을 대폭 단축했습니다.

### ⚙️ Apache Kafka (Event Streaming)
* **선정 배경**: 실시간 채팅 외에 알림 전송, 데이터 분석, 감사 로그 기록 등 다양한 비즈니스 로직이 채팅 메시지 발생 시점에 유발됩니다. 이를 동기식으로 처리하면 채팅 속도에 병목이 생깁니다.
* **적용 목적**: 메시지 발생 이벤트를 Kafka 토픽(`orders`, `notifications` 등)에 발행(Publish)하여 처리함으로써, 채팅 핵심 기능과 부가 서비스 간의 결합도를 낮추고(Decoupling) 비동기식 대용량 이벤트 스트리밍 처리를 보장합니다.

### 💾 Oracle Database & SQLAlchemy (Async)
* **선정 배경**: 기업급 애플리케이션의 트랜잭션 정합성 및 시스템 설정값 관리를 위해 강력한 Oracle DB를 사용하며, 비동기 처리를 위해 SQLAlchemy의 Async Engine을 채택했습니다.
* **적용 목적**: 사용자 권한 설정이나 시스템 설정 매핑값(`TbSysValidationMap`) 조회 등 안정적이고 정합성이 필요한 데이터 영속화 레이어로 사용됩니다.

### 🎵 Web Audio API (Client Side)
* **선정 배경**: 타 사용자의 메시지 수신 시 알림음을 재생하기 위해 무거운 오디오 파일(MP3, WAV 등)을 다운로드하는 것은 네트워크 대역폭 낭비와 지연을 유발합니다.
* **적용 목적**: 브라우저 내장 Web Audio API의 `OscillatorNode`와 `GainNode`를 사용하여 코드로 부드러운 우주 종소리(Cosmic Chime) 알림음을 실시간 합성 및 재생합니다.

---

## 2. 실행 방법

### 📋 요구사항 (Prerequisites)
* Python 3.10 이상
* Docker 및 Docker Compose

### Step 1. 가상환경 구성 및 패키지 설치
프로젝트 루트 디렉토리에서 가상환경을 활성화한 후, 요구되는 의존성 패키지를 설치합니다.

```bash
# 가상환경 생성 및 활성화
python -m venv venv
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Windows (CMD)
.\venv\Scripts\activate.bat
# Linux/macOS
source venv/bin/activate

# 의존성 라이브러리 설치
pip install -r requirements.txt
# (선택) requirements.txt에 누락된 Redis, Kafka, Oracle DB 드라이버 설치
pip install redis aiokafka oracledb
```

### Step 2. 환경 변수 설정 (`.env`)
루트 디렉토리에 `.env` 파일을 생성하거나 수정합니다. 기동할 컨테이너 환경에 맞춰 `DATABASE_URL`을 설정하세요.

```env
ENVIRONMENT=development
DEBUG=true
APP_NAME="Cosmic Chat Server"

# Oracle DB 연결 정보
# 1) 로컬 Docker 컨테이너 사용 시 (추천 - Step 3 방법 A 참고)
DATABASE_URL=oracle+oracledb://admn:admn!123@localhost:1521/orcl

# 2) 외부 개발 DB 서버 사용 시
# DATABASE_URL=oracle+oracledb://admn:admn!123@119.203.251.35:1521/orcl

# Redis 설정
REDIS_URL=redis://localhost:6379/
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

HISTORY_LIMIT=100
CHANNEL_PREFIX=chat:
HISTORY_PREFIX=chat_history:

# Kafka 설정
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Step 3. Docker 인프라 실행 (Kafka, Redis, Oracle DB)
개발 환경 구축을 위해 필요한 백엔드 인프라를 Docker 컨테이너로 기동합니다.

#### 💡 방법 A. 개발용 통합 컨테이너 기동 (추천)
`image/kafka-image.yml` 파일을 사용하여 **Kafka, Redis, Oracle DB**를 한 번에 컨테이너로 띄울 수 있습니다. 별도로 로컬에 해당 미들웨어를 깔지 않아도 되어 간편합니다.

```bash
# Kafka, Redis, Oracle DB 일괄 백그라운드 기동
docker-compose -f image/kafka-image.yml up -d
```
* **기동되는 컨테이너 목록**:
  * `kafka-broker`: `localhost:9092` (KRaft 기반 단일 노드 Kafka)
  * `redis-cache`: `localhost:6379`
  * `oracle-db`: `localhost:1521` (초기 계정 `admn`/`admn!123`, 데이터베이스 `orcl` 자동 생성 및 연동)

#### ⚙️ 방법 B. 모니터링 UI 및 인증 서버 포함 기동
인증 토큰 관리를 위한 Keycloak 서버 및 Kafka 토픽 모니터링을 위한 Kafka-UI 대시보드가 필요하다면 `image/kafka-all.yml`을 실행합니다.

```bash
# Redis는 별개 컨테이너로 단독 실행
docker run --name redis -p 6379:6379 -d redis

# Kafka, Keycloak, Kafka-UI, CLI Producer/Consumer 일괄 실행
docker-compose -f image/kafka-all.yml up -d
```

### Step 4. FastAPI 애플리케이션 실행
설정이 완료되면 `uvicorn`을 통해 FastAPI 애플리케이션 서버를 실행합니다.

```bash
uvicorn app.main:app --reload --port 8000
```
서버 실행 후 브라우저에서 `http://localhost:8000/chat/` 주소로 접속하면 실시간 채팅 UI 페이지가 열립니다.

---

## 3. 테스트 및 검증 방법

### 🔍 1. Oracle DB 연결 검증
제공된 단독 테스트 스크립트를 실행하여 Oracle 데이터베이스와 비동기 연결이 원활히 이루어지는지 검증합니다.
*(Docker로 실행한 경우, oracle-db 컨테이너가 정상적으로 완전히 기동된 후 실행해야 합니다. 최초 기동 시 데이터베이스 생성 프로세스로 인해 1~2분 소요될 수 있습니다.)*

```bash
# .env의 DATABASE_URL을 로컬 주소(localhost)로 설정했는지 확인 후 실행
python test_oracle.py
```
* 성공 시 터미널에 `연결 성공!` 메시지가 출력됩니다.

### 🌐 2. Swagger UI API 테스트
FastAPI에서 자동 제공하는 OpenAPI 문서를 통해 개별 라우터의 동작 상태를 검증합니다.
* **접속 주소**: `http://localhost:8000/docs`
* **검증 대상 엔드포인트**:
  * `POST /redis/set` & `GET /redis/get/{key}`: Redis 값 저장 및 조회 검증
  * `GET /redis/rate-limit`: 요청 횟수 제한 작동 여부 검증 (1분에 최대 10회 제한 초과 시 429 오류)
  * `POST /kafka/produce`: Kafka 브로커로 테스트 토픽 메시지 발행 테스트
  * `GET /validation-maps`: Oracle DB에서 시스템 설정 테이블(`TB_SYS_VALIDATION_MAP`) 비동기 조회 검증

### 💬 3. 실시간 다중 접속 및 이미지 공유 검증
실제 멀티 세션 환경에서 메시지가 실시간으로 Pub/Sub 동기화되는지 확인합니다.
1. 브라우저 창을 2개 이상 열고 `http://localhost:8000/chat/`에 접속합니다.
2. 각각의 창에 다른 `SENDER` 이름(예: `UserA`, `UserB`)을 입력하고 **연결 시작**을 클릭합니다.
3. 한쪽 창에서 메시지를 입력한 후 전송했을 때 다른 창에 즉각 수신되는지 확인합니다.
4. **사진 첨부(📎) 버튼**을 통해 사진 파일을 전송한 경우, Base64 바이너리 스트림이 JSON 페이로드로 직렬화되어 상대방에게 이미지 카드로 렌더링되는지 확인합니다.
5. 다른 사용자가 보낸 메시지를 받을 때 웹 브라우저 스피커를 통해 알림 효과음(Chime)이 정상 작동하는지 확인합니다.

### 📊 4. Kafka & Keycloak 통합 모니터링
* **Kafka UI**: `http://localhost:8080`에 접속하여 Kafka 브로커의 활성 상태 및 `demo-topic` 등 토픽 내부 메시지를 모니터링합니다. *(방법 B 실행 시)*
* **Keycloak**: `http://auth.local:8081` 관리자 콘솔(`admin` / `Idras@2024`)로 접속하여 인증 클라이언트 정보 및 사용자 계정 관리 상태를 확인할 수 있습니다. *(방법 B 실행 시)*
