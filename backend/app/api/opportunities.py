import os
import tempfile
from datetime import date
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.opportunity import Opportunity
from app.models.user import User
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityResponse,
    OpportunityUpdate,
    OpportunityListResponse,
)
from app.utils.excel import import_excel, export_excel
from app.services.log_service import log_operation

router = APIRouter(prefix="/api/opportunities", tags=["商机管理"])


async def _validate_three_roles(data, db: AsyncSession):
    """Validate that all three roles are assigned and users exist"""
    errors = []
    role_fields = [
        ("division_member_id", "项目经理"),
        ("account_manager_id", "客户经理"),
        ("branch_director_id", "责任支局长"),
    ]
    for field, role_name in role_fields:
        uid = getattr(data, field, None)
        if not uid:
            errors.append(f"缺少{role_name}")
        else:
            result = await db.execute(select(User).where(User.id == uid, User.role == role_name))
            if not result.scalar_one_or_none():
                errors.append(f"{role_name}(ID:{uid})不存在或角色不匹配")
    if errors:
        raise HTTPException(status_code=400, detail="请补充完整的三角色人员: " + "; ".join(errors))


def _apply_role_filter(query, user_role: str, user_id: int):
    """Apply role-based data access filter"""
    if user_role == "项目经理":
        return query.where(Opportunity.division_member_id == user_id)
    elif user_role == "客户经理":
        return query.where(Opportunity.account_manager_id == user_id)
    elif user_role == "责任支局长":
        return query.where(Opportunity.branch_director_id == user_id)
    # Admin sees all
    return query


def _apply_role_filter_to_count(count_query, user_role: str, user_id: int):
    """Apply role-based data access filter to count query"""
    if user_role == "项目经理":
        return count_query.where(Opportunity.division_member_id == user_id)
    elif user_role == "客户经理":
        return count_query.where(Opportunity.account_manager_id == user_id)
    elif user_role == "责任支局长":
        return count_query.where(Opportunity.branch_director_id == user_id)
    return count_query


@router.get("", response_model=OpportunityListResponse)
async def list_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, alias="status"),
    priority: Optional[int] = Query(None, alias="priority"),
    branch_office: Optional[str] = None,
    division_member_id: Optional[int] = None,
    account_manager_id: Optional[int] = None,
    keyword: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取商机列表（按角色过滤）"""
    # Base queries
    base_query = select(Opportunity).options(
        selectinload(Opportunity.division_member),
        selectinload(Opportunity.account_manager),
        selectinload(Opportunity.branch_director),
    )
    base_count = select(func.count(Opportunity.id))

    # Apply role-based filtering
    user_role = current_user.get("role")
    user_id = current_user.get("id")
    base_query = _apply_role_filter(base_query, user_role, user_id)
    base_count = _apply_role_filter_to_count(base_count, user_role, user_id)

    query = base_query
    count_query = base_count

    # Additional filters
    if status:
        query = query.where(Opportunity.opportunity_status == status)
        count_query = count_query.where(Opportunity.opportunity_status == status)
    if priority:
        query = query.where(Opportunity.priority_level == priority)
        count_query = count_query.where(Opportunity.priority_level == priority)
    if branch_office:
        query = query.where(Opportunity.branch_office == branch_office)
        count_query = count_query.where(Opportunity.branch_office == branch_office)
    if division_member_id:
        query = query.where(Opportunity.division_member_id == division_member_id)
        count_query = count_query.where(Opportunity.division_member_id == division_member_id)
    if account_manager_id:
        query = query.where(Opportunity.account_manager_id == account_manager_id)
        count_query = count_query.where(Opportunity.account_manager_id == account_manager_id)
    if keyword:
        keyword_filter = or_(
            Opportunity.opportunity_name.ilike(f"%{keyword}%"),
            Opportunity.customer_name.ilike(f"%{keyword}%"),
        )
        query = query.where(keyword_filter)
        count_query = count_query.where(keyword_filter)

    # Count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Sort
    sort_column = getattr(Opportunity, sort_by, Opportunity.id)
    order_fn = sort_column.desc if sort_order == "desc" else sort_column.asc
    query = query.order_by(order_fn())

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    opportunities = result.scalars().unique().all()

    return OpportunityListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[OpportunityResponse.model_validate(o) for o in opportunities],
    )


@router.get("/import-template", response_class=FileResponse)
async def download_import_template(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """下载导入模板 Excel"""
    from app.utils.excel import EXPORT_COLUMNS
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "导入模板"

    # Style
    header_font = Font(name="微软雅黑", bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="0052CC", end_color="0052CC", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="DFE1E6"),
        right=Side(style="thin", color="DFE1E6"),
        top=Side(style="thin", color="DFE1E6"),
        bottom=Side(style="thin", color="DFE1E6"),
    )

    # Template columns (based on COLUMN_MAP in excel.py)
    template_columns = [
        ("序号", 8),
        ("商机名称", 30),
        ("客户名称", 20),
        ("商机情况", 14),
        ("商机预测金额(万元)", 14),
        ("产品类别", 14),
        ("商机产品", 20),
        ("支局", 12),
        ("企业和政府", 10),
        ("项目经理", 12),
        ("客户经理", 12),
        ("责任支局长", 12),
        ("预计签约日期", 14),
        ("商机创建时间", 14),
        ("最新推进时间", 14),
        ("大单规模", 12),
        ("分管领导", 12),
        ("商机详情", 40),
        ("备注", 30),
        ("是否清单级客户", 12),
        ("是否招标", 10),
    ]

    for col_idx, (col_name, col_width) in enumerate(template_columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(col_idx)].width = col_width

    # Add a sample row with notes
    ws.cell(row=3, column=1, value="Fill instructions:").font = Font(name="Arial", bold=True, size=10, color="FF5E6C84")
    notes = [
        "1. Opportunity name and customer name are required",
        "2. For role members: fill in the user's real name as it exists in the system",
        "3. Date format: 2024-01-01 or 2024/01/01",
        "4. Yes/No fields: use Yes/No or 1/0",
    ]
    for i, note in enumerate(notes):
        ws.cell(row=4 + i, column=1, value=note).font = Font(name="Arial", size=10, color="FF5E6C84")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(tmp.name)
    wb.close()

    return FileResponse(
        tmp.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="import_template.xlsx",
    )


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_opportunities(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """导入 Excel 商机数据"""
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        await log_operation("import", {"filename": file.filename}, resource_type="opportunity", status="fail", error_message="不支持的文件格式", db=db)
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 文件")

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await import_excel(tmp_path, db)
        await log_operation(
            "import",
            {"filename": file.filename, "total": result["total"], "imported": result["imported"], "errors": result["errors"][:10]},
            resource_type="opportunity",
            status="success" if result["errors"] == [] else "partial",
            error_message=f"{len(result['errors'])}行错误" if result["errors"] else None,
            db=db,
        )
    except Exception as e:
        await log_operation("import", {"filename": file.filename}, resource_type="opportunity", status="fail", error_message=str(e), db=db)
        raise
    finally:
        os.unlink(tmp_path)

    return {
        "message": f"导入完成：共 {result['total']} 条，成功 {result['imported']} 条",
        "total": result["total"],
        "imported": result["imported"],
        "errors": result["errors"],
    }


@router.get("/export", response_class=FileResponse)
async def export_opportunities(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """导出商机数据到 Excel"""
    # Build query with role filtering
    base_query = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.division_member),
            selectinload(Opportunity.account_manager),
            selectinload(Opportunity.branch_director),
        )
    )
    user_role = current_user.get("role")
    user_id = current_user.get("id")
    base_query = _apply_role_filter(base_query, user_role, user_id)
    base_query = base_query.order_by(Opportunity.id)

    result = await db.execute(base_query)
    opportunities = result.scalars().unique().all()

    tmp_path = tempfile.mktemp(suffix=".xlsx")
    await export_excel(opportunities, tmp_path)

    background_tasks.add_task(os.unlink, tmp_path)

    return FileResponse(
        path=tmp_path,
        filename="商机列表.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取商机详情（按角色过滤）"""
    query = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.division_member),
            selectinload(Opportunity.account_manager),
            selectinload(Opportunity.branch_director),
        )
        .where(Opportunity.id == opportunity_id)
    )

    # Apply role-based filtering
    user_role = current_user.get("role")
    user_id = current_user.get("id")
    query = _apply_role_filter(query, user_role, user_id)

    result = await db.execute(query)
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在或无权访问")
    return OpportunityResponse.model_validate(opp)


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    data: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建商机（需补充完整的三角色人员）"""
    await _validate_three_roles(data, db)
    opp = Opportunity(**data.model_dump())
    db.add(opp)
    await db.flush()
    # 重新查询以加载关联关系
    result = await db.execute(
        select(Opportunity)
        .options(
            selectinload(Opportunity.division_member),
            selectinload(Opportunity.account_manager),
            selectinload(Opportunity.branch_director),
        )
        .where(Opportunity.id == opp.id)
    )
    opp = result.scalar_one()
    return OpportunityResponse.model_validate(opp)


@router.put("/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: int,
    data: OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """更新商机（需补充完整的三角色人员）"""
    result = await db.execute(
        select(Opportunity)
        .options(
            selectinload(Opportunity.division_member),
            selectinload(Opportunity.account_manager),
            selectinload(Opportunity.branch_director),
        )
        .where(Opportunity.id == opportunity_id)
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    # Validate three roles if any role field is being updated
    if data.division_member_id is not None or data.account_manager_id is not None or data.branch_director_id is not None:
        # Merge existing with new data for validation
        from pydantic import BaseModel
        class _MergeData(BaseModel):
            division_member_id: Optional[int] = None
            account_manager_id: Optional[int] = None
            branch_director_id: Optional[int] = None
        merge = _MergeData(
            division_member_id=data.division_member_id if data.division_member_id is not None else opp.division_member_id,
            account_manager_id=data.account_manager_id if data.account_manager_id is not None else opp.account_manager_id,
            branch_director_id=data.branch_director_id if data.branch_director_id is not None else opp.branch_director_id,
        )
        await _validate_three_roles(merge, db)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(opp, field, value)

    await db.flush()
    await db.refresh(opp)
    return OpportunityResponse.model_validate(opp)


@router.post("/{opportunity_id}/analyze", status_code=status.HTTP_200_OK)
async def analyze_opportunity(
    opportunity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """手动触发 AI 分析"""
    from app.services.ai_engine import analyze_opportunity_full
    result = await analyze_opportunity_full(opportunity_id, db)
    if not result:
        raise HTTPException(status_code=400, detail="AI分析失败，请检查 DeepSeek 配置")
    return {"message": "AI 分析完成", "risk_level": result.get("risk_level") or result.get("ai_risk_level"), "priority_suggestion": result.get("priority_suggestion")}


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(
    opportunity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """删除商机"""
    result = await db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")
    await db.delete(opp)
    await db.flush()
