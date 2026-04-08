param(
    [Parameter(Mandatory = $true)]
    [string]$DockerImage
)

$env:DOCKER_IMAGE = $DockerImage

Write-Host "최신 Docker 이미지를 가져옵니다: $DockerImage"
docker compose pull

if ($LASTEXITCODE -ne 0) {
    throw "Docker 이미지 pull에 실패했습니다."
}

Write-Host "컨테이너를 재시작합니다."
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose 실행에 실패했습니다."
}

Write-Host "배포가 완료되었습니다."
