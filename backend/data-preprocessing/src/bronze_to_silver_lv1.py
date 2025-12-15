"""
Bronze → Silver 변환
- 메타데이터 조인 (spid → 선수명, matchtype → 매치명 등)
- 스키마 정규화
- goalTime 디코딩
- 좌표 → 구역 변환
"""

import json
from pathlib import Path
from typing import Optional

from config import BRONZE_DATA, SILVER_DATA, OUTPUT_FILES
from utils import (
    MetaLoader,
    decode_goaltime,
    get_zone,
    get_zone_detail,
    get_penalty_area_zone,
    get_shot_type,
    get_shot_type_korean,
    get_shot_result,
    get_match_end_type,
)
from config import TARGET_OUID

# 분석 대상 유저 OUID (config.py에서 설정)
MY_OUID = TARGET_OUID


def transform_shoot_detail(shoot_detail: dict, meta: MetaLoader) -> dict:
    """shootDetail 데이터 변환"""
    # 슈터 정보
    spid = shoot_detail.get("spId", 0)
    season_id, player_id = meta.parse_spid(spid)

    # 어시스터 정보
    assist_spid = shoot_detail.get("assistSpId", 0)
    assist_season_id, assist_player_id = (
        meta.parse_spid(assist_spid) if assist_spid else (0, 0)
    )

    # 좌표 및 구역
    x = shoot_detail.get("x", 0)
    y = shoot_detail.get("y", 0)
    zone_info = get_zone_detail(x, y)

    # goalTime 디코딩
    goaltime_raw = shoot_detail.get("goalTime", 0)
    goaltime_decoded = decode_goaltime(goaltime_raw)

    # 결과 코드
    result_code = shoot_detail.get("result", 1)
    shot_type_code = shoot_detail.get("type", 1)

    return {
        "time": {
            "raw": goaltime_raw,
            "half": goaltime_decoded["half"],
            "minute": goaltime_decoded["minute"],
            "display": goaltime_decoded["display"],
        },
        "shooter": {
            "sp_id": spid,
            "name": meta.get_player_name(spid),
            "season_id": season_id,
            "season_name": meta.get_season_name(season_id),
        },
        "location": {
            "x": x,
            "y": y,
            "zone": zone_info["zone"],
            "zone_desc": zone_info.get("description", ""),
            "x_zone": zone_info["x_zone"],
            "y_zone": zone_info["y_zone"],
            "penalty_zone": get_penalty_area_zone(x, y),
        },
        "shot_type": {
            "code": shot_type_code,
            "name": get_shot_type(shot_type_code),
            "korean": get_shot_type_korean(shot_type_code),
        },
        "result": {
            "code": result_code,
            "name": get_shot_result(result_code),
            "is_goal": result_code == 3,
            "is_on_target": result_code in [1, 3],
        },
        "assist": (
            {
                "sp_id": assist_spid,
                "name": meta.get_player_name(assist_spid) if assist_spid else None,
                "season_id": assist_season_id if assist_spid else None,
                "season_name": (
                    meta.get_season_name(assist_season_id) if assist_spid else None
                ),
                "x": shoot_detail.get("assistX", 0),
                "y": shoot_detail.get("assistY", 0),
            }
            if assist_spid
            else None
        ),
        "in_penalty": shoot_detail.get("inPenalty", False),
        "hit_post": shoot_detail.get("hitPost", False),
    }


def transform_player_stat(player: dict, meta: MetaLoader) -> dict:
    """player 스탯 데이터 변환"""
    spid = player.get("spId", 0)
    season_id, player_id = meta.parse_spid(spid)
    position = player.get("spPosition", 0)

    # status 추출
    status = player.get("status", {})

    return {
        "sp_id": spid,
        "name": meta.get_player_name(spid),
        "season_id": season_id,
        "season_name": meta.get_season_name(season_id),
        "position": {
            "code": position,
            "name": meta.get_position_name(position),
        },
        "grade": player.get("spGrade", 0),
        "rating": status.get("spRating", 0),
        "stats": {
            # 공격
            "goal": status.get("goal", 0),
            "assist": status.get("assist", 0),
            "shoot": status.get("shoot", 0),
            "effective_shoot": status.get("effectiveShoot", 0),
            "dribble_try": status.get("dribbleTry", 0),
            "dribble_success": status.get("dribbleSuccess", 0),
            # 패스
            "pass_try": status.get("passTry", 0),
            "pass_success": status.get("passSuccess", 0),
            "aerial_try": status.get("aerialTry", 0),
            "aerial_success": status.get("aerialSuccess", 0),
            # 수비
            "block_try": status.get("blockTry", 0),
            "block_success": status.get("blockSuccess", 0),
            "tackle_try": status.get("tackleTry", 0),
            "tackle_success": status.get("tackleSuccess", 0),
            # 기타
            "yellow_cards": status.get("yellowCards", 0),
            "red_cards": status.get("redCards", 0),
        },
    }


def transform_match_info(match_info: dict, meta: MetaLoader) -> dict:
    """matchInfo (단일 플레이어) 데이터 변환"""
    ouid = match_info.get("ouid", "")
    nickname = match_info.get("nickname", "")
    match_detail = match_info.get("matchDetail", {}) or {}
    shoot = match_info.get("shoot", {}) or {}
    shoot_detail_list = match_info.get("shootDetail", []) or []
    pass_data = match_info.get("pass", {}) or {}
    defence = match_info.get("defence", {}) or {}
    player_list = match_info.get("player", []) or []

    # 매치 종료 타입
    end_type_code = match_detail.get("matchEndType", 0)

    # 슈팅 상세 변환
    transformed_shoots = [transform_shoot_detail(sd, meta) for sd in shoot_detail_list]

    # 선수 스탯 변환
    transformed_players = [transform_player_stat(p, meta) for p in player_list]

    return {
        "ouid": ouid,
        "nickname": nickname,
        "is_me": ouid == MY_OUID,
        "result": match_detail.get("matchResult", ""),
        "end_type": {
            "code": end_type_code,
            "name": get_match_end_type(end_type_code),
        },
        "stats": {
            "possession": match_detail.get("possession", 0),
            "average_rating": match_detail.get("averageRating", 0),
            "controller": match_detail.get("controller", ""),
            "season_id": match_detail.get("seasonId", 0),
            "foul": match_detail.get("foul", 0),
            "injury": match_detail.get("injury", 0),
            "yellow_cards": match_detail.get("yellowCards", 0),
            "red_cards": match_detail.get("redCards", 0),
            "offsides": match_detail.get("offsides", 0),
            "corner_kicks": match_detail.get("cornerKick", 0),
        },
        "shoot_summary": {
            "total": shoot.get("shootTotal", 0),
            "on_target": shoot.get("effectiveShootTotal", 0),
            "goals": shoot.get("goalTotal", 0),
            "goals_in_penalty": shoot.get("goalTotalDisplay", 0),  # 패널티 안에서
            "outside_penalty": shoot.get("shootOutScore", 0),
            "heading_goals": shoot.get("goalHeading", 0),
            "freekick_goals": shoot.get("goalFreekick", 0),
            "penalty_goals": shoot.get("goalPenaltyKick", 0),
            "own_goals": shoot.get("goalOwnGoal", 0),
        },
        "shoot_details": transformed_shoots,
        "pass_stats": {
            "total_try": pass_data.get("passTry") or 0,
            "total_success": pass_data.get("passSuccess") or 0,
            "accuracy": (
                round(
                    (pass_data.get("passSuccess") or 0)
                    / (pass_data.get("passTry") or 1)
                    * 100,
                    1,
                )
                if (pass_data.get("passTry") or 0) > 0
                else 0
            ),
            "short_try": pass_data.get("shortPassTry") or 0,
            "short_success": pass_data.get("shortPassSuccess") or 0,
            "long_try": pass_data.get("longPassTry") or 0,
            "long_success": pass_data.get("longPassSuccess") or 0,
            "through_try": pass_data.get("throughPassTry") or 0,
            "through_success": pass_data.get("throughPassSuccess") or 0,
            "lobby_try": pass_data.get("lobbPassTry") or 0,
            "lobby_success": pass_data.get("lobbPassSuccess") or 0,
            "bouncingLob_try": pass_data.get("bouncingLobPassTry") or 0,
            "bouncingLob_success": pass_data.get("bouncingLobPassSuccess") or 0,
            "driven_ground_try": pass_data.get("drivenGroundPassTry") or 0,
            "driven_ground_success": pass_data.get("drivenGroundPassSuccess") or 0,
        },
        "defence_stats": {
            "block_try": defence.get("blockTry") or 0,
            "block_success": defence.get("blockSuccess") or 0,
            "tackle_try": defence.get("tackleTry") or 0,
            "tackle_success": defence.get("tackleSuccess") or 0,
        },
        "players_stats": transformed_players,
    }


def transform_match(match: dict, meta: MetaLoader) -> dict:
    """단일 매치 데이터 변환"""
    match_id = match.get("matchId", "")
    match_date = match.get("matchDate", "")
    match_type = match.get("matchType", 0)
    match_info_list = match.get("matchInfo", [])

    # 플레이어별 데이터 변환
    transformed_players = [transform_match_info(mi, meta) for mi in match_info_list]

    return {
        "match_id": match_id,
        "match_date": match_date,
        "match_type": {
            "code": match_type,
            "name": meta.get_matchtype_name(match_type),
        },
        "players": transformed_players,
    }


def transform_match_detail():
    """
    matchDetail Bronze → Silver 변환
    """
    bronze_dir = BRONZE_DATA["matchDetail"]
    silver_dir = SILVER_DATA["matchDetail"]
    silver_dir.mkdir(parents=True, exist_ok=True)

    bronze_file = bronze_dir / OUTPUT_FILES["matchDetail"]
    # Silver 파일명에 _lv1 접미사 추가
    silver_filename = OUTPUT_FILES["matchDetail"].replace(".jsonl", "_lv1.jsonl")
    silver_file = silver_dir / silver_filename

    if not bronze_file.exists():
        print(f"⚠️ Bronze 파일이 없습니다: {bronze_file}")
        return

    # 메타데이터 로더 초기화
    meta = MetaLoader()

    # 변환 수행
    transformed_count = 0
    with open(bronze_file, "r", encoding="utf-8") as f_in, open(
        silver_file, "w", encoding="utf-8"
    ) as f_out:

        for line in f_in:
            if not line.strip():
                continue

            match = json.loads(line)
            transformed = transform_match(match, meta)
            f_out.write(json.dumps(transformed, ensure_ascii=False) + "\n")
            transformed_count += 1

    print(f"✅ matchDetail 변환 완료: {transformed_count}건")
    print(f"   📁 {silver_file}")


def transform_community():
    """
    community Bronze → Silver 변환

    TODO:
    - 스키마 정규화
    - 불필요한 HTML 태그 정리
    """
    bronze_dir = BRONZE_DATA["community"]
    silver_dir = SILVER_DATA["community"]
    silver_dir.mkdir(parents=True, exist_ok=True)

    bronze_file = bronze_dir / OUTPUT_FILES["community"]
    silver_file = silver_dir / OUTPUT_FILES["community"]

    if not bronze_file.exists():
        print(f"⚠️ Bronze 파일이 없습니다: {bronze_file}")
        return

    # TODO: 실제 변환 로직 구현
    print(f"⏳ community 변환 미구현")


def transform_server_maintenance():
    """
    server-maintenance Bronze → Silver 변환

    TODO:
    - 스키마 정규화
    - 점검 시간 파싱
    """
    bronze_dir = BRONZE_DATA["server-maintenance"]
    silver_dir = SILVER_DATA["server-maintenance"]
    silver_dir.mkdir(parents=True, exist_ok=True)

    bronze_file = bronze_dir / OUTPUT_FILES["server-maintenance"]
    silver_file = silver_dir / OUTPUT_FILES["server-maintenance"]

    if not bronze_file.exists():
        print(f"⚠️ Bronze 파일이 없습니다: {bronze_file}")
        return

    # TODO: 실제 변환 로직 구현
    print(f"⏳ server-maintenance 변환 미구현")


def transform_all():
    """모든 Bronze → Silver 변환 실행"""
    print("🚀 Bronze → Silver 변환 시작\n")

    print("=" * 50)
    print("🔄 matchDetail 변환")
    print("=" * 50)
    transform_match_detail()

    print("\n" + "=" * 50)
    print("🔄 community 변환")
    print("=" * 50)
    transform_community()

    print("\n" + "=" * 50)
    print("🔄 server-maintenance 변환")
    print("=" * 50)
    transform_server_maintenance()

    print("\n🎉 Bronze → Silver 변환 완료!")


if __name__ == "__main__":
    transform_all()
