#!/usr/bin/env python3
"""
导入xlsx文件中的走访数据到商机进度时间线
"""
import asyncio
import openpyxl
from datetime import date, datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.opportunity import Opportunity
from app.models.opportunity_progress import OpportunityProgress


async def import_progress_data():
    """导入走访数据"""
    # 读取xlsx文件
    wb = openpyxl.load_workbook('/app/data.xlsx', read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()

    async with async_session() as db:
        imported = 0
        skipped = 0
        errors = []

        for i, row in enumerate(rows, start=2):
            try:
                # 获取字段值
                opportunity_name = row[7] if len(row) > 7 else None  # H列：商机名称
                n_val = row[13] if len(row) > 13 else None  # N列：最新推进时间
                u_val = row[20] if len(row) > 20 else None  # U列：走访数据

                if not opportunity_name or not u_val or not str(u_val).strip():
                    skipped += 1
                    continue

                # 查找商机
                result = await db.execute(
                    select(Opportunity).where(Opportunity.opportunity_name == str(opportunity_name).strip())
                )
                opp = result.scalar_one_or_none()

                if not opp:
                    errors.append(f"行{i}: 商机 '{opportunity_name}' 不存在")
                    skipped += 1
                    continue

                # 解析最新推进时间
                progress_date = date.today()
                if n_val:
                    if isinstance(n_val, datetime):
                        progress_date = n_val.date()
                    elif isinstance(n_val, date):
                        progress_date = n_val
                    elif isinstance(n_val, str):
                        try:
                            # 尝试解析字符串日期
                            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
                                try:
                                    progress_date = datetime.strptime(n_val.strip(), fmt).date()
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass

                # 创建进度记录
                prog = OpportunityProgress(
                    opportunity_id=opp.id,
                    updater_id=1,  # 使用管理员用户
                    updater_role="客户经理",
                    progress_content=str(u_val).strip(),
                    progress_date=progress_date,
                    week_number=int(progress_date.strftime("%Y%U")),
                )
                db.add(prog)

                # 更新商机的last_push_date和weekly_progress
                opp.last_push_date = progress_date
                opp.no_push_days = 0
                opp.no_push_flag = 0

                # 更新weekly_progress
                if opp.weekly_progress:
                    opp.weekly_progress = f"[{progress_date}] {u_val}\n{opp.weekly_progress}"
                else:
                    opp.weekly_progress = f"[{progress_date}] {u_val}"

                imported += 1
                print(f"行{i}: 导入成功 - 商机: {opportunity_name}, 日期: {progress_date}, 内容: {u_val[:30]}...")

            except Exception as e:
                errors.append(f"行{i}: {str(e)}")

        # 提交事务
        await db.commit()

        print(f"\n导入完成:")
        print(f"  成功: {imported}")
        print(f"  跳过: {skipped}")
        print(f"  错误: {len(errors)}")
        if errors:
            print("\n错误详情:")
            for err in errors[:10]:
                print(f"  {err}")


if __name__ == "__main__":
    asyncio.run(import_progress_data())
