"""
메타데이터 로더
- spid.json: 선수 ID → 선수명
- seasonid.json: 시즌 ID → 시즌명
- matchtype.json: 매치타입 코드 → 매치명
- division.json: 디비전 코드 → 등급명
- spposition.json: 포지션 코드 → 포지션명
"""

import json
from pathlib import Path
from typing import Dict, Optional
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import BRONZE_DATA


class MetaLoader:
    """메타데이터 로더 (싱글톤 패턴)"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self._load_all()
            self._loaded = True

    def _load_all(self):
        """모든 메타데이터 로드"""
        meta_dir = BRONZE_DATA["meta"]

        # spid.json (선수 ID → 선수명)
        self.spid: Dict[int, str] = {}
        spid_file = meta_dir / "spid.json"
        if spid_file.exists():
            with open(spid_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # [{"id": 123, "name": "선수명"}, ...] 형식 가정
                for item in data:
                    self.spid[item["id"]] = item["name"]

        # seasonid.json (시즌 ID → 시즌명)
        self.seasonid: Dict[int, str] = {}
        seasonid_file = meta_dir / "seasonid.json"
        if seasonid_file.exists():
            with open(seasonid_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.seasonid[item.get("seasonId", item.get("id"))] = item.get(
                        "className", item.get("name", "")
                    )

        # matchtype.json (매치타입 코드 → 매치명)
        self.matchtype: Dict[int, str] = {}
        matchtype_file = meta_dir / "matchtype.json"
        if matchtype_file.exists():
            with open(matchtype_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.matchtype[item.get("matchtype", item.get("id"))] = item.get(
                        "desc", item.get("name", "")
                    )

        # division.json (디비전 코드 → 등급명)
        self.division: Dict[int, str] = {}
        division_file = meta_dir / "division.json"
        if division_file.exists():
            with open(division_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.division[item.get("divisionId", item.get("id"))] = item.get(
                        "divisionName", item.get("name", "")
                    )

        # spposition.json (포지션 코드 → 포지션명)
        self.spposition: Dict[int, str] = {}
        spposition_file = meta_dir / "spposition.json"
        if spposition_file.exists():
            with open(spposition_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.spposition[item.get("spposition", item.get("id"))] = item.get(
                        "desc", item.get("name", "")
                    )

    def get_player_name(self, spid: int) -> str:
        """
        선수 ID로 선수명 조회

        Args:
            spid: 전체 spid (시즌ID * 1000000 + 선수ID) 또는 선수ID만

        spid.json의 id는 전체 spid 형식 (예: 241206517 = 시즌241 + 선수206517)
        """
        # 전체 spid로 먼저 조회
        if spid in self.spid:
            return self.spid[spid]

        # 선수ID만으로 조회 실패 시 Unknown 반환
        return f"Unknown({spid})"

    def get_season_name(self, season_id: int) -> str:
        """시즌 ID로 시즌명 조회"""
        return self.seasonid.get(season_id, f"Unknown({season_id})")

    def get_matchtype_name(self, matchtype: int) -> str:
        """매치타입 코드로 매치명 조회"""
        return self.matchtype.get(matchtype, f"Unknown({matchtype})")

    def get_division_name(self, division_id: int) -> str:
        """디비전 코드로 등급명 조회"""
        return self.division.get(division_id, f"Unknown({division_id})")

    def get_position_name(self, position: int) -> str:
        """포지션 코드로 포지션명 조회"""
        return self.spposition.get(position, f"Unknown({position})")

    def parse_spid(self, spid: int) -> tuple:
        """
        spid에서 시즌ID와 선수ID 분리
        spid = seasonId * 1000000 + playerId
        """
        season_id = spid // 1000000
        player_id = spid % 1000000
        return season_id, player_id


# 전역 인스턴스
meta = MetaLoader()
