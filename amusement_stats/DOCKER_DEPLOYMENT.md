# ParkPulse Analytics Docker 部署说明

## 镜像地址

```text
crpi-9gmsq2s17re73ia9.cn-qingdao.personal.cr.aliyuncs.com/yyh163/parkpulse-analytics
```

## 构建方式

项目支持两种构建方式：

- GitHub Actions：仓库根目录 `.github/workflows/docker-acr.yml`
- 阿里云 ACR 内置构建：仓库根目录 `Dockerfile`

如果使用 GitHub Actions 构建并推送镜像，建议关闭 ACR 内置自动构建，避免重复构建。

## GitHub Secrets

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions` 中配置：

```text
ACR_USERNAME=你的阿里云 ACR 用户名
ACR_PASSWORD=你的阿里云 ACR 密码或访问凭证
```

不要把 ACR 密码、Docker 登录 Token、Django 生产密钥提交到仓库。

## ACR 内置构建规则

仓库根目录已提供兼容用 `Dockerfile`，ACR 可以使用默认规则：

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

## 创建容器

镜像：

```text
crpi-9gmsq2s17re73ia9.cn-qingdao.personal.cr.aliyuncs.com/yyh163/parkpulse-analytics:latest
```

端口：

```text
主机端口：8000
容器端口：8000
协议：TCP
```

建议挂载：

```text
主机目录：/data/parkpulse/data
容器目录：/app/data
```

```text
主机目录：/data/parkpulse/media
容器目录：/app/media
```

容器启动脚本会自动创建并修正 `/app/data`、`/app/media`、`/app/staticfiles` 权限，再降权为 `parkpulse` 用户运行 Django。

容器运行用户请保持镜像默认值，或者显式设置为：

```text
root
```

不要把容器运行用户设置为 `999`、`parkpulse` 或其他非 root 用户；否则启动脚本无法修正挂载目录权限。

## 核心环境变量

```text
DJANGO_SECRET_KEY=生产随机密钥
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=服务器IP,localhost,127.0.0.1
DJANGO_DB_PATH=/app/data/db.sqlite3
DJANGO_MEDIA_ROOT=/app/media
DJANGO_STATIC_ROOT=/app/staticfiles
QUEUE_API_KEY=生产队列接口密钥
PORT=8000
```

如果使用 HTTPS 域名和反向代理，再设置：

```text
DJANGO_CSRF_TRUSTED_ORIGINS=https://你的域名
DJANGO_SECURE_PROXY_SSL_HEADER=1
```

## 演示环境一键初始化

容器环境变量增加：

```text
DJANGO_SEED_DEMO_DATA=1
DEMO_ADMIN_PASSWORD=ParkPulse@2026!
DEMO_STAFF_PASSWORD=Staff@2026!
DEMO_VISITOR_PASSWORD=Visitor@2026!
```

可选调整演示数据规模：

```text
DJANGO_SHOWCASE_DAYS=90
DJANGO_SHOWCASE_RECORDS_PER_DAY=120
```

容器启动顺序为：

```text
collectstatic -> migrate -> seed_showcase_data -> rebuild_heat_snapshots -> train_heat_forecast -> gunicorn
```

初始化完成后，如果不希望每次重启都检查和补齐演示数据，可以把：

```text
DJANGO_SEED_DEMO_DATA=0
```

演示账号：

```text
demo_admin   / ParkPulse@2026!
demo_staff   / Staff@2026!
demo_visitor / Visitor@2026!
```

## 本地构建验证

在仓库根目录执行：

```powershell
docker build -t parkpulse-analytics:local .
```

或显式使用 Django 子目录 Dockerfile：

```powershell
docker build -f amusement_stats/Dockerfile -t parkpulse-analytics:local amusement_stats
```

运行：

```powershell
docker run --rm -p 8000:8000 `
  -e DJANGO_SECRET_KEY="change-me" `
  -e DJANGO_DEBUG=0 `
  -e DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost" `
  -e DJANGO_SEED_DEMO_DATA=1 `
  -v parkpulse_data:/app/data `
  -v parkpulse_media:/app/media `
  parkpulse-analytics:local
```

访问：

```text
http://127.0.0.1:8000/healthz/
http://127.0.0.1:8000/
http://127.0.0.1:8000/visitor/
```

## 运行策略

- 容器启动时默认执行 `collectstatic` 和 `migrate`。
- SQLite 数据保存在 `/app/data/db.sqlite3`。
- 上传文件保存在 `/app/media`。
- 如需跳过启动迁移，可设置 `DJANGO_MIGRATE=0`。
- 如需跳过静态文件收集，可设置 `DJANGO_COLLECTSTATIC=0`。
- 默认 Docker 镜像只安装 `requirements.txt`，不安装 `requirements-ml.txt`；预测会自动使用轻量模型降级运行。
