"""Gemini 기반 Git 커밋 메시지 추천 API 서버."""

from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field


MODEL_NAME = "gemini-2.5-flash"
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(feat|fix|refactor|chore|docs|test|style|perf|ci|build)"
    r"(\([^)]+\))?:\s+.+$",
    re.IGNORECASE,
)


class CommitMessageRequest(BaseModel):
    """커밋 메시지 추천 요청 본문을 정의한다."""

    code_diff: str = Field(..., min_length=1, description="git diff 결과 텍스트")


class CommitMessageResponse(BaseModel):
    """커밋 메시지 추천 응답 본문을 정의한다."""

    success: bool
    recommended_messages: str


def create_prompt(code_diff: str) -> str:
    """Gemini가 커밋 메시지를 생성할 수 있도록 프롬프트를 구성한다."""

    return f"""
당신은 10년 차 시니어 개발자입니다.
아래 git diff를 분석하고 Conventional Commits 규칙에 맞는 한국어 Git 커밋 메시지 3개를 추천하세요.

출력 규칙:
1. 타입은 feat, fix, refactor, chore, docs, test, style, perf, ci, build 중 가장 적절한 값을 사용합니다.
2. 각 메시지는 한 줄로 작성하고 형식은 `type: 설명` 입니다.
3. 설명은 자연스러운 한국어로 작성하며 변경 의도를 분명하게 드러냅니다.
4. 총 3개만 작성하고, 각 줄은 `- `로 시작합니다.
5. 추가 설명, 서론, 코드 블록, 주석은 출력하지 않습니다.

git diff:
{code_diff}
""".strip()


def normalize_recommendations(raw_text: str) -> str:
    """Gemini 응답을 3개의 가독성 좋은 메시지 문자열로 정리한다."""

    if not raw_text or not raw_text.strip():
        raise ValueError("Gemini 응답이 비어 있습니다.")

    candidate_messages: list[str] = []
    cleaned_messages: list[str] = []

    for line in raw_text.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue

        normalized_line = re.sub(r"^[-*\d\.\)\s]+", "", stripped_line).strip()
        if normalized_line:
            candidate_messages.append(normalized_line)
            if CONVENTIONAL_COMMIT_PATTERN.match(normalized_line):
                cleaned_messages.append(normalized_line)

    selected_messages = (
        cleaned_messages if len(cleaned_messages) >= 3 else candidate_messages
    )

    if len(selected_messages) < 3:
        raise ValueError("Gemini 응답에서 3개의 커밋 메시지를 추출하지 못했습니다.")

    formatted_lines = [
        f"{index}. {message}"
        for index, message in enumerate(selected_messages[:3], start=1)
    ]
    return "\n".join(formatted_lines)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 시 Gemini 모델을 초기화한다."""

    load_dotenv(override=True)
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. "
            ".env 파일 또는 시스템 환경 변수에 값을 추가하세요."
        )

    genai.configure(api_key=api_key)
    app.state.gemini_model = genai.GenerativeModel(MODEL_NAME)
    yield


app = FastAPI(
    title="Commit Message Recommender API",
    description="Gemini API로 Git 커밋 메시지를 추천하는 FastAPI 서버",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """서버 상태를 간단히 확인한다."""

    return {"status": "ok"}


@app.post(
    "/predict/commit-message",
    response_model=CommitMessageResponse,
    summary="Git 커밋 메시지 추천",
)
async def predict_commit_message(
    payload: CommitMessageRequest,
    request: Request,
) -> CommitMessageResponse:
    """전달받은 git diff를 기반으로 커밋 메시지 3개를 추천한다."""

    try:
        prompt = create_prompt(payload.code_diff)
        response = await run_in_threadpool(
            request.app.state.gemini_model.generate_content,
            prompt,
        )
        raw_text = getattr(response, "text", "")
        recommended_messages = normalize_recommendations(raw_text)

        return CommitMessageResponse(
            success=True,
            recommended_messages=recommended_messages,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"커밋 메시지 추천 생성 중 오류가 발생했습니다: {exc}",
        ) from exc
