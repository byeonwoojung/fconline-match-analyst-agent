"""
Silver → Gold 변환
- 경기 요약 텍스트 생성 (RAG 임베딩용)
- 통계 집계 (전체, 시간대별, 구역별, 실점 패턴, 선수별)
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

from config import SILVER_DATA, GOLD_DATA, DATA_ROOT
from utils import get_zone


# ============================================================================
# Gold 출력 경로
# ============================================================================
GOLD_DIR = DATA_ROOT / "gold" / "match_summaries"
GOLD_COMMUNITY_DIR = DATA_ROOT / "gold" / "community"
GOLD_SERVER_MAINTENANCE_DIR = DATA_ROOT / "gold" / "server-maintenance"

GOLD_OUTPUT = {
    # match_summaries
    "match_summaries": GOLD_DIR / "match_summaries.jsonl",
    "overall_stats": GOLD_DIR / "overall_stats.json",
    "time_zone_stats": GOLD_DIR / "time_zone_stats.json",
    "zone_stats": GOLD_DIR / "zone_stats.json",
    "concede_patterns": GOLD_DIR / "concede_patterns.json",
    "player_stats": GOLD_DIR / "player_stats.json",
    # community
    "community": GOLD_COMMUNITY_DIR / "community.jsonl",
    # server-maintenance
    "server_maintenance": GOLD_SERVER_MAINTENANCE_DIR / "server-maintenance.jsonl",
}


# ============================================================================
# 헬퍼 함수
# ============================================================================
def load_silver_lv1():
    """Silver Lv1 데이터 로드"""
    silver_file = SILVER_DATA["matchDetail"] / "matchDetail_lv1.jsonl"
    data = []
    with open(silver_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def get_player_grade(sp_id: int, players_stats: list) -> int:
    """매치 내 선수 스탯에서 강화등급 조회"""
    for p in players_stats:
        if p["sp_id"] == sp_id:
            return p.get("grade", 0)
    return 0


def format_player(name: str, season: str, grade: int) -> str:
    """선수명(시즌, +N강) 포맷"""
    # 시즌명이 길면 줄임
    season_short = season.split(" (")[0] if " (" in season else season
    return f"{name}({season_short}, +{grade}강)"


def format_goal_sentence(
    time_display: str,
    shooter_name: str,
    shooter_season: str,
    shooter_grade: int,
    zone: str,
    zone_desc: str,
    penalty_zone: str,
    shot_type_korean: str,
    goal_type: str,  # "득점" | "실점"
    assist_name: str = None,
    assist_season: str = None,
    assist_grade: int = None,
    assist_zone: str = None,
) -> str:
    """골 상세 문장 생성"""

    # 슈터 정보
    shooter_info = format_player(shooter_name, shooter_season, shooter_grade)

    # 위치 정보 구성
    location_parts = [zone]
    if zone_desc:
        location_parts.append(f"({zone_desc})")
    if penalty_zone and penalty_zone != "페널티박스외":
        if zone_desc:
            location_parts[-1] = location_parts[-1][:-1] + f", {penalty_zone})"
        else:
            location_parts.append(f"({penalty_zone})")
    location = "".join(location_parts)

    # 기본 문장
    if goal_type == "득점":
        sentence = f"{time_display}에 {shooter_info}가 {location}에서 {shot_type_korean}로 득점했습니다."
    else:  # 실점
        sentence = f"{time_display}에 {shooter_info}가 {location}에서 {shot_type_korean}로 득점하며 실점했습니다."

    # 어시스트 추가
    if assist_name and assist_zone and assist_name != "Unknown(-1)":
        assist_info = format_player(assist_name, assist_season, assist_grade)
        sentence += (
            f" 이 골은 {assist_info}가 {assist_zone}에서 연결한 패스로 만들어졌습니다."
        )
    else:
        sentence += " 개인 돌파로 만든 골입니다."

    return sentence


def extract_goals_from_player(player_data: dict, goal_type: str) -> list:
    """플레이어 데이터에서 골 정보 추출"""
    goals = []
    players_stats = player_data.get("players_stats", [])

    for shoot in player_data.get("shoot_details", []):
        if not shoot["result"]["is_goal"]:
            continue

        # 슈터 정보
        shooter = shoot["shooter"]
        shooter_grade = get_player_grade(shooter["sp_id"], players_stats)

        # 어시스트 정보
        assist = shoot.get("assist")
        assist_name = None
        assist_season = None
        assist_grade = 0
        assist_zone = None

        if assist and assist.get("sp_id") and assist["sp_id"] != -1:
            assist_name = assist["name"]
            assist_season = assist.get("season_name", "")
            assist_grade = get_player_grade(assist["sp_id"], players_stats)
            # 어시스트 좌표로 구역 계산
            assist_x = assist.get("x", 0.5)
            assist_y = assist.get("y", 0.5)
            assist_zone = get_zone(assist_x, assist_y)

        # 문장 생성
        sentence = format_goal_sentence(
            time_display=shoot["time"]["display"],
            shooter_name=shooter["name"],
            shooter_season=shooter.get("season_name", ""),
            shooter_grade=shooter_grade,
            zone=shoot["location"]["zone"],
            zone_desc=shoot["location"].get("zone_desc", ""),
            penalty_zone=shoot["location"].get("penalty_zone", ""),
            shot_type_korean=shoot["shot_type"]["korean"],
            goal_type=goal_type,
            assist_name=assist_name,
            assist_season=assist_season,
            assist_grade=assist_grade,
            assist_zone=assist_zone,
        )

        goals.append(
            {
                "time": shoot["time"],
                "sentence": sentence,
                "shooter": shooter["name"],
                "shot_type": shoot["shot_type"]["korean"],
                "zone": shoot["location"]["zone"],
            }
        )

    # 시간순 정렬
    goals.sort(key=lambda x: x["time"]["raw"])
    return goals


# ============================================================================
# Gold 생성 함수들
# ============================================================================
def generate_match_summaries():
    """매치별 요약 텍스트 생성"""
    silver_data = load_silver_lv1()

    gold_dir = GOLD_OUTPUT["match_summaries"].parent
    gold_dir.mkdir(parents=True, exist_ok=True)

    summaries = []

    for match in silver_data:
        match_id = match["match_id"]
        match_date = match["match_date"]
        match_type_name = match["match_type"]["name"]

        # 내 데이터와 상대 데이터 분리
        my_data = None
        opponent_data = None
        for p in match["players"]:
            if p["is_me"]:
                my_data = p
            else:
                opponent_data = p

        if not my_data:
            continue

        # 기본 정보
        my_result = my_data["result"]
        result_text = {"승": "승리", "무": "무승부", "패": "패배"}.get(
            my_result, my_result
        )

        my_goals = my_data["shoot_summary"]["goals"]
        opponent_goals = opponent_data["shoot_summary"]["goals"] if opponent_data else 0
        opponent_nickname = opponent_data["nickname"] if opponent_data else "상대"

        my_possession = my_data["stats"]["possession"]
        opponent_possession = (
            opponent_data["stats"]["possession"]
            if opponent_data
            else (100 - my_possession)
        )

        my_shots = my_data["shoot_summary"]["total"]
        my_shots_on_target = my_data["shoot_summary"]["on_target"]
        opponent_shots = opponent_data["shoot_summary"]["total"] if opponent_data else 0
        opponent_shots_on_target = (
            opponent_data["shoot_summary"]["on_target"] if opponent_data else 0
        )

        # 날짜 포맷
        try:
            dt = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y년 %m월 %d일")
        except:
            date_str = match_date

        # 요약 문장
        summary_text = (
            f"{date_str} {match_type_name}에서 {opponent_nickname}을(를) 상대로 "
            f"{my_goals}:{opponent_goals} {result_text}를 거뒀습니다. "
            f"점유율 {my_possession}% vs {opponent_possession}%, "
            f"슈팅 {my_shots}개(유효 {my_shots_on_target}개) vs {opponent_shots}개(유효 {opponent_shots_on_target}개)를 기록했습니다."
        )

        # 득점 상세
        my_goals_list = extract_goals_from_player(my_data, "득점")
        my_goals_text = [g["sentence"] for g in my_goals_list]

        # 실점 상세 (상대 데이터에서)
        conceded_goals_list = []
        conceded_goals_text = []
        if opponent_data:
            conceded_goals_list = extract_goals_from_player(opponent_data, "실점")
            conceded_goals_text = [g["sentence"] for g in conceded_goals_list]

        # 전체 내러티브 구성
        full_narrative_parts = [summary_text]

        if my_goals_text:
            full_narrative_parts.append("\n\n[득점]")
            for i, goal in enumerate(my_goals_text, 1):
                full_narrative_parts.append(f"{i}. {goal}")
        else:
            full_narrative_parts.append("\n\n[득점]\n이 경기에서 득점이 없었습니다.")

        if conceded_goals_text:
            full_narrative_parts.append("\n\n[실점]")
            for i, goal in enumerate(conceded_goals_text, 1):
                full_narrative_parts.append(f"{i}. {goal}")
        else:
            full_narrative_parts.append("\n\n[실점]\n이 경기에서 실점이 없었습니다.")

        full_narrative = "\n".join(full_narrative_parts)

        summaries.append(
            {
                "match_id": match_id,
                "match_date": match_date,
                "match_type": match_type_name,
                "result": my_result,
                "score": {"me": my_goals, "opponent": opponent_goals},
                "opponent_nickname": opponent_nickname,
                "summary_text": summary_text,
                "my_goals_text": my_goals_text,
                "conceded_goals_text": conceded_goals_text,
                "full_narrative": full_narrative,
                "metadata": {
                    "my_possession": my_possession,
                    "my_shots": my_shots,
                    "my_shots_on_target": my_shots_on_target,
                    "my_goals": my_goals,
                    "opponent_goals": opponent_goals,
                },
            }
        )

    # 저장
    with open(GOLD_OUTPUT["match_summaries"], "w", encoding="utf-8") as f:
        for s in summaries:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"✅ match_summaries 생성 완료: {len(summaries)}건")
    print(f"   📁 {GOLD_OUTPUT['match_summaries']}")


def generate_overall_stats():
    """전체 통계 집계"""
    silver_data = load_silver_lv1()

    stats = {
        "total_matches": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "total_goals_scored": 0,
        "total_goals_conceded": 0,
        "total_possession": 0,
        "total_shots": 0,
        "total_shots_on_target": 0,
        "scorers": defaultdict(
            lambda: {"goals": 0, "assists": 0, "season": "", "appearances": 0}
        ),
        "players_used": defaultdict(
            lambda: {"appearances": 0, "total_rating": 0, "season": ""}
        ),
    }

    for match in silver_data:
        my_data = None
        opponent_data = None
        for p in match["players"]:
            if p["is_me"]:
                my_data = p
            else:
                opponent_data = p

        if not my_data:
            continue

        stats["total_matches"] += 1

        # 승/무/패
        result = my_data["result"]
        if result == "승":
            stats["wins"] += 1
        elif result == "무":
            stats["draws"] += 1
        else:
            stats["losses"] += 1

        # 득실점
        my_goals = my_data["shoot_summary"].get("goals") or 0
        stats["total_goals_scored"] += my_goals
        opponent_goals = (
            (opponent_data["shoot_summary"].get("goals") or 0) if opponent_data else 0
        )
        stats["total_goals_conceded"] += opponent_goals

        # 점유율, 슈팅
        stats["total_possession"] += my_data["stats"].get("possession") or 0
        stats["total_shots"] += my_data["shoot_summary"].get("total") or 0
        stats["total_shots_on_target"] += my_data["shoot_summary"].get("on_target") or 0

        # 선수별 통계
        for player in my_data.get("players_stats", []):
            name = player["name"]
            if "Unknown" in name:
                continue

            key = f"{name}_{player['season_name']}"
            stats["players_used"][key]["appearances"] += 1
            stats["players_used"][key]["total_rating"] += player.get("rating", 0)
            stats["players_used"][key]["season"] = player["season_name"]
            stats["players_used"][key]["name"] = name

            # 골/어시스트
            goals = player["stats"].get("goal", 0)
            assists = player["stats"].get("assist", 0)
            if goals > 0 or assists > 0:
                stats["scorers"][key]["goals"] += goals
                stats["scorers"][key]["assists"] += assists
                stats["scorers"][key]["season"] = player["season_name"]
                stats["scorers"][key]["name"] = name

    # 최종 계산
    total = stats["total_matches"]
    output = {
        "total_matches": total,
        "wins": stats["wins"],
        "draws": stats["draws"],
        "losses": stats["losses"],
        "win_rate": round(stats["wins"] / total * 100, 1) if total > 0 else 0,
        "total_goals_scored": stats["total_goals_scored"],
        "total_goals_conceded": stats["total_goals_conceded"],
        "goal_difference": stats["total_goals_scored"] - stats["total_goals_conceded"],
        "avg_goals_scored": (
            round(stats["total_goals_scored"] / total, 2) if total > 0 else 0
        ),
        "avg_goals_conceded": (
            round(stats["total_goals_conceded"] / total, 2) if total > 0 else 0
        ),
        "avg_possession": (
            round(stats["total_possession"] / total, 1) if total > 0 else 0
        ),
        "avg_shots": round(stats["total_shots"] / total, 1) if total > 0 else 0,
        "shot_accuracy": (
            round(stats["total_shots_on_target"] / stats["total_shots"] * 100, 1)
            if stats["total_shots"] > 0
            else 0
        ),
        "top_scorers": sorted(
            [
                {
                    "name": v["name"],
                    "season": v["season"],
                    "goals": v["goals"],
                    "assists": v["assists"],
                }
                for v in stats["scorers"].values()
                if v["goals"] > 0
            ],
            key=lambda x: (x["goals"], x["assists"]),
            reverse=True,
        )[:10],
        "top_assists": sorted(
            [
                {
                    "name": v["name"],
                    "season": v["season"],
                    "goals": v["goals"],
                    "assists": v["assists"],
                }
                for v in stats["scorers"].values()
                if v["assists"] > 0
            ],
            key=lambda x: (x["assists"], x["goals"]),
            reverse=True,
        )[:10],
        "most_used_players": sorted(
            [
                {
                    "name": v["name"],
                    "season": v["season"],
                    "appearances": v["appearances"],
                    "avg_rating": (
                        round(v["total_rating"] / v["appearances"], 2)
                        if v["appearances"] > 0
                        else 0
                    ),
                }
                for v in stats["players_used"].values()
            ],
            key=lambda x: x["appearances"],
            reverse=True,
        )[:10],
    }

    # 저장
    gold_dir = GOLD_OUTPUT["overall_stats"].parent
    gold_dir.mkdir(parents=True, exist_ok=True)

    with open(GOLD_OUTPUT["overall_stats"], "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ overall_stats 생성 완료")
    print(f"   📁 {GOLD_OUTPUT['overall_stats']}")


def generate_time_zone_stats():
    """시간대별 득점/실점 통계"""
    silver_data = load_silver_lv1()

    from utils import get_time_range

    time_zones = [
        "0-15분",
        "16-30분",
        "31-45분",
        "46-60분",
        "61-75분",
        "76-90분",
        "연장전",
        "승부차기",
    ]

    stats = {
        "goals_scored": {tz: 0 for tz in time_zones},
        "goals_conceded": {tz: 0 for tz in time_zones},
        "shots_taken": {tz: 0 for tz in time_zones},
        "shots_on_target": {tz: 0 for tz in time_zones},
    }

    for match in silver_data:
        my_data = None
        opponent_data = None
        for p in match["players"]:
            if p["is_me"]:
                my_data = p
            else:
                opponent_data = p

        if not my_data:
            continue

        # 내 슈팅 분석
        for shoot in my_data.get("shoot_details", []):
            tz = get_time_range(shoot["time"]["raw"])
            stats["shots_taken"][tz] += 1
            if shoot["result"]["is_on_target"]:
                stats["shots_on_target"][tz] += 1
            if shoot["result"]["is_goal"]:
                stats["goals_scored"][tz] += 1

        # 실점 분석 (상대 골)
        if opponent_data:
            for shoot in opponent_data.get("shoot_details", []):
                if shoot["result"]["is_goal"]:
                    tz = get_time_range(shoot["time"]["raw"])
                    stats["goals_conceded"][tz] += 1

    # 저장
    with open(GOLD_OUTPUT["time_zone_stats"], "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"✅ time_zone_stats 생성 완료")
    print(f"   📁 {GOLD_OUTPUT['time_zone_stats']}")


def generate_zone_stats():
    """구역별 슈팅 통계"""
    silver_data = load_silver_lv1()

    stats = {
        "my_shots": defaultdict(
            lambda: {
                "total": 0,
                "on_target": 0,
                "goals": 0,
                "shot_types": defaultdict(int),
            }
        ),
        "opponent_shots": defaultdict(
            lambda: {
                "total": 0,
                "on_target": 0,
                "goals": 0,
                "shot_types": defaultdict(int),
            }
        ),
    }

    for match in silver_data:
        my_data = None
        opponent_data = None
        for p in match["players"]:
            if p["is_me"]:
                my_data = p
            else:
                opponent_data = p

        if not my_data:
            continue

        # 내 슈팅
        for shoot in my_data.get("shoot_details", []):
            zone = shoot["location"]["zone"]
            shot_type = shoot["shot_type"]["korean"]

            stats["my_shots"][zone]["total"] += 1
            stats["my_shots"][zone]["shot_types"][shot_type] += 1
            if shoot["result"]["is_on_target"]:
                stats["my_shots"][zone]["on_target"] += 1
            if shoot["result"]["is_goal"]:
                stats["my_shots"][zone]["goals"] += 1

        # 상대 슈팅 (실점 분석)
        if opponent_data:
            for shoot in opponent_data.get("shoot_details", []):
                zone = shoot["location"]["zone"]
                shot_type = shoot["shot_type"]["korean"]

                stats["opponent_shots"][zone]["total"] += 1
                stats["opponent_shots"][zone]["shot_types"][shot_type] += 1
                if shoot["result"]["is_on_target"]:
                    stats["opponent_shots"][zone]["on_target"] += 1
                if shoot["result"]["is_goal"]:
                    stats["opponent_shots"][zone]["goals"] += 1

    # defaultdict를 일반 dict로 변환
    output = {
        "my_shots": {
            k: {
                "total": v["total"],
                "on_target": v["on_target"],
                "goals": v["goals"],
                "shot_types": dict(v["shot_types"]),
            }
            for k, v in stats["my_shots"].items()
        },
        "opponent_shots": {
            k: {
                "total": v["total"],
                "on_target": v["on_target"],
                "goals": v["goals"],
                "shot_types": dict(v["shot_types"]),
            }
            for k, v in stats["opponent_shots"].items()
        },
    }

    # 저장
    with open(GOLD_OUTPUT["zone_stats"], "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ zone_stats 생성 완료")
    print(f"   📁 {GOLD_OUTPUT['zone_stats']}")


def generate_concede_patterns():
    """실점 패턴 분석"""
    silver_data = load_silver_lv1()

    from utils import get_time_range

    patterns = {
        "total_conceded": 0,
        "by_zone": defaultdict(int),
        "by_time_zone": defaultdict(int),
        "by_shot_type": defaultdict(int),
        "by_scorer": defaultdict(lambda: {"goals": 0, "season": ""}),
        "details": [],  # 개별 실점 기록
    }

    for match in silver_data:
        opponent_data = None
        for p in match["players"]:
            if not p["is_me"]:
                opponent_data = p
                break

        if not opponent_data:
            continue

        players_stats = opponent_data.get("players_stats", [])

        for shoot in opponent_data.get("shoot_details", []):
            if not shoot["result"]["is_goal"]:
                continue

            patterns["total_conceded"] += 1

            zone = shoot["location"]["zone"]
            time_zone = get_time_range(shoot["time"]["raw"])
            shot_type = shoot["shot_type"]["korean"]
            scorer_name = shoot["shooter"]["name"]
            scorer_season = shoot["shooter"].get("season_name", "")

            patterns["by_zone"][zone] += 1
            patterns["by_time_zone"][time_zone] += 1
            patterns["by_shot_type"][shot_type] += 1

            scorer_key = f"{scorer_name}_{scorer_season}"
            patterns["by_scorer"][scorer_key]["goals"] += 1
            patterns["by_scorer"][scorer_key]["season"] = scorer_season
            patterns["by_scorer"][scorer_key]["name"] = scorer_name

            # 개별 기록
            patterns["details"].append(
                {
                    "match_id": match["match_id"],
                    "match_date": match["match_date"],
                    "time": shoot["time"]["display"],
                    "scorer": scorer_name,
                    "scorer_season": scorer_season,
                    "zone": zone,
                    "shot_type": shot_type,
                }
            )

    # 패턴 분석 텍스트 생성
    analysis_texts = []

    # 가장 많이 실점한 구역
    if patterns["by_zone"]:
        top_zone = max(patterns["by_zone"].items(), key=lambda x: x[1])
        analysis_texts.append(f"가장 많이 실점한 구역: {top_zone[0]} ({top_zone[1]}골)")

    # 가장 많이 실점한 시간대
    if patterns["by_time_zone"]:
        top_time = max(patterns["by_time_zone"].items(), key=lambda x: x[1])
        analysis_texts.append(
            f"가장 많이 실점한 시간대: {top_time[0]} ({top_time[1]}골)"
        )

    # 가장 많이 허용한 슈팅 타입
    if patterns["by_shot_type"]:
        top_type = max(patterns["by_shot_type"].items(), key=lambda x: x[1])
        analysis_texts.append(
            f"가장 많이 허용한 슈팅 타입: {top_type[0]} ({top_type[1]}골)"
        )

    output = {
        "total_conceded": patterns["total_conceded"],
        "by_zone": dict(patterns["by_zone"]),
        "by_time_zone": dict(patterns["by_time_zone"]),
        "by_shot_type": dict(patterns["by_shot_type"]),
        "top_scorers_against": sorted(
            [
                {"name": v["name"], "season": v["season"], "goals": v["goals"]}
                for v in patterns["by_scorer"].values()
            ],
            key=lambda x: x["goals"],
            reverse=True,
        )[:10],
        "analysis": analysis_texts,
        "details": patterns["details"],
    }

    # 저장
    with open(GOLD_OUTPUT["concede_patterns"], "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ concede_patterns 생성 완료")
    print(f"   📁 {GOLD_OUTPUT['concede_patterns']}")


def generate_player_stats():
    """선수별 누적 통계"""
    silver_data = load_silver_lv1()

    players = defaultdict(
        lambda: {
            "name": "",
            "season": "",
            "appearances": 0,
            "total_rating": 0,
            "goals": 0,
            "assists": 0,
            "shots": 0,
            "effective_shots": 0,
            "pass_try": 0,
            "pass_success": 0,
            "positions": defaultdict(int),
            "shot_zones": defaultdict(int),
            "goal_zones": defaultdict(int),
            "shot_types": defaultdict(int),
        }
    )

    for match in silver_data:
        my_data = None
        for p in match["players"]:
            if p["is_me"]:
                my_data = p
                break

        if not my_data:
            continue

        # 선수 스탯
        for player in my_data.get("players_stats", []):
            name = player["name"]
            if "Unknown" in name:
                continue

            key = f"{name}_{player['season_name']}"
            players[key]["name"] = name
            players[key]["season"] = player["season_name"]
            players[key]["appearances"] += 1
            players[key]["total_rating"] += player.get("rating", 0)
            players[key]["goals"] += player["stats"].get("goal", 0)
            players[key]["assists"] += player["stats"].get("assist", 0)
            players[key]["shots"] += player["stats"].get("shoot", 0)
            players[key]["effective_shots"] += player["stats"].get("effective_shoot", 0)
            players[key]["pass_try"] += player["stats"].get("pass_try", 0)
            players[key]["pass_success"] += player["stats"].get("pass_success", 0)
            players[key]["positions"][player["position"]["name"]] += 1

        # 슈팅 정보에서 구역/타입별 통계
        for shoot in my_data.get("shoot_details", []):
            shooter_name = shoot["shooter"]["name"]
            shooter_season = shoot["shooter"].get("season_name", "")
            if "Unknown" in shooter_name:
                continue

            key = f"{shooter_name}_{shooter_season}"
            zone = shoot["location"]["zone"]
            shot_type = shoot["shot_type"]["korean"]

            players[key]["shot_zones"][zone] += 1
            players[key]["shot_types"][shot_type] += 1

            if shoot["result"]["is_goal"]:
                players[key]["goal_zones"][zone] += 1

    # 출력 형식으로 변환
    output = []
    for key, p in players.items():
        if p["appearances"] == 0:
            continue

        output.append(
            {
                "name": p["name"],
                "season": p["season"],
                "appearances": p["appearances"],
                "avg_rating": (
                    round(p["total_rating"] / p["appearances"], 2)
                    if p["appearances"] > 0
                    else 0
                ),
                "goals": p["goals"],
                "assists": p["assists"],
                "shots": p["shots"],
                "effective_shots": p["effective_shots"],
                "shot_accuracy": (
                    round(p["effective_shots"] / p["shots"] * 100, 1)
                    if p["shots"] > 0
                    else 0
                ),
                "pass_accuracy": (
                    round(p["pass_success"] / p["pass_try"] * 100, 1)
                    if p["pass_try"] > 0
                    else 0
                ),
                "main_position": (
                    max(p["positions"].items(), key=lambda x: x[1])[0]
                    if p["positions"]
                    else ""
                ),
                "positions": dict(p["positions"]),
                "shot_zones": dict(p["shot_zones"]),
                "goal_zones": dict(p["goal_zones"]),
                "shot_types": dict(p["shot_types"]),
            }
        )

    # 출전 횟수순 정렬
    output.sort(key=lambda x: x["appearances"], reverse=True)

    # 저장
    with open(GOLD_OUTPUT["player_stats"], "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ player_stats 생성 완료: {len(output)}명")
    print(f"   📁 {GOLD_OUTPUT['player_stats']}")


# ============================================================================
# 커뮤니티 변환
# ============================================================================
def generate_community():
    """
    커뮤니티 데이터 Gold 변환

    TODO:
    - 스쿼드 정보 추출
    - 팁/공략 분류
    - RAG용 텍스트 정제
    """
    gold_dir = GOLD_COMMUNITY_DIR
    gold_dir.mkdir(parents=True, exist_ok=True)

    # TODO: 실제 변환 로직 구현
    print(f"⏳ community 변환 미구현")


# ============================================================================
# 서버 점검 공지 변환
# ============================================================================
def generate_server_maintenance():
    """
    서버 점검 공지 데이터 Gold 변환

    TODO:
    - 점검 시간 파싱
    - 점검 내용 요약
    - RAG용 텍스트 정제
    """
    gold_dir = GOLD_SERVER_MAINTENANCE_DIR
    gold_dir.mkdir(parents=True, exist_ok=True)

    # TODO: 실제 변환 로직 구현
    print(f"⏳ server-maintenance 변환 미구현")


# ============================================================================
# 메인 실행
# ============================================================================
def transform_all():
    """모든 Silver → Gold 변환 실행"""
    print("🚀 Silver → Gold 변환 시작\n")

    print("=" * 50)
    print("🔄 매치 요약 생성")
    print("=" * 50)
    generate_match_summaries()

    print("\n" + "=" * 50)
    print("🔄 전체 통계 집계")
    print("=" * 50)
    generate_overall_stats()

    print("\n" + "=" * 50)
    print("🔄 시간대별 통계")
    print("=" * 50)
    generate_time_zone_stats()

    print("\n" + "=" * 50)
    print("🔄 구역별 통계")
    print("=" * 50)
    generate_zone_stats()

    print("\n" + "=" * 50)
    print("🔄 실점 패턴 분석")
    print("=" * 50)
    generate_concede_patterns()

    print("\n" + "=" * 50)
    print("🔄 선수별 통계")
    print("=" * 50)
    generate_player_stats()

    print("\n" + "=" * 50)
    print("🔄 커뮤니티 변환")
    print("=" * 50)
    generate_community()

    print("\n" + "=" * 50)
    print("🔄 서버 점검 공지 변환")
    print("=" * 50)
    generate_server_maintenance()

    print("\n🎉 Silver → Gold 변환 완료!")


if __name__ == "__main__":
    transform_all()
