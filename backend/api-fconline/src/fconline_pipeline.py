"""
FC Online 데이터 수집 파이프라인
닉네임 → OUID 조회 → 매치 기록 수집 → JSONL 저장
"""

import os
import sys
import importlib
from pathlib import Path
from dotenv import load_dotenv

# backend/.env 파일에서 환경변수 로드
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# 하이픈이 포함된 모듈명 import
crawler_ouid = importlib.import_module("crawler-ouid")
crawler_match = importlib.import_module("crawler-match")

FCOnlineOUIDCrawler = crawler_ouid.FCOnlineOUIDCrawler
FCOnlineMatchCrawler = crawler_match.FCOnlineMatchCrawler


def run_pipeline(
    nickname: str, match_type: int = 50, max_matches: int | None = None
) -> dict:
    """
    FC Online 데이터 수집 파이프라인 실행

    Args:
        nickname: 구단주 닉네임
        match_type: 매치 종류 (기본값: 50 - 공식경기)
        max_matches: 최대 조회 매치 수 (None이면 전체)

    Returns:
        결과 딕셔너리 {
            "nickname": str,
            "ouid": str,
            "match_file": str,
            "match_detail_file": str
        }
    """
    api_key = os.getenv("NEXON_API_KEY")

    if not api_key:
        raise ValueError(
            "NEXON_API_KEY 환경변수가 설정되지 않았습니다. backend/.env 파일을 확인해주세요."
        )

    print("=" * 60)
    print("🚀 FC Online 데이터 수집 파이프라인 시작")
    print("=" * 60)

    # Step 1: OUID 조회
    print(f"\n📌 Step 1: OUID 조회")
    print(f"   닉네임: {nickname}")

    ouid_crawler = FCOnlineOUIDCrawler(api_key)
    ouid = ouid_crawler.get_ouid(nickname)

    if not ouid:
        print(f"\n❌ 파이프라인 실패: '{nickname}' 닉네임의 OUID를 조회할 수 없습니다.")
        return {
            "nickname": nickname,
            "ouid": None,
            "match_file": None,
            "match_detail_file": None,
        }

    print(f"   ✅ OUID: {ouid}")

    # Step 2: 매치 기록 수집 및 저장
    print(f"\n📌 Step 2: 매치 기록 수집")

    match_crawler = FCOnlineMatchCrawler(api_key)
    result = match_crawler.crawl_and_save_matches(
        ouid=ouid, match_type=match_type, max_matches=max_matches
    )

    # 결과 출력
    print("\n" + "=" * 60)
    print("🎉 파이프라인 완료!")
    print("=" * 60)
    print(f"   닉네임: {nickname}")
    print(f"   OUID: {ouid}")
    print(f"   매치 ID 파일: {result['match']}")
    print(f"   매치 상세 파일: {result['match_detail']}")

    return {
        "nickname": nickname,
        "ouid": ouid,
        "match_file": result["match"],
        "match_detail_file": result["match_detail"],
    }


def main():
    """메인 함수 - CLI 실행"""
    print("\n🎮 FC Online 데이터 수집 파이프라인")
    print("-" * 40)

    # 닉네임 입력
    nickname = input("조회할 구단주 닉네임을 입력하세요: ").strip()

    if not nickname:
        print("❌ 닉네임을 입력해주세요.")
        return

    # 매치 타입 선택
    print("\n매치 타입:")
    print("  50: 공식경기 (기본값)")
    print("  52: 감독모드")
    print("  30: 리그 친선")
    print("  40: 클래식 1on1")

    match_type_input = input("매치 타입을 입력하세요 (기본값: 50): ").strip()
    match_type = int(match_type_input) if match_type_input else 50

    # 최대 매치 수 입력
    max_input = input("최대 조회 매치 수를 입력하세요 (전체: Enter): ").strip()
    max_matches = int(max_input) if max_input else None

    # 파이프라인 실행
    run_pipeline(nickname, match_type, max_matches)


if __name__ == "__main__":
    main()
