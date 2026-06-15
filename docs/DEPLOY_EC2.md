# EC2 배포

Amazon Linux 2023에서 Docker Compose로 API, PostgreSQL, Redis를 실행한다.

## 운영 URL

- API: `http://43.202.51.195`
- Swagger: `http://43.202.51.195/docs`
- ReDoc: `http://43.202.51.195/redoc`
- Health: `http://43.202.51.195/health`

## 배포

```bash
cd /opt/farmu
sudo docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

`.env.production`은 서버에만 두며 Git과 배포 압축 파일에 포함하지 않는다.

## 로그와 상태

```bash
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs -f api
curl -fsS http://localhost/health
```

API 컨테이너는 시작할 때 `alembic upgrade head`를 실행한다. PostgreSQL과 Redis는 외부
포트를 공개하지 않고 Docker 내부 네트워크에서만 접근한다.

## 도메인과 HTTPS

1. 도메인의 A 레코드를 EC2 공인 IP로 연결한다.
2. EC2 보안 그룹에서 TCP 80·443과 UDP 443을 허용한다.
3. `.env.production`에 도메인과 프론트 오리진을 설정한다.

```env
DOMAIN=api.example.com
PUBLIC_BASE_URL=https://api.example.com
CORS_ORIGINS=["https://frontend.example.com"]
```

4. Caddy 오버라이드를 포함해 재기동한다.

```bash
sudo docker compose \
  --env-file .env.production \
  -f docker-compose.prod.yml \
  -f docker-compose.https.yml \
  up -d --build
```

Caddy가 Let's Encrypt 인증서를 자동 발급·갱신한다. DNS 전파 전에는 공인 인증서를
발급할 수 없으므로 도메인 연결 이후 실행한다.
