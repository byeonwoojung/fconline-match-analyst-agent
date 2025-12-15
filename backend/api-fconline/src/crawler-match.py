"""
FC Online 매치 기록 조회 및 저장 API
Nexon Open API를 사용하여 OUID로 유저의 매치 기록을 조회하고 JSONL 형식으로 저장합니다.
"""

import json
import os
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# backend/.env 파일에서 환경변수 로드
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# 한국 시간대
KST = ZoneInfo("Asia/Seoul")


class FCOnlineMatchCrawler:
    """FC Online 매치 기록 조회 및 저장 클래스"""

    # API 엔드포인트
    MATCH_LIST_URL = "https://open.api.nexon.com/fconline/v1/user/match"
    MATCH_DETAIL_URL = "https://open.api.nexon.com/fconline/v1/match-detail"

    # 매치 타입 코드
    MATCH_TYPES = {
        50: "공식경기",
        52: "감독모드",
        30: "리그 친선",
        40: "클래식 1on1",
        # 필요에 따라 추가
    }

    def __init__(self, api_key: str, base_data_dir: str = "../data"):
        """
        Args:
            api_key: Nexon Open API 키
            base_data_dir: 기본 데이터 저장 디렉토리 경로
        """
        self.api_key = api_key
        self.headers = {"x-nxopen-api-key": api_key}

        # 한국 시간 기준 오늘 날짜 폴더 (YY-MM-DD 형식)
        today_kst = datetime.now(KST).strftime("%y-%m-%d")

        # 데이터 저장 디렉토리 설정 (현재 파일 기준 상대 경로)
        base_dir = Path(__file__).parent / base_data_dir
        self.match_dir = base_dir / "match" / today_kst  # 매치 ID 목록 저장
        self.match_detail_dir = (
            base_dir / "matchDetail" / today_kst
        )  # 매치 상세 정보 저장

        self.match_dir.mkdir(parents=True, exist_ok=True)
        self.match_detail_dir.mkdir(parents=True, exist_ok=True)

    def get_match_ids(
        self, ouid: str, match_type: int = 50, offset: int = 0, limit: int = 100
    ) -> Optional[List[str]]:
        """
        유저의 매치 ID 목록을 조회합니다.

        Args:
            ouid: 유저 계정 식별자
            match_type: 매치 종류 (기본값: 50 - 공식경기)
            offset: 조회 시작 위치
            limit: 조회 개수 (최대 100)

        Returns:
            매치 ID 목록 또는 None (조회 실패 시)
        """
        params = {
            "ouid": ouid,
            "matchtype": match_type,
            "offset": offset,
            "limit": min(limit, 100),  # 최대 100개
        }

        try:
            response = requests.get(
                self.MATCH_LIST_URL, headers=self.headers, params=params
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            self._handle_http_error(response, e)
            return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 요청 중 오류 발생: {e}")
            return None

    def get_match_detail(self, match_id: str) -> Optional[dict]:
        """
        매치 상세 정보를 조회합니다.

        Args:
            match_id: 매치 ID

        Returns:
            매치 상세 정보 딕셔너리 또는 None (조회 실패 시)
        """
        params = {"matchid": match_id}

        try:
            response = requests.get(
                self.MATCH_DETAIL_URL, headers=self.headers, params=params
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            self._handle_http_error(response, e)
            return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 요청 중 오류 발생: {e}")
            return None

    def get_all_matches(
        self,
        ouid: str,
        match_type: int = 50,
        max_matches: Optional[int] = None,
        delay: float = 0.1,
    ) -> List[str]:
        """
        유저의 모든 매치 ID를 조회합니다 (페이지네이션 처리).

        Args:
            ouid: 유저 계정 식별자
            match_type: 매치 종류
            max_matches: 최대 조회 매치 수 (None이면 전체)
            delay: API 호출 간 딜레이 (초)

        Returns:
            전체 매치 ID 목록
        """
        all_match_ids = []
        offset = 0
        limit = 100

        print(
            f"📊 매치 ID 목록 조회 시작 (매치 타입: {self.MATCH_TYPES.get(match_type, match_type)})"
        )

        while True:
            match_ids = self.get_match_ids(ouid, match_type, offset, limit)

            if match_ids is None:
                print(f"[WARN] offset {offset}에서 조회 실패")
                break

            if not match_ids:
                print(f"✅ 더 이상 매치가 없습니다. (총 {len(all_match_ids)}개)")
                break

            all_match_ids.extend(match_ids)
            print(f"   조회 완료: {len(all_match_ids)}개 매치")

            # 최대 매치 수 제한 확인
            if max_matches and len(all_match_ids) >= max_matches:
                all_match_ids = all_match_ids[:max_matches]
                print(f"✅ 최대 조회 수 도달 ({max_matches}개)")
                break

            # 다음 페이지
            if len(match_ids) < limit:
                print(f"✅ 마지막 페이지 도달 (총 {len(all_match_ids)}개)")
                break

            offset += limit
            time.sleep(delay)  # Rate limit 방지

        return all_match_ids

    def crawl_and_save_matches(
        self,
        ouid: str,
        match_type: int = 50,
        max_matches: Optional[int] = None,
        delay: float = 0.1,
    ) -> dict:
        """
        유저의 매치 기록을 조회하고 JSONL 파일로 저장합니다.
        매치 ID 목록은 match 폴더에, 매치 상세 정보는 matchDetail 폴더에 저장됩니다.

        Args:
            ouid: 유저 계정 식별자
            match_type: 매치 종류
            max_matches: 최대 조회 매치 수
            delay: API 호출 간 딜레이 (초)

        Returns:
            저장된 파일 경로 딕셔너리 {"match": str, "match_detail": str}
        """
        # 1. 매치 ID 목록 조회
        match_ids = self.get_all_matches(ouid, match_type, max_matches, delay)

        if not match_ids:
            print("❌ 조회된 매치가 없습니다.")
            return {"match": "", "match_detail": ""}

        # 2. 파일명 생성 (ouid_matchtype_timestamp.jsonl)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ouid}_{match_type}_{timestamp}.jsonl"

        match_filepath = self.match_dir / filename
        match_detail_filepath = self.match_detail_dir / filename

        # 3. 매치 ID 목록 저장 (match 폴더)
        print(f"\n📁 매치 ID 목록 저장 중...")
        with open(match_filepath, "w", encoding="utf-8") as f:
            for match_id in match_ids:
                f.write(json.dumps({"matchId": match_id}, ensure_ascii=False) + "\n")
        print(f"   저장 완료: {match_filepath}")

        # 4. 매치 상세 정보 조회 및 저장 (matchDetail 폴더)
        print(f"\n📥 매치 상세 정보 조회 및 저장 시작...")
        success_count = 0
        fail_count = 0

        with open(match_detail_filepath, "w", encoding="utf-8") as f:
            for i, match_id in enumerate(match_ids, 1):
                match_detail = self.get_match_detail(match_id)

                if match_detail:
                    # JSONL 형식으로 한 줄씩 저장
                    f.write(json.dumps(match_detail, ensure_ascii=False) + "\n")
                    success_count += 1
                else:
                    fail_count += 1

                # 진행 상황 출력
                if i % 10 == 0 or i == len(match_ids):
                    print(
                        f"   진행: {i}/{len(match_ids)} (성공: {success_count}, 실패: {fail_count})"
                    )

                time.sleep(delay)  # Rate limit 방지

        print(f"\n✅ 저장 완료!")
        print(f"   매치 ID 파일: {match_filepath}")
        print(f"   매치 상세 파일: {match_detail_filepath}")
        print(f"   총 매치: {len(match_ids)}개")
        print(f"   상세 정보 - 성공: {success_count}개, 실패: {fail_count}개")

        return {
            "match": str(match_filepath),
            "match_detail": str(match_detail_filepath),
        }

    def _handle_http_error(self, response: requests.Response, error: Exception):
        """HTTP 에러를 처리합니다."""
        if response.status_code == 400:
            print(f"[ERROR] 잘못된 요청입니다: {error}")
        elif response.status_code == 401:
            print(f"[ERROR] 인증 실패 - API 키를 확인해주세요: {error}")
        elif response.status_code == 404:
            print(f"[ERROR] 리소스를 찾을 수 없습니다: {error}")
        elif response.status_code == 429:
            print(f"[ERROR] 요청 한도 초과 - 잠시 후 다시 시도해주세요: {error}")
        elif response.status_code == 500:
            print(f"[ERROR] 서버 내부 오류: {error}")
        else:
            print(f"[ERROR] HTTP 오류 발생: {error}")


def crawl_matches_by_ouid(
    ouid: str, match_type: int = 50, max_matches: Optional[int] = None
) -> dict:
    """
    파이프라인에서 호출할 수 있는 함수.
    OUID를 입력받아 매치 기록을 조회하고 JSONL로 저장합니다.

    Args:
        ouid: 유저 계정 식별자
        match_type: 매치 종류 (기본값: 50 - 공식경기)
        max_matches: 최대 조회 매치 수 (None이면 전체)

    Returns:
        저장된 파일 경로 딕셔너리 {"match": str, "match_detail": str}
    """
    api_key = os.getenv("NEXON_API_KEY")

    if not api_key:
        raise ValueError("NEXON_API_KEY 환경변수가 설정되지 않았습니다.")

    crawler = FCOnlineMatchCrawler(api_key)
    return crawler.crawl_and_save_matches(ouid, match_type, max_matches)


def main():
    """메인 함수 - 단독 실행 시 사용"""
    api_key = os.getenv("NEXON_API_KEY", "YOUR_API_KEY_HERE")

    if api_key == "YOUR_API_KEY_HERE":
        print("⚠️  API 키를 설정해주세요.")
        print("   환경변수 NEXON_API_KEY를 설정하거나 코드에서 직접 입력하세요.")
        print("   API 키는 https://openapi.nexon.com 에서 발급받을 수 있습니다.")
        return

    # OUID 입력
    ouid = input("조회할 OUID를 입력하세요: ").strip()

    if not ouid:
        print("❌ OUID를 입력해주세요.")
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

    # 크롤링 실행
    crawler = FCOnlineMatchCrawler(api_key)
    result = crawler.crawl_and_save_matches(ouid, match_type, max_matches)

    if result["match"] and result["match_detail"]:
        print(f"\n🎉 크롤링 완료!")
        print(f"   매치 ID 파일: {result['match']}")
        print(f"   매치 상세 파일: {result['match_detail']}")


if __name__ == "__main__":
    main()
