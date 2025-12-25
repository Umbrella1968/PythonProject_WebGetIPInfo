from datetime import datetime, timedelta

from fastapi import FastAPI, Request, BackgroundTasks, Depends, Query
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime,
    func, desc
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session

import get_client_ip
import fetch_ipinfo

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI(title="IP Logger with BackgroundTasks")

# -------------------------
# Database setup (SQLite)
# -------------------------
engine = create_engine(
    "sqlite:///visitors.db",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


# -------------------------
# 3) ORM Model
# -------------------------
class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, index=True, nullable=False)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(), index=True)
    geo_info_region =Column(String, nullable=True)


Base.metadata.create_all(bind=engine)


# -------------------------
# 4) DB dependency
# -------------------------
def get_db():
    """FastAPI 依赖注入：每个请求创建一个 session，用完关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# Background task: save visit and get ipinfo
# -------------------------
def save_visit_to_db(ip: str, ua: str | None, dedup_seconds: int,geo_info: dict | None):
    """
    后台任务：保存访问记录（带去重逻辑）
    dedup_seconds: 同一个 IP 在多少秒内只记录一次
    """
    db: Session = SessionLocal()
    try:
        if dedup_seconds > 0:
            # 查找该 IP 在 dedup_seconds 时间窗口内是否已经记录过
            threshold = datetime.now() - timedelta(seconds=dedup_seconds)
            exists = (
                db.query(Visit)
                .filter(Visit.ip == ip, Visit.created_at >= threshold)
                .first()
            )
            if exists:
                # 已经记录过了 -> 不插入
                return

        db.add(Visit(ip=ip, user_agent=ua, created_at=datetime.now(),geo_info_region=geo_info.get("region")))
        db.commit()
    finally:
        db.close()

# -------------------------
# Endpoint: /
# -------------------------
@app.get("/")
async def whoami(
    request: Request,
    background_tasks: BackgroundTasks,
    dedup_seconds: int = Query(60, ge=0, description="去重窗口（秒），0 表示不去重"),
):

    ip = get_client_ip(request)
    ua = request.headers.get("user-agent")
    geo_info=await fetch_ipinfo(ip)

    #后台任务
    background_tasks.add_task(save_visit_to_db, ip, ua, dedup_seconds,geo_info)

    return {"ip": ip, "user_agent": ua, "dedup_seconds": dedup_seconds,"geo_info": geo_info}



# -------------------------
# 9) Endpoint: stats
# -------------------------
@app.get("/logs")
def stats(
    db: Session = Depends(get_db),
    top_n: int = Query(10, ge=1, le=100),
    hours: int = Query(24, ge=1, le=720, description="统计最近 N 小时"),
):
    """
    统计访问量：
    - total_visits：总访问数
    - unique_ips：独立 IP 数
    - top_ips：访问次数最多的 IP
    """
    since = datetime.now() - timedelta(hours=hours)

    # 总访问量
    total_visits = (
        db.query(func.count(Visit.id))
        .filter(Visit.created_at >= since)
        .scalar()
    )

    # 独立 IP 数
    unique_ips = (
        db.query(func.count(func.distinct(Visit.ip)))
        .filter(Visit.created_at >= since)
        .scalar()
    )

    # Top IP 列表
    top_ips = (
        db.query(Visit.ip, func.count(Visit.id).label("cnt"))
        .filter(Visit.created_at >= since)
        .group_by(Visit.ip)
        .order_by(desc("cnt"))
        .limit(top_n)
        .all()
    )

    return {
        "since": since.isoformat(),
        "hours": hours,
        "total_visits": total_visits,
        "unique_ips": unique_ips,
        "top_ips": [{"ip": ip, "count": cnt} for ip, cnt in top_ips],
    }
