# ParkPulse Analytics Docker 部署说明

## 镜像地址

```text
crpi-9gmsq2s17re73ia9.cn-qingdao.personal.cr.aliyuncs.com/yyh163/parkpulse-analytics
```

## 推荐构建方式：GitHub Actions

本项目的 GitHub 仓库根目录是整个 `F:\ghq`，Django 项目位于仓库子目录 `amusement_stats/`。

GitHub Actions workflow 必须放在仓库根目录：

```text
.github/workflows/docker-acr.yml
```

当前 workflow 会在 `main` 分支变更后自动执行：

1. 进入 `amusement_stats/` 安装依赖并运行 Django 检查和测试。
2. 使用 `amusement_stats/Dockerfile` 构建镜像。
3. 推送到阿里云 ACR：
   - `latest`
   - `sha-<commit-sha>`
   - `v*` 标签推送时的版本标签

## GitHub Secrets

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions` 中配置：

```text
ACR_USERNAME=你的阿里云 ACR 用户名
ACR_PASSWORD=你的阿里云 ACR 密码或访问凭证
```

不要把 ACR 密码、Docker 登录 Token、Django 生产密钥提交到仓库。

## ACR 内置构建规则说明

如果使用 GitHub Actions 构建并推送镜像，建议关闭阿里云 ACR 的“自动构建规则”，避免重复构建。

当前仓库根目录也提供了兼容用 `Dockerfile`，因此 ACR 内置构建可以继续使用默认规则：

```text
类型：Branch
Branch/Tag：main
构建上下文目录：/
Dockerfile 文件名：Dockerfile
镜像版本：latest
```

也可以直接按 Django 子目录构建：

```text
类型：Branch
Branch/Tag：main
构建上下文目录：/amusement_stats
Dockerfile 文件名：Dockerfile
镜像版本：latest
```

此前 ACR 日志中 `open .../Dockerfile: no such file or directory` 的原因是：ACR 使用了根目录构建规则，但仓库根目录当时没有 `Dockerfile`。

## 本地构建验证

在仓库根目录执行：

```powershell
docker build -t parkpulse-analytics:local .
```

或显式使用 Django 子目录 Dockerfile：

```powershell
docker build -f amusement_stats/Dockerfile -t parkpulse-analytics:local amusement_stats
```

或进入 Django 项目目录执行：

```powershell
cd amusement_stats
docker build -t parkpulse-analytics:local .
```

运行：

```powershell
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

进入 Django 项目目录：

```powershell
cd amusement_stats
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
