# 活动智囊后端

基于 FastAPI 的校园社团活动策划与执行包生成服务。

## 本地启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

## 接口文档

- Swagger UI：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/healthz

## 目录结构

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── agent/
├── tests/
├── requirements.txt
└── .env.example
```
