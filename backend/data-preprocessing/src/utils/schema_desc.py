"""
FC Online MatchDetail API 스키마 설명
출처: https://openapi.nexon.com/ko/game/fconline/?id=3

각 필드의 의미와 코드 매핑을 정의합니다.
"""

# ============================================================================
# 슈팅 종류 (shootDetail.type)
# ============================================================================
SHOT_TYPE = {
    1: "normal",           # 일반 슛
    2: "finesse",          # 감아차기
    3: "header",           # 헤딩
    4: "lob",              # 로빙슛
    5: "flare",            # 플레어슛
    6: "low",              # 낮은 슛
    7: "volley",           # 발리
    8: "free-kick",        # 프리킥
    9: "penalty",          # 페널티킥
    10: "knuckle",         # 무회전슛
    11: "bicycle",         # 바이시클킥
    12: "super",           # 파워샷
}

SHOT_TYPE_KOREAN = {
    1: "일반 슛",
    2: "감아차기",
    3: "헤딩",
    4: "로빙슛",
    5: "플레어슛",
    6: "낮은 슛",
    7: "발리",
    8: "프리킥",
    9: "페널티킥",
    10: "무회전슛",
    11: "바이시클킥",
    12: "파워샷",
}

def get_shot_type(code: int) -> str:
    """슈팅 종류 코드 → 영문명 변환"""
    return SHOT_TYPE.get(code, "normal")

def get_shot_type_korean(code: int) -> str:
    """슈팅 종류 코드 → 한글명 변환"""
    return SHOT_TYPE_KOREAN.get(code, "일반 슛")


# ============================================================================
# 슈팅 결과 (shootDetail.result)
# ============================================================================
SHOT_RESULT = {
    1: "유효슈팅",          # ontarget
    2: "빗나감",            # offtarget
    3: "골",               # goal
}

def get_shot_result(code: int) -> str:
    """슈팅 결과 코드 → 한글명 변환"""
    return SHOT_RESULT.get(code, "알수없음")


# ============================================================================
# 매치 종료 타입 (matchDetail.matchEndType)
# ============================================================================
MATCH_END_TYPE = {
    0: "정상종료",
    1: "몰수승",
    2: "몰수패",
}

def get_match_end_type(code: int) -> str:
    """매치 종료 타입 코드 → 한글명 변환"""
    return MATCH_END_TYPE.get(code, "알수없음")


# ============================================================================
# 컨트롤러 타입 (matchDetail.controller)
# ============================================================================
CONTROLLER_TYPE = {
    "keyboard": "키보드",
    "pad": "패드",
    "etc": "기타",
}

def get_controller_type(code: str) -> str:
    """컨트롤러 타입 → 한글명 변환"""
    return CONTROLLER_TYPE.get(code, code)


# ============================================================================
# 필드 설명 (API 스키마 기준)
# ============================================================================
FIELD_DESCRIPTIONS = {
    # === MatchDetail (최상위) ===
    "matchId": "매치 고유 식별자",
    "matchDate": "매치 일자 (UTC0)",
    "matchType": "매치 종류 (/metadata/matchtype API 참고)",
    "matchInfo": "매치 참여 플레이어별 매치 상세",
    
    # === matchInfo[] ===
    "ouid": "계정 식별자",
    "nickname": "유저 닉네임",
    
    # === matchInfo[].matchDetail (매치 결과 상세 정보) ===
    "seasonId": "시즌 ID",
    "matchResult": "매치 결과 (승, 무, 패)",
    "matchEndType": "매치종료 타입 (0 정상종료, 1 몰수승, 2 몰수패)",
    "systemPause": "게임 일시정지 수",
    "foul": "파울 수",
    "injury": "부상 수",
    "redCards": "받은 레드카드 수",
    "yellowCards": "받은 옐로카드 수",
    "dribble": "드리블 거리(야드)",
    "cornerKick": "코너킥 수",
    "possession": "점유율",
    "OffsideCount": "오프사이드 수",
    "averageRating": "경기 평점",
    "controller": "사용한 컨트롤러 타입 (keyboard / pad / etc 중 1)",
    
    # === matchInfo[].shoot (슈팅 정보) ===
    "shootTotal": "총 슛 수",
    "effectiveShootTotal": "총 유효슛 수",
    "shootOutScore": "승부차기 슛 수",
    "goalTotal": "총 골 수 (실제 골 수, goalInPenalty + goalOutPenalty + goalPenaltyKick)",
    "goalTotalDisplay": "게임 종료 후 유저에게 노출되는 골 수",
    "ownGoal": "자책 골 수",
    "shootHeading": "헤딩 슛 수",
    "goalHeading": "헤딩 골 수",
    "shootFreekick": "프리킥 슛 수",
    "goalFreekick": "프리킥 골 수",
    "shootInPenalty": "인패널티 슛 수",
    "goalInPenalty": "인패널티 골 수",
    "shootOutPenalty": "아웃패널티 슛 수",
    "goalOutPenalty": "아웃패널티 골 수",
    "shootPenaltyKick": "패널티킥 슛 수",
    "goalPenaltyKick": "패널티킥 골 수",
    
    # === matchInfo[].shootDetail[] (슈팅 별 상세정보) ===
    "goalTime": "슛 시간 (인코딩된 값, decode_goaltime 필요)",
    "x": "슛 x좌표 (전체 경기장 기준)",
    "y": "슛 y좌표 (전체 경기장 기준)",
    "type": "슛 종류 (1~12, SHOT_TYPE 참고)",
    "result": "슛 결과 (1 ontarget, 2 offtarget, 3 goal)",
    "spId": "슈팅 선수 고유 식별자 (/metadata/spid API 참고)",
    "spGrade": "슈팅 선수 강화 등급",
    "spLevel": "슈팅 선수 레벨",
    "spIdType": "슈팅 선수 임대 여부 (임대선수 true, 비임대선수 false)",
    "assist": "어시스트 받은 골 여부 (받음 true, 안받음 false)",
    "assistSpId": "어시스트 선수 고유 식별자 (/metadata/spid API 참고)",
    "assistX": "어시스트 x좌표",
    "assistY": "어시스트 y좌표",
    "hitPost": "골포스트 맞춤 여부 (맞춤 true, 못 맞춤 false)",
    "inPenalty": "페널티박스 안에서 넣은 슛 여부 (안 true, 밖 false)",
    
    # === matchInfo[].pass (패스 정보) ===
    "passTry": "패스 시도 수",
    "passSuccess": "패스 성공 수",
    "shortPassTry": "숏 패스 시도 수",
    "shortPassSuccess": "숏 패스 성공 수",
    "longPassTry": "롱 패스 시도 수",
    "longPassSuccess": "롱 패스 성공 수",
    "bouncingLobPassTry": "바운싱 롭 패스 시도 수",
    "bouncingLobPassSuccess": "바운싱 롭 패스 성공 수",
    "drivenGroundPassTry": "드리븐 땅볼 패스 시도 수",
    "drivenGroundPassSuccess": "드리븐 땅볼 패스 성공 수",
    "throughPassTry": "스루 패스 시도 수",
    "throughPassSuccess": "스루 패스 성공 수",
    "lobbedThroughPassTry": "로빙 스루 패스 시도 수",
    "lobbedThroughPassSuccess": "로빙 스루 패스 성공 수",
    
    # === matchInfo[].defence (수비 정보) ===
    "blockTry": "블락 시도 수",
    "blockSuccess": "블락 성공 수",
    "tackleTry": "태클 시도 수",
    "tackleSuccess": "태클 성공 수",
    
    # === matchInfo[].player[] (경기 사용 선수 정보) ===
    "spPosition": "선수 포지션 (/metadata/spposition API 참고)",
    # spId, spGrade는 위에서 정의됨
    
    # === matchInfo[].player[].status (선수 경기 스탯) ===
    "shoot": "슛 수",
    "effectiveShoot": "유효 슛 수",
    # "assist": "어시스트 수",  # shootDetail에서 정의됨 (의미 다름)
    "goal": "득점 수",
    # "dribble": "드리블 거리(야드)",  # matchDetail에서 정의됨
    "intercept": "인터셉트 수",
    "defending": "디펜딩 수",
    # "passTry", "passSuccess"  # pass에서 정의됨
    "dribbleTry": "드리블 시도 수",
    "dribbleSuccess": "드리블 성공 수",
    "ballPossesionTry": "볼 소유 시도 수",
    "ballPossesionSuc": "볼 소유 성공 수",
    "aerialTry": "공중볼 경합 시도 수",
    "aerialSuccess": "공중볼 경합 성공 수",
    "block": "블락 성공 수",
    "tackle": "태클 성공 수",
    # "yellowCards", "redCards"  # matchDetail에서 정의됨
    "spRating": "선수 평점",
}

def get_field_description(field_name: str) -> str:
    """필드명 → 설명 반환"""
    return FIELD_DESCRIPTIONS.get(field_name, "")


# ============================================================================
# goalTime 인코딩 설명 (참고용)
# ============================================================================
"""
goalTime 인코딩 규칙:
- 2^24 * 0 ~ 2^24 * 1 - 1: 전반전, 그대로 사용 (초 단위)
- 2^24 * 1 ~ 2^24 * 2 - 1: 후반전, 2^24*1 차감 후 45*60s 더하기
- 2^24 * 2 ~ 2^24 * 3 - 1: 연장전 전반전, 2^24*2 차감 후 90*60s 더하기
- 2^24 * 3 ~ 2^24 * 4 - 1: 연장전 후반전, 2^24*3 차감 후 105*60s 더하기
- 2^24 * 4 ~ 2^24 * 5 - 1: 승부차기, 2^24*4 차감 후 120*60s 더하기

→ utils.goaltime.decode_goaltime() 사용
"""
