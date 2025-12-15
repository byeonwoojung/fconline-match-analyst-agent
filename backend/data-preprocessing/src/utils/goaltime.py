"""
goalTime 인코딩/디코딩 유틸리티

FC Online API의 goalTime 형식:
- goalTime 값은 경기 시간(초)과 경기 구간 정보가 인코딩되어 있음
- 전반전: 0 ~ 2^24-1 (그대로 사용, 0~45분)
- 후반전: 2^24 ~ 2^24*2-1 (2^24 차감 후 45분(2700초) 더하기)
- 연장전반: 2^24*2 ~ 2^24*3-1 (2^24*2 차감 후 90분(5400초) 더하기)
- 연장후반: 2^24*3 ~ 2^24*4-1 (2^24*3 차감 후 105분(6300초) 더하기)
- 승부차기: 2^24*4 ~ 2^24*5-1 (2^24*4 차감 후 120분(7200초) 더하기)
"""

# 기준값 (2^24)
BASE = 16777216

# 각 반전의 기준값
HALF_OFFSET = BASE * 1  # 후반전
EXTRA_FIRST_OFFSET = BASE * 2  # 연장전반
EXTRA_SECOND_OFFSET = BASE * 3  # 연장후반
PENALTY_OFFSET = BASE * 4  # 승부차기

# 각 반전에서 더할 초
ADD_SECONDS = {
    "전반": 0,
    "후반": 2700,  # 45분
    "연장전반": 5400,  # 90분
    "연장후반": 6300,  # 105분
    "승부차기": 7200,  # 120분
}


def decode_goaltime(goaltime: int) -> dict:
    """
    goalTime을 사람이 읽을 수 있는 형식으로 디코딩

    Args:
        goaltime: FC Online API의 goalTime 값

    Returns:
        {
            "half": "전반" | "후반" | "연장전반" | "연장후반" | "승부차기",
            "seconds": int (해당 반전 내에서의 초),
            "total_seconds": int (경기 전체에서의 초),
            "minute": int (경기 전체에서의 분),
            "display": "전반 15분" 형식의 문자열
        }
    """
    if goaltime >= PENALTY_OFFSET:
        half = "승부차기"
        seconds = goaltime - PENALTY_OFFSET
    elif goaltime >= EXTRA_SECOND_OFFSET:
        half = "연장후반"
        seconds = goaltime - EXTRA_SECOND_OFFSET
    elif goaltime >= EXTRA_FIRST_OFFSET:
        half = "연장전반"
        seconds = goaltime - EXTRA_FIRST_OFFSET
    elif goaltime >= HALF_OFFSET:
        half = "후반"
        seconds = goaltime - HALF_OFFSET
    else:
        half = "전반"
        seconds = goaltime

    # 해당 반전에서 더할 초를 더해서 전체 경기 시간 계산
    total_seconds = seconds + ADD_SECONDS[half]
    minute = total_seconds // 60

    return {
        "half": half,
        "seconds": seconds,
        "total_seconds": total_seconds,
        "minute": minute,
        "display": f"{half} {minute}분",
    }


def encode_goaltime(half: str, total_minute: int) -> int:
    """
    사람이 읽을 수 있는 형식을 goalTime으로 인코딩

    Args:
        half: "전반" | "후반" | "연장전반" | "연장후반" | "승부차기"
        total_minute: 경기 전체 기준 분

    Returns:
        FC Online API 형식의 goalTime 값 (초 단위)
    """
    total_seconds = total_minute * 60

    if half == "승부차기":
        return PENALTY_OFFSET + (total_seconds - ADD_SECONDS["승부차기"])
    elif half == "연장후반":
        return EXTRA_SECOND_OFFSET + (total_seconds - ADD_SECONDS["연장후반"])
    elif half == "연장전반":
        return EXTRA_FIRST_OFFSET + (total_seconds - ADD_SECONDS["연장전반"])
    elif half == "후반":
        return HALF_OFFSET + (total_seconds - ADD_SECONDS["후반"])
    else:
        return total_seconds


def get_time_range(goaltime: int) -> str:
    """
    골 시간대를 범위로 분류

    Returns:
        "0-15분", "16-30분", "31-45분", "46-60분", "61-75분", "76-90분", "연장전", "승부차기"
    """
    decoded = decode_goaltime(goaltime)
    half = decoded["half"]
    minute = decoded["minute"]  # 전체 경기 기준 분

    if half == "승부차기":
        return "승부차기"

    if half in ["연장전반", "연장후반"]:
        return "연장전"

    # 전체 경기 기준 분으로 시간대 분류
    if minute <= 15:
        return "0-15분"
    elif minute <= 30:
        return "16-30분"
    elif minute <= 45:
        return "31-45분"
    elif minute <= 60:
        return "46-60분"
    elif minute <= 75:
        return "61-75분"
    else:
        return "76-90분"
