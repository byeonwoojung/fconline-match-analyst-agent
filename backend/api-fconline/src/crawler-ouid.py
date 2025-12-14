"""
FC Online OUID (계정 식별자) 조회 API
Nexon Open API를 사용하여 구단주 닉네임으로 계정 식별자(OUID)를 조회합니다.
"""

import os
import requests
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# backend/.env 파일에서 환경변수 로드
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class FCOnlineOUIDCrawler:
    """FC Online 계정 식별자(OUID) 조회 클래스"""

    BASE_URL = "https://open.api.nexon.com/fconline/v1/id"

    def __init__(self, api_key: str):
        """
        Args:
            api_key: Nexon Open API 키
        """
        self.api_key = api_key
        self.headers = {"x-nxopen-api-key": api_key}

    def get_ouid(self, nickname: str) -> Optional[str]:
        """
        구단주 닉네임으로 계정 식별자(OUID)를 조회합니다.

        Args:
            nickname: 구단주 닉네임

        Returns:
            OUID 문자열 또는 None (조회 실패 시)
        """
        params = {"nickname": nickname}

        try:
            response = requests.get(self.BASE_URL, headers=self.headers, params=params)
            response.raise_for_status()

            data = response.json()
            return data.get("ouid")

        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                print(f"[ERROR] 잘못된 요청입니다: {e}")
            elif response.status_code == 401:
                print(f"[ERROR] 인증 실패 - API 키를 확인해주세요: {e}")
            elif response.status_code == 404:
                print(f"[ERROR] 존재하지 않는 닉네임입니다: {nickname}")
            elif response.status_code == 429:
                print(f"[ERROR] 요청 한도 초과 - 잠시 후 다시 시도해주세요: {e}")
            elif response.status_code == 500:
                print(f"[ERROR] 서버 내부 오류: {e}")
            else:
                print(f"[ERROR] HTTP 오류 발생: {e}")
            return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 요청 중 오류 발생: {e}")
            return None


def main():
    # 환경변수에서 API 키 로드 (backend/.env)
    api_key = os.getenv("NEXON_API_KEY", "YOUR_API_KEY_HERE")

    if api_key == "YOUR_API_KEY_HERE":
        print("⚠️  API 키를 설정해주세요.")
        print("   환경변수 NEXON_API_KEY를 설정하거나 코드에서 직접 입력하세요.")
        print("   API 키는 https://openapi.nexon.com 에서 발급받을 수 있습니다.")
        return

    crawler = FCOnlineOUIDCrawler(api_key)

    # 테스트: 닉네임으로 OUID 조회
    nickname = input("조회할 구단주 닉네임을 입력하세요: ")

    ouid = crawler.get_ouid(nickname)

    if ouid:
        print(f"\n✅ 조회 성공!")
        print(f"   닉네임: {nickname}")
        print(f"   OUID: {ouid}")
    else:
        print(f"\n❌ '{nickname}' 닉네임의 OUID를 조회할 수 없습니다.")


if __name__ == "__main__":
    main()
