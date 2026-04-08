"""로컬 Git 변경 사항을 서버로 보내 커밋 메시지를 추천받는 클라이언트."""

from __future__ import annotations

import subprocess
import sys

import requests


SERVER_URL = "http://127.0.0.1:8000/predict/commit-message"
REQUEST_TIMEOUT = 60


def get_staged_diff() -> str:
    """스테이징된 Git 변경 사항을 텍스트로 가져온다."""

    result = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        error_message = result.stderr.strip() or "git diff 실행에 실패했습니다."
        raise RuntimeError(error_message)

    return result.stdout.strip()


def request_commit_messages(code_diff: str) -> dict:
    """FastAPI 서버에 커밋 메시지 추천을 요청한다."""

    response = requests.post(
        SERVER_URL,
        json={"code_diff": code_diff},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def print_recommendations(recommended_messages: str) -> None:
    """추천받은 커밋 메시지를 터미널에 보기 좋게 출력한다."""

    separator = "=" * 60
    print(separator)
    print("추천 Git 커밋 메시지")
    print(separator)
    print(recommended_messages)
    print(separator)


def main() -> None:
    """Git diff를 읽고 API 서버에 전송한 뒤 결과를 출력한다."""

    try:
        code_diff = get_staged_diff()
    except RuntimeError as exc:
        print(f"[오류] {exc}")
        sys.exit(1)

    if not code_diff:
        print("[안내] 스테이징된 변경 사항이 없습니다. 먼저 `git add`를 실행해 주세요.")
        sys.exit(0)

    try:
        result = request_commit_messages(code_diff)
    except requests.exceptions.ConnectionError:
        print(
            "[오류] 로컬 API 서버에 연결할 수 없습니다. "
            "`uvicorn main:app --reload`로 서버가 실행 중인지 확인해 주세요."
        )
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        response_text = exc.response.text if exc.response is not None else str(exc)
        print(f"[오류] 서버가 요청을 처리하지 못했습니다: {response_text}")
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        print(f"[오류] 서버 요청 중 문제가 발생했습니다: {exc}")
        sys.exit(1)

    if not result.get("success"):
        print("[오류] 서버가 커밋 메시지 추천에 실패했습니다.")
        sys.exit(1)

    print_recommendations(result.get("recommended_messages", "추천 결과가 없습니다."))


if __name__ == "__main__":
    main()
