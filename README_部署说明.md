# 游乐场运营后台离线部署说明

## 1. 项目目录说明

- 后端项目目录：`amusement_stats`
- Python 依赖清单：`amusement_stats/requirements.txt`
- 离线依赖包目录：`amusement_stats/offline_packages`
- 前端静态资源（已本地化）：`amusement_stats/amusement_stats/static/vendor`

## 2. 目标电脑准备

- Windows 10/11
- Python 3.10+（建议与开发机一致）
- 允许本机命令行执行 Python

## 3. 离线安装步骤

在 `amusement_stats` 目录下执行：

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --no-index --find-links=offline_packages -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

浏览器访问：

- 登录页：`http://127.0.0.1:8000/login/`
- 看板页：`http://127.0.0.1:8000/`

## 4. 演示数据初始化（可选）
    
```powershell
python manage.py seed_demo_data --days 14 --records-per-day 40
```

执行后会自动生成项目和游玩记录，便于答辩演示图表与统计功能。

## 5. 常见问题

- 提示缺依赖：确认使用了 `--no-index --find-links=offline_packages`
- 页面样式丢失：确认 `amusement_stats/static/vendor` 目录完整
- 无法登录：确认已执行 `createsuperuser`
- 数据为空：执行演示数据命令后刷新看板

