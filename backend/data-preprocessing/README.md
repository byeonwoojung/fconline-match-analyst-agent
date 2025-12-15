# FC Online 데이터 전처리 파이프라인

## 개요
Bronze → Silver → Gold 데이터 파이프라인으로 Raw 데이터를 RAG 분석용으로 변환합니다.

## 폴더 구조
```
backend/data-preprocessing/
├── src/
│   ├── bronze_to_silver_lv1.py  # Bronze → Silver 변환
│   ├── silver_to_gold.py        # Silver → Gold 변환
│   ├── config.py                # 경로 설정
│   └── utils/
│       ├── __init__.py          # 유틸리티 export
│       ├── goaltime.py          # goalTime 인코딩/디코딩
│       ├── zone.py              # 좌표→구역 변환
│       ├── schema_desc.py       # 슈팅/매치종료 타입 설명
│       └── meta_loader.py       # 메타데이터 로더 (싱글톤)
└── meta/                        # 메타데이터 (gitignore)
    ├── spid.json                # 선수 ID → 이름 매핑
    ├── seasonid.json            # 시즌 ID → 이름 매핑
    └── matchtype.json           # 매치 타입 ID → 이름 매핑

data/  (프로젝트 루트)
├── bronze/matchDetail/*.jsonl   # 원본 경기 데이터
├── silver/lv1/*.jsonl           # 변환된 경기 데이터
├── gold/
│   ├── match_summaries/         # 경기 분석 데이터
│   │   ├── match_summaries.jsonl
│   │   ├── overall_stats.json
│   │   ├── time_zone_stats.json
│   │   ├── zone_stats.json
│   │   ├── concede_patterns.json
│   │   └── player_stats.json
│   ├── community/               # (예정)
│   └── server-maintenance/      # (예정)
└── vectordb/                    # ChromaDB
```

## 사용법

### 0. 타겟 유저 설정
분석할 유저의 OUID를 `config.py`에서 설정합니다:
```python
# config.py
TARGET_OUID = "8f0b662aaa013843b965a3c6fac7e8a9"  # 예시: 철마산호랑이
```

OUID는 Nexon Open API에서 닉네임으로 조회할 수 있습니다.

### 1. 데이터 전처리
```bash
cd backend/data-preprocessing/src

# Bronze → Silver 변환
python bronze_to_silver_lv1.py

# Silver → Gold 변환
python silver_to_gold.py
```

## 파이프라인 설명

### Bronze Layer
- **소스**: Nexon API에서 수집한 matchDetail 원본
- **처리**: Raw JSON 그대로 저장
- **출력**: `data/bronze/matchDetail/*.jsonl`

### Silver Layer (Lv1)
- **입력**: Bronze matchDetail
- **처리**:
  - 선수명 매핑 (spid → 선수명, 시즌명)
  - goalTime 디코딩 (인코딩된 값 → 전/후반, 분:초)
  - 구역 정보 추가 (좌표 → 19개 구역)
  - 슈팅 타입/결과 설명 추가
- **출력**: `data/silver/lv1/*.jsonl`

### Gold Layer
- **입력**: Silver Lv1 데이터
- **처리**:
  - 경기별 자연어 서술 생성 (RAG용)
  - 전체 통계 집계
  - 시간대/구역별 패턴 분석
  - 선수별 누적 통계
- **출력**: `data/gold/match_summaries/`

## 주요 유틸리티

### goaltime.py
```python
from utils import decode_goaltime

# goalTime 디코딩
result = decode_goaltime(16777216 + 1350)  
# → {"period": "후반", "minutes": 22, "seconds": 30, "display": "후반 22:30"}
```

### zone.py
```python
from utils import get_zone, get_zone_detail

# 좌표 → 구역
zone = get_zone(0.85, 0.5)  # → "상대 중앙 페널티박스"
detail = get_zone_detail(0.85, 0.5)  # → {"zone": "...", "x_zone": "...", "y_zone": "...", "description": "..."}
```

### meta_loader.py
```python
from utils import MetaLoader

meta = MetaLoader()
player_name = meta.get_player_name(241206517)  # → "호날두"
season_name = meta.get_season_name(241)  # → "26 TOTY"
```

## goalTime 인코딩 규칙

| Period | Base Value | Add Seconds | 예시 |
|--------|------------|-------------|------|
| 전반 | 0 ~ 2^24-1 | +0s | goalTime=1350 → 전반 22:30 |
| 후반 | 2^24 ~ 2^25-1 | +2700s | goalTime=16778566 → 후반 22:30 |
| 연장전반 | 2^25 ~ 3×2^24-1 | +5400s | - |
| 연장후반 | 3×2^24 ~ 2^26-1 | +6300s | - |
| 승부차기 | ≥ 2^26 | +7200s | - |

## Zone 시스템

19개 구역 (x축 6등분 × y축 3등분 + 경기장외각)
- x=0: 자기 골대, x=1: 상대 골대
- y=0: 왼쪽, y=1: 오른쪽
