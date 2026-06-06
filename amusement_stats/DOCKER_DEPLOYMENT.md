# ParkPulse Analytics Docker 部署说明

## 镜像地址

```text
crpi-9gmsq2s17re73ia9.cn-qingdao.personal.cr.aliyuncs.com/yyh163/parkpulse-analytics
```

GitHub Actions 会在 `main` 分支推送后构建并推送：

- `latest`
- `sha-<commit-sha>`
- `v*` 标签推送时对应的版本标签

## GitHub Secrets

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions` 中配置：

```text
ACR_USERNAME=你的阿里云 ACR 用户名
ACR_PASSWORD=你的阿里云 ACR 密码或访问凭证
```

不要把 ACR 密码、Docker 登录 Token、Django 生产密钥提交到仓库。

## 本地构建验证

```powershell
docker build -t parkpulse-analytics:local .
docker run --rm -p 8000:8000 `
  -e DJANGO_SECRET_KEY="change-me" `
  -e DJANGO_DEBUG=0 `
  -e DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost" `
  parkpulse-analytics:local
```

访问：

```text
http://127.0.0.1:8000/healthz/
http://127.0.0.1:8000/
```

## 使用 docker compose 部署

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，至少修改：

```text
DJANGO_SECRET_KEY=生产随机密钥
DJANGO_ALLOWED_HOSTS=你的服务器IP,你的域名
DJANGO_CSRF_TRUSTED_ORIGINS=https://你的域名
QUEUE_API_KEY=生产队列接口密钥
```

启动：

```powershell
docker compose up -d
docker compose logs -f parkpulse
```

更新到 ACR 最新镜像：

```powershell
docker compose pull
docker compose up -d
```

## 运行策略

- 容器启动时默认执行 `collectstatic` 和 `migrate`。
- SQLite 数据保存在 Docker volume `parkpulse_data` 的 `/app/data/db.sqlite3`。
- 上传文件保存在 Docker volume `parkpulse_media` 的 `/app/media`。
- 如需跳过启动迁移，可设置 `DJANGO_MIGRATE=0`。
- 如需跳过静态文件收集，可设置 `DJANGO_COLLECTSTATIC=0`。

## 可选 ML 依赖

默认 Docker 镜像只安装 `requirements.txt`，不安装 `requirements-ml.txt`，因此 Prophet / PyTorch 不会增加基础镜像体积。系统会自动使用轻量预测模型。

如需构建包含 ML 依赖的镜像，建议后续新增独立 Dockerfile target 或构建参数，避免影响普通部署镜像。
