# Gemini Commit Message API

FastAPI와 Gemini API를 사용해 `git diff`를 분석하고 한국어 Git 커밋 메시지 3개를 추천하는 프로젝트입니다.
로컬 개발 환경에서는 Conda 가상환경으로 바로 실행할 수 있고, `main` 브랜치에 push하면 GitHub Actions가 Docker 이미지를 빌드해서 Docker Hub로 자동 푸시하도록 구성했습니다.

## 프로젝트 구성

- `main.py`: Gemini 기반 커밋 메시지 추천 FastAPI 서버
- `ask_commit.py`: `git diff --staged` 결과를 서버에 보내는 터미널 클라이언트
- `Dockerfile`: API 서버 컨테이너 이미지 빌드 파일
- `docker-compose.yml`: 로컬 서버에서 Docker 컨테이너 실행용 설정
- `.github/workflows/docker-publish.yml`: GitHub Actions Docker 자동 배포 워크플로
- `deploy_local.ps1`: Docker Hub의 최신 이미지를 받아 로컬 서버를 재배포하는 PowerShell 스크립트

## 1. Conda 로컬 실행

### 1-1. 가상환경 생성

```powershell
cd "C:\school\2-1\HelloDevOps"
conda create -n commit-msg-api python=3.11 -y
conda activate commit-msg-api
```

### 1-2. 패키지 설치

```powershell
pip install -r requirements.txt
```

### 1-3. 환경 변수 파일 생성

```powershell
Copy-Item .env.example .env
```

`.env` 예시:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

### 1-4. 서버 실행

```powershell
uvicorn main:app --reload
```

서버 확인:

- Health Check: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`

## 2. 클라이언트 실험

다른 터미널에서 실행합니다.

```powershell
conda activate commit-msg-api
cd "커밋할_실제_Git_저장소"
git add .
python "C:\school\2-1\HelloDevOps\ask_commit.py"
```

클라이언트는 현재 터미널 위치의 Git 저장소에서 `git diff --staged`를 읽고, 로컬 FastAPI 서버로 전송합니다.

## 3. Docker 로컬 실행

### 3-1. 이미지 빌드

```powershell
docker build -t commit-message-api:local .
```

### 3-2. 컨테이너 실행

```powershell
docker run --rm -p 8000:8000 --env-file .env commit-message-api:local
```

## 4. GitHub Actions로 Docker Hub 자동 푸시

`main` 브랜치에 push하면 GitHub Actions가 아래 작업을 수행합니다.

1. 저장소 체크아웃
2. Python 문법 검사
3. Docker 이미지 빌드
4. Docker Hub 로그인
5. `latest`와 짧은 SHA 태그로 이미지 푸시

### 4-1. Docker Hub 준비

Docker Hub에 아래 이름으로 저장소를 하나 생성하세요.

- `hello-devops-commit-message-api`

예시 최종 이미지 이름:

- `your-dockerhub-username/hello-devops-commit-message-api:latest`

### 4-2. GitHub Secrets 설정

GitHub 저장소 `Settings -> Secrets and variables -> Actions`에 아래 두 값을 추가하세요.

- `DOCKERHUB_USERNAME`: Docker Hub 사용자명
- `DOCKERHUB_TOKEN`: Docker Hub Access Token

`DOCKERHUB_TOKEN`은 Docker Hub 비밀번호 대신 Access Token을 쓰는 것을 권장합니다.

## 5. 로컬 서버에서 최신 Docker 이미지 배포

GitHub Actions가 Docker Hub로 새 이미지를 올린 뒤, 로컬 서버에서는 아래 명령으로 최신 버전을 반영할 수 있습니다.

```powershell
cd "C:\school\2-1\HelloDevOps"
.\deploy_local.ps1 -DockerImage "your-dockerhub-username/hello-devops-commit-message-api:latest"
```

이 스크립트는 아래 작업을 수행합니다.

1. Docker Hub에서 최신 이미지 pull
2. `docker-compose.yml` 기준으로 컨테이너 재시작

## 6. 전체 흐름 요약

```text
코드 수정
-> git push origin main
-> GitHub Actions 실행
-> Docker 이미지 빌드
-> Docker Hub 업로드
-> 로컬 서버에서 deploy_local.ps1 실행
-> 최신 컨테이너 반영
```

## 7. 참고

- `.env` 파일은 Git에 포함하지 않습니다.
- GitHub Actions가 자동 배포하는 범위는 Docker Hub 푸시까지입니다.
- 로컬 컴퓨터까지 완전 자동 배포하려면 이후 단계로 self-hosted runner 또는 Watchtower 같은 추가 구성이 필요합니다.
