"""
重新对数据库中所有商机执行 AI 全量分析（并发多线程）
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 并发数
CONCURRENCY = 10


async def analyze_one(sem: asyncio.Semaphore, opp_id: int, idx: int, total: int) -> bool:
    """分析单条商机，返回是否成功"""
    from app.core.database import async_session
    from app.services.ai_engine import analyze_opportunity_full

    async with sem:
        try:
            async with async_session() as db:
                await analyze_opportunity_full(opp_id, db)
                await db.commit()
            logger.info(f"[{idx}/{total}] 商机 {opp_id} 分析完成")
            return True
        except Exception as e:
            logger.error(f"[{idx}/{total}] 商机 {opp_id} 分析失败: {e}")
            return False


async def main():
    from app.core.database import async_session
    from sqlalchemy import select
    from app.models.opportunity import Opportunity

    async with async_session() as db:
        result = await db.execute(select(Opportunity.id).order_by(Opportunity.id))
        ids = [row[0] for row in result.fetchall()]

    total = len(ids)
    logger.info(f"共 {total} 条商机，并发 {CONCURRENCY} 条，开始重新分析...")

    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [
        analyze_one(sem, opp_id, idx, total)
        for idx, opp_id in enumerate(ids, start=1)
    ]
    results = await asyncio.gather(*tasks)

    success = sum(results)
    fail = total - success
    logger.info(f"全部完成：成功 {success} 条，失败 {fail} 条")


if __name__ == "__main__":
    asyncio.run(main())
