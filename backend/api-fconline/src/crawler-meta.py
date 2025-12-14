"""
FC Online 메타데이터 수집 API
Nexon Open API를 사용하여 선수 고유 식별자, 시즌 ID 등 메타데이터를 수집하고 저장합니다.
"""

import json
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# backend/.env 파일에서 환경변수 로드
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# 한국 시간대
KST = ZoneInfo("Asia/Seoul")


class FCOnlineMetaCrawler:
    """FC Online 메타데이터 수집 클래스"""

    # 메타데이터 API 엔드포인트 (Static API - API 키 불필요)
    SPID_URL = (
        "https://open.api.nexon.com/static/fconline/meta/spid.json"  # 선수 고유 식별자
    )
    SEASON_URL = (
        "https://open.api.nexon.com/static/fconline/meta/seasonid.json"  # 시즌 ID
    )
    SPPOSITION_URL = (
        "https://open.api.nexon.com/static/fconline/meta/spposition.json"  # 포지션
    )
    MATCHTYPE_URL = (
        "https://open.api.nexon.com/static/fconline/meta/matchtype.json"  # 매치 종류
    )
    DIVISION_URL = (
        "https://open.api.nexon.com/static/fconline/meta/division.json"  # 등급
    )

    def __init__(self, base_data_dir: str = "../data"):
        """
        Args:
            base_data_dir: 기본 데이터 저장 디렉토리 경로
        """
        # 한국 시간 기준 오늘 날짜 폴더 (YY-MM-DD 형식)
        today_kst = datetime.now(KST).strftime("%y-%m-%d")

        # 데이터 저장 디렉토리 설정 (현재 파일 기준 상대 경로)
        base_dir = Path(__file__).parent / base_data_dir
        self.meta_dir = base_dir / "meta" / today_kst

        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def _fetch_json(self, url: str) -> Optional[list]:
        """
        JSON 데이터를 가져옵니다.

        Args:
            url: API URL

        Returns:
            JSON 데이터 또는 None (실패 시)
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 요청 중 오류 발생: {e}")
            return None

    def get_spid(self) -> Optional[list]:
        """
        선수 고유 식별자(SPID) 메타데이터를 조회합니다.

        Returns:
            선수 목록 [{"id": int, "name": str}, ...]
        """
        print("📥 선수 고유 식별자(SPID) 메타데이터 조회 중...")
        data = self._fetch_json(self.SPID_URL)
        if data:
            print(f"   ✅ {len(data)}명의 선수 데이터 조회 완료")
        return data

    def get_season_id(self) -> Optional[list]:
        """
        시즌 ID 메타데이터를 조회합니다.

        Returns:
            시즌 목록 [{"seasonId": int, "className": str, "seasonImg": str}, ...]
        """
        print("📥 시즌 ID 메타데이터 조회 중...")
        data = self._fetch_json(self.SEASON_URL)
        if data:
            print(f"   ✅ {len(data)}개의 시즌 데이터 조회 완료")
        return data

    def get_spposition(self) -> Optional[list]:
        """
        포지션 메타데이터를 조회합니다.

        Returns:
            포지션 목록 [{"spposition": int, "desc": str}, ...]
        """
        print("📥 포지션 메타데이터 조회 중...")
        data = self._fetch_json(self.SPPOSITION_URL)
        if data:
            print(f"   ✅ {len(data)}개의 포지션 데이터 조회 완료")
        return data

    def get_matchtype(self) -> Optional[list]:
        """
        매치 종류 메타데이터를 조회합니다.

        Returns:
            매치 종류 목록 [{"matchtype": int, "desc": str}, ...]
        """
        print("📥 매치 종류 메타데이터 조회 중...")
        data = self._fetch_json(self.MATCHTYPE_URL)
        if data:
            print(f"   ✅ {len(data)}개의 매치 종류 데이터 조회 완료")
        return data

    def get_division(self) -> Optional[list]:
        """
        등급(디비전) 메타데이터를 조회합니다.

        Returns:
            등급 목록 [{"divisionId": int, "divisionName": str}, ...]
        """
        print("📥 등급(디비전) 메타데이터 조회 중...")
        data = self._fetch_json(self.DIVISION_URL)
        if data:
            print(f"   ✅ {len(data)}개의 등급 데이터 조회 완료")
        return data

    def save_spid(self) -> str:
        """
        선수 고유 식별자(SPID) 메타데이터를 저장합니다.

        Returns:
            저장된 파일 경로
        """
        data = self.get_spid()
        if not data:
            print("❌ SPID 데이터를 가져올 수 없습니다.")
            return ""

        filepath = self.meta_dir / "spid.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"   💾 저장 완료: {filepath}")
        return str(filepath)

    def save_season_id(self) -> str:
        """
        시즌 ID 메타데이터를 저장합니다.

        Returns:
            저장된 파일 경로
        """
        data = self.get_season_id()
        if not data:
            print("❌ 시즌 ID 데이터를 가져올 수 없습니다.")
            return ""

        filepath = self.meta_dir / "seasonid.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"   💾 저장 완료: {filepath}")
        return str(filepath)

    def save_spposition(self) -> str:
        """
        포지션 메타데이터를 저장합니다.

        Returns:
            저장된 파일 경로
        """
        data = self.get_spposition()
        if not data:
            print("❌ 포지션 데이터를 가져올 수 없습니다.")
            return ""

        filepath = self.meta_dir / "spposition.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"   💾 저장 완료: {filepath}")
        return str(filepath)

    def save_matchtype(self) -> str:
        """
        매치 종류 메타데이터를 저장합니다.

        Returns:
            저장된 파일 경로
        """
        data = self.get_matchtype()
        if not data:
            print("❌ 매치 종류 데이터를 가져올 수 없습니다.")
            return ""

        filepath = self.meta_dir / "matchtype.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"   💾 저장 완료: {filepath}")
        return str(filepath)

    def save_division(self) -> str:
        """
        등급(디비전) 메타데이터를 저장합니다.

        Returns:
            저장된 파일 경로
        """
        data = self.get_division()
        if not data:
            print("❌ 등급 데이터를 가져올 수 없습니다.")
            return ""

        filepath = self.meta_dir / "division.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"   💾 저장 완료: {filepath}")
        return str(filepath)

    def save_all_meta(self) -> dict:
        """
        모든 메타데이터를 저장합니다.

        Returns:
            저장된 파일 경로 딕셔너리
        """
        print("=" * 60)
        print("🚀 FC Online 메타데이터 수집 시작")
        print("=" * 60)

        result = {
            "spid": self.save_spid(),
            "seasonid": self.save_season_id(),
            "spposition": self.save_spposition(),
            "matchtype": self.save_matchtype(),
            "division": self.save_division(),
        }

        print("\n" + "=" * 60)
        print("🎉 메타데이터 수집 완료!")
        print("=" * 60)
        print(f"   저장 위치: {self.meta_dir}")

        return result


def save_all_metadata() -> dict:
    """
    파이프라인에서 호출할 수 있는 함수.
    모든 메타데이터를 수집하고 저장합니다.

    Returns:
        저장된 파일 경로 딕셔너리
    """
    crawler = FCOnlineMetaCrawler()
    return crawler.save_all_meta()


def main():
    """메인 함수 - 단독 실행 시 사용"""
    print("\n🎮 FC Online 메타데이터 수집")
    print("-" * 40)

    print("\n수집할 메타데이터:")
    print("  1: 선수 고유 식별자 (SPID)")
    print("  2: 시즌 ID")
    print("  3: 포지션")
    print("  4: 매치 종류")
    print("  5: 등급 (디비전)")
    print("  A: 전체")

    choice = input("\n선택하세요 (기본값: A): ").strip().upper()

    if not choice:
        choice = "A"

    crawler = FCOnlineMetaCrawler()

    if choice == "A":
        crawler.save_all_meta()
    elif choice == "1":
        crawler.save_spid()
    elif choice == "2":
        crawler.save_season_id()
    elif choice == "3":
        crawler.save_spposition()
    elif choice == "4":
        crawler.save_matchtype()
    elif choice == "5":
        crawler.save_division()
    else:
        print("❌ 잘못된 선택입니다.")


if __name__ == "__main__":
    main()
