"""
데이터 전처리 파이프라인 설정
"""

from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# ============================================================================
# 타겟 유저 설정
# ============================================================================
# 분석 대상 유저의 OUID입니다.
# Nexon Open API에서 닉네임으로 OUID를 조회할 수 있습니다.
# 예시: 철마산호랑이 닉네임의 OUID
TARGET_OUID = "8f0b662aaa013843b965a3c6fac7e8a9"

# ============================================================================
# 소스 데이터 경로 (Raw Data)
# ============================================================================
SOURCE_DATA = {
    "matchDetail": PROJECT_ROOT / "backend" / "api-fconline" / "data" / "matchDetail",
    "meta": PROJECT_ROOT / "backend" / "api-fconline" / "data" / "meta",
    "community": PROJECT_ROOT / "backend" / "crawler-fconline-community" / "data",
    "server-maintenance": PROJECT_ROOT
    / "backend"
    / "crawler-fconline-server-maintenance"
    / "data",
}

# ============================================================================
# 타겟 데이터 경로 (Bronze / Silver / Gold)
# ============================================================================
DATA_ROOT = PROJECT_ROOT / "data"

BRONZE_DATA = {
    "matchDetail": DATA_ROOT / "bronze" / "matchDetail",
    "meta": DATA_ROOT / "bronze" / "meta",
    "community": DATA_ROOT / "bronze" / "community",
    "server-maintenance": DATA_ROOT / "bronze" / "server-maintenance",
}

SILVER_DATA = {
    "matchDetail": DATA_ROOT / "silver" / "matchDetail",
    "community": DATA_ROOT / "silver" / "community",
    "server-maintenance": DATA_ROOT / "silver" / "server-maintenance",
}

GOLD_DATA = {
    "match_summaries": DATA_ROOT / "gold" / "match_summaries",
    "user_stats": DATA_ROOT / "gold" / "user_stats",
    "community": DATA_ROOT / "gold" / "community",
}

VECTORDB_PATH = DATA_ROOT / "vectordb"

# ============================================================================
# 파일명 설정
# ============================================================================
OUTPUT_FILES = {
    "matchDetail": "matchDetail.jsonl",
    "community": "community.jsonl",
    "server-maintenance": "server-maintenance.jsonl",
}

# 메타데이터 파일명
META_FILES = [
    "spid.json",
    "seasonid.json",
    "matchtype.json",
    "division.json",
    "spposition.json",
]
