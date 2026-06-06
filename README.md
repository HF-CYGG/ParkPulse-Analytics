# ParkPulse Analytics

ParkPulse Analytics is a Django-based amusement park operations analytics platform. It supports ride record management, attraction maintenance, operational dashboards, heat-score forecasting, spatial heat visualization, audit logs, and visitor-facing smart route recommendations.

中文定位：游乐场热门项目统计与智能运营分析平台，面向运营人员、工作人员和游客三类角色，提供数据录入、热度分析、预测预警、园区地图、游客反馈和个性化游玩推荐。

## Tech Stack

- Backend: Python 3.10+, Django 6
- Frontend: Bootstrap 5, ECharts, Plotly, Leaflet/Folium
- Data: SQLite by default, Django ORM models and migrations
- Analytics: multi-dimensional heat scoring, baseline forecasting, optional Prophet/LSTM dependencies

## Repository Layout

| Path | Purpose |
| --- | --- |
| `amusement_stats/` | Django application root, including `manage.py` and dependency files |
| `amusement_stats/amusement_stats/` | Django settings, URL configuration, templates, and static assets |
| `amusement_stats/analytics/` | Heat scoring, forecasting, spatial heat, and recommendation APIs |
| `amusement_stats/dashboard/` | Staff dashboard and statistics views |
| `amusement_stats/visitor/` | Visitor pages, profiles, maps, feedback, and recommendations |
| `README_部署说明.md` | Deployment notes for offline or demo environments |

## Quick Start

Run these commands from `amusement_stats/`:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

For production-style deployment, copy `.env.example` to `.env` and set real values for `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, and `QUEUE_API_KEY`.

Common URLs:

| Page | URL |
| --- | --- |
| Staff login | http://127.0.0.1:8000/login/ |
| Operations dashboard | http://127.0.0.1:8000/ |
| Django admin | http://127.0.0.1:8000/admin/ |
| Visitor portal | http://127.0.0.1:8000/visitor/ |

## Demo and Analytics Commands

```powershell
python manage.py seed_demo_data --days 14 --records-per-day 40
python manage.py seed_analytics_demo_data
python manage.py rebuild_heat_snapshots --days 30
python manage.py train_heat_forecast --model all --days 90 --horizon 7
```

Optional ML dependencies are isolated in `amusement_stats/requirements-ml.txt`. The default system remains usable without installing them.

## Git Notes

This repository intentionally ignores local runtime files such as `venv/`, SQLite databases, logs, media uploads, offline package caches, and generated source snapshots. Source code, migrations, templates, scripts, and documentation remain trackable.
