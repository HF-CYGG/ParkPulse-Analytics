# 智能热度与路线推荐升级说明

## 模块边界

- `analytics.models`：保存热度快照、预测结果、模型评估、评分、设备事件、节假日和促销活动。
- `analytics.services.heat`：统一多维热度评分，输出总分、六类分项和可解释指标。
- `analytics.services.forecasting`：生成未来 7 天 baseline 预测和 MAE/MSE/R2 评估。Prophet/LSTM 作为可选增强依赖，不阻断基础运行。
- `analytics.services.spatial`：结合项目坐标生成热度辐射范围和周边业态连带热度。
- `analytics.services.recommendations`：基于游客画像、实时排队和热度数据生成避峰、路线、组合推荐。

## 运维命令

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py rebuild_heat_snapshots --days 90
.\venv\Scripts\python.exe manage.py train_heat_forecast --model all --days 90 --horizon 7
.\venv\Scripts\python.exe manage.py seed_analytics_demo_data
```

## 可选 ML 依赖

普通安装仍使用：

```bat
install_deps.bat
```

需要安装 Prophet / PyTorch / scikit-learn 时使用：

```bat
install_deps.bat --with-ml
```

如果可选 ML 依赖安装失败，不影响 Django 基础功能；系统会使用 baseline 预测模式。

## 关键 API

- `/analytics/api/heat-score/`
- `/analytics/api/forecast/`
- `/analytics/api/forecast-evaluation/?refresh=1`
- `/analytics/api/spatial-heat/`
- `/visitor/recommendations/`
- `/visitor/api/recommendations/`
