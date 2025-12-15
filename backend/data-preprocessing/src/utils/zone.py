"""
좌표 구역화 유틸리티

FC Online 좌표 시스템 (해당 행동을 수행한 선수 시점):
- x축: 0 = 자기 골대, 1 = 상대 골대
- y축: 0 = 터치라인, 1 = 반대쪽 터치라인
- x > 1 또는 y > 1: 경기장 밖

※ (x, y) 좌표는 해당 행동을 수행한 선수 시점
  - x가 클수록 상대 골대에 가까움 (공격 방향)
  - x가 작을수록 자기 골대에 가까움 (수비 방향)

구역 (19개):
x축 6등분 × y축 3등분 = 18개 + 경기장외각 1개

x축 경계:
- 0.00 ~ 0.17: 수비골대앞 (중앙), 수비코너라인부근 (좌우측) - 자기 골대 근처
- 0.17 ~ 0.33: 수비큰박스라인부근 (중앙), 수비지역 (좌우측) - 자기 진영
- 0.33 ~ 0.50: 미들수비지역 - 하프라인 자기쪽
- 0.50 ~ 0.67: 미들공격지역 - 하프라인 상대쪽
- 0.67 ~ 0.83: 공격큰박스라인부근 (중앙), 공격지역 (좌우측) - 상대 진영
- 0.83 ~ 1.00: 공격골대앞 (중앙), 공격코너라인부근 (좌우측) - 상대 골대 근처

y축 경계:
- 0.00 ~ 0.33: 우측
- 0.33 ~ 0.67: 중앙
- 0.67 ~ 1.00: 좌측
"""

from typing import Tuple

# x축 경계값 정의 (6등분)
X_GOAL_NEAR = 0.17  # 골대앞 끝
X_DEFENSE = 0.33  # 수비지역 끝
X_MID_DEFENSE = 0.50  # 미들수비지역 끝
X_MID_ATTACK = 0.67  # 미들공격지역 끝
X_ATTACK = 0.83  # 공격지역 끝

# y축 경계값 정의 (3등분)
Y_RIGHT_MAX = 0.33  # 우측 끝
Y_CENTER_MAX = 0.67  # 중앙 끝


def get_zone(x: float, y: float) -> str:
    """
    좌표를 구역명으로 변환 (19개 구역)

    ※ 해당 행동을 수행한 선수 시점 기준 좌표

    Args:
        x: x 좌표 (0 = 자기 골대, 1 = 상대 골대)
        y: y 좌표 (0 = 터치라인, 1 = 반대쪽 터치라인)

    Returns:
        구역명 (예: "중앙_공격골대앞", "좌측_미들수비지역", "경기장외각")
    """
    # 경기장 외각 체크
    if x < 0 or x > 1 or y < 0 or y > 1:
        return "경기장외각"

    # y축 구역 (우측/중앙/좌측)
    if y <= Y_RIGHT_MAX:
        y_zone = "우측"
    elif y <= Y_CENTER_MAX:
        y_zone = "중앙"
    else:
        y_zone = "좌측"

    # x축 구역 (6등분, y_zone에 따라 다른 이름)
    if x <= X_GOAL_NEAR:
        # 0 ~ 0.17: 수비 골대앞/코너라인부근
        if y_zone == "중앙":
            return "중앙_수비골대앞"
        else:
            return f"{y_zone}_수비코너라인부근"

    elif x <= X_DEFENSE:
        # 0.17 ~ 0.33: 수비지역/큰박스라인부근
        if y_zone == "중앙":
            return "중앙_수비큰박스라인부근"
        else:
            return f"{y_zone}_수비지역"

    elif x <= X_MID_DEFENSE:
        # 0.33 ~ 0.50: 미들수비지역
        return f"{y_zone}_미들수비지역"

    elif x <= X_MID_ATTACK:
        # 0.50 ~ 0.67: 미들공격지역
        return f"{y_zone}_미들공격지역"

    elif x <= X_ATTACK:
        # 0.67 ~ 0.83: 공격지역/큰박스라인부근
        if y_zone == "중앙":
            return "중앙_공격큰박스라인부근"
        else:
            return f"{y_zone}_공격지역"

    else:
        # 0.83 ~ 1.00: 공격 골대앞/코너라인부근
        if y_zone == "중앙":
            return "중앙_공격골대앞"
        else:
            return f"{y_zone}_공격코너라인부근"


def get_zone_detail(x: float, y: float) -> dict:
    """
    좌표를 상세 구역 정보로 변환

    Returns:
        {
            "zone": "중앙_공격골대앞",
            "x_zone": "공격골대앞",
            "y_zone": "중앙",
            "is_outside": False,
            "x_normalized": 0.90,
            "y_normalized": 0.50,
        }
    """
    # 경기장 외각 체크
    is_outside = x < 0 or x > 1 or y < 0 or y > 1

    # 정규화 (0~1 범위로 클램핑)
    x_normalized = max(0, min(1, x))
    y_normalized = max(0, min(1, y))

    if is_outside:
        return {
            "zone": "경기장외각",
            "x_zone": None,
            "y_zone": None,
            "is_outside": True,
            "x_normalized": x_normalized,
            "y_normalized": y_normalized,
        }

    # y축 구역 (우측/중앙/좌측)
    if y <= Y_RIGHT_MAX:
        y_zone = "우측"
    elif y <= Y_CENTER_MAX:
        y_zone = "중앙"
    else:
        y_zone = "좌측"

    # x축 구역명 결정
    if x <= X_GOAL_NEAR:
        x_zone = "수비골대앞" if y_zone == "중앙" else "수비코너라인부근"
    elif x <= X_DEFENSE:
        x_zone = "수비큰박스라인부근" if y_zone == "중앙" else "수비지역"
    elif x <= X_MID_DEFENSE:
        x_zone = "미들수비지역"
    elif x <= X_MID_ATTACK:
        x_zone = "미들공격지역"
    elif x <= X_ATTACK:
        x_zone = "공격큰박스라인부근" if y_zone == "중앙" else "공격지역"
    else:
        x_zone = "공격골대앞" if y_zone == "중앙" else "공격코너라인부근"

    zone = get_zone(x, y)

    return {
        "zone": zone,
        "description": ZONE_DESCRIPTIONS.get(zone, zone),
        "x_zone": x_zone,
        "y_zone": y_zone,
        "is_outside": False,
        "x_normalized": x_normalized,
        "y_normalized": y_normalized,
    }


def get_penalty_area_zone(x: float, y: float) -> str:
    """
    페널티 박스 기준 구역 분류

    페널티 박스 추정 좌표:
    - x: 0.83 ~ 1.0 (상대팀 페널티박스)
    - y: 0.21 ~ 0.79 (페널티박스 너비)

    Returns:
        "페널티박스내", "페널티박스외곽", "원거리" 중 하나
    """
    if x < 0 or x > 1 or y < 0 or y > 1:
        return "경기장외각"

    # 상대팀 페널티 박스 (공격 시)
    if x >= 0.83 and 0.21 <= y <= 0.79:
        return "페널티박스내"
    elif x >= 0.67:
        return "페널티박스외곽"
    else:
        return "원거리"


# 전체 구역 목록 (19개)
ALL_ZONES = [
    # 수비 골대앞 (x: 0~0.17)
    "좌측_수비코너라인부근",
    "중앙_수비골대앞",
    "우측_수비코너라인부근",
    # 수비지역 (x: 0.17~0.33)
    "좌측_수비지역",
    "중앙_수비큰박스라인부근",
    "우측_수비지역",
    # 미들수비지역 (x: 0.33~0.5)
    "좌측_미들수비지역",
    "중앙_미들수비지역",
    "우측_미들수비지역",
    # 미들공격지역 (x: 0.5~0.67)
    "좌측_미들공격지역",
    "중앙_미들공격지역",
    "우측_미들공격지역",
    # 공격지역 (x: 0.67~0.83)
    "좌측_공격지역",
    "중앙_공격큰박스라인부근",
    "우측_공격지역",
    # 공격 골대앞 (x: 0.83~1.0)
    "좌측_공격코너라인부근",
    "중앙_공격골대앞",
    "우측_공격코너라인부근",
    # 경기장외각
    "경기장외각",
]


# 구역별 한글 설명 (RAG 텍스트 생성용)
ZONE_DESCRIPTIONS = {
    # 수비 골대앞 영역
    "좌측_수비코너라인부근": "좌측 수비 코너 라인 부근 (자기 골대 근처)",
    "중앙_수비골대앞": "중앙 수비 골대 앞 (자기 골대 정면)",
    "우측_수비코너라인부근": "우측 수비 코너 라인 부근 (자기 골대 근처)",
    # 수비지역
    "좌측_수비지역": "좌측 수비 지역",
    "중앙_수비큰박스라인부근": "중앙 수비 큰 박스 라인 부근 (페널티 에어리어 경계)",
    "우측_수비지역": "우측 수비 지역",
    # 미들수비지역
    "좌측_미들수비지역": "좌측 미드필드 수비 지역",
    "중앙_미들수비지역": "중앙 미드필드 수비 지역",
    "우측_미들수비지역": "우측 미드필드 수비 지역",
    # 미들공격지역
    "좌측_미들공격지역": "좌측 미드필드 공격 지역",
    "중앙_미들공격지역": "중앙 미드필드 공격 지역",
    "우측_미들공격지역": "우측 미드필드 공격 지역",
    # 공격지역
    "좌측_공격지역": "좌측 공격 지역 (상대 진영)",
    "중앙_공격큰박스라인부근": "중앙 공격 큰 박스 라인 부근 (상대 페널티 에어리어 경계)",
    "우측_공격지역": "우측 공격 지역 (상대 진영)",
    # 공격 골대앞 영역
    "좌측_공격코너라인부근": "좌측 공격 코너 라인 부근 (상대 골대 근처)",
    "중앙_공격골대앞": "중앙 공격 골대 앞 (상대 골대 정면, 슈팅 최적 위치)",
    "우측_공격코너라인부근": "우측 공격 코너 라인 부근 (상대 골대 근처)",
    # 경기장외각
    "경기장외각": "경기장 밖",
}


def get_zone_description(zone: str) -> str:
    """구역명을 자연어 설명으로 변환"""
    return ZONE_DESCRIPTIONS.get(zone, zone)


if __name__ == "__main__":
    zone = get_zone(x, y)
    desc = get_zone_description(zone)

    # print(f"({x:.2f}, {y:.2f}) → {zone}")
    # print(f"  설명: {desc}")
    # print()
