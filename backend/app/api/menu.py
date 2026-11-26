"""菜单与权限点字典接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_perm
from app.db.session import get_db
from app.models import Menu, Permission
from app.schemas import ApiResponse, MenuOut, PermissionOut
from app.services import permission as perm_svc

router = APIRouter(tags=["菜单与权限"])


class MenuIn(BaseModel):
    parent_id: int = 0
    title: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    path: str = ""
    component: str = ""
    icon: str | None = None
    type: str = "menu"
    perm_code: str | None = None
    sort: int = 0
    visible: bool = True
    keep_alive: bool = False
    is_ext: bool = False
    status: int = 1


# --------------------------------------------------------------------------- #
# 权限点
# --------------------------------------------------------------------------- #
@router.get("/permissions", response_model=ApiResponse[list[PermissionOut]], summary="权限点字典")
async def list_permissions(db: AsyncSession = Depends(get_db), _: CurrentUser = None,
                           __=Depends(require_perm("system:role:list", "system:role:grant"))):
    rows = list((await db.execute(
        select(Permission).order_by(Permission.module, Permission.sort)
    )).scalars())
    return ApiResponse(data=[PermissionOut.model_validate(r) for r in rows])


# --------------------------------------------------------------------------- #
# 菜单
# --------------------------------------------------------------------------- #
@router.get("/menus/tree", response_model=ApiResponse[list[MenuOut]], summary="完整菜单树（管理端）")
async def menu_tree(db: AsyncSession = Depends(get_db), _: CurrentUser = None,
                    __=Depends(require_perm("system:menu:list", "system:role:grant"))):
    rows = list((await db.execute(select(Menu).order_by(Menu.sort, Menu.id))).scalars())
    tree = perm_svc.build_menu_tree(rows)
    # 管理端需要展示按钮节点，单独拼一层
    def attach(nodes: list[dict], parent: int):
        for node in nodes:
            node["children"] = node["children"] + [
                {
                    "id": m.id, "parent_id": m.parent_id, "title": m.title, "name": m.name,
                    "path": m.path, "component": m.component, "icon": m.icon, "type": m.type,
                    "perm_code": m.perm_code, "sort": m.sort, "visible": m.visible,
                    "keep_alive": m.keep_alive, "is_ext": m.is_ext, "children": [],
                }
                for m in sorted(rows, key=lambda x: x.sort)
                if m.parent_id == parent and m.type == "button"
            ]
            attach(node["children"], node["id"])
    attach(tree, 0)
    return ApiResponse(data=tree)


@router.get("/menus", response_model=ApiResponse[list[dict]], summary="菜单扁平列表")
async def menu_flat(
    current: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_perm("system:menu:list", "system:role:grant")),
):
    rows = list((await db.execute(select(Menu).order_by(Menu.sort, Menu.id))).scalars())
    return ApiResponse(data=[{
        "id": m.id, "parent_id": m.parent_id, "title": m.title, "name": m.name,
        "path": m.path, "component": m.component, "icon": m.icon, "type": m.type,
        "perm_code": m.perm_code, "sort": m.sort, "visible": m.visible,
        "keep_alive": m.keep_alive, "is_ext": m.is_ext, "status": m.status,
    } for m in rows])


@router.post("/menus", response_model=ApiResponse[dict], summary="新建菜单",
             dependencies=[Depends(require_perm("system:menu:create"))])
async def create_menu(body: MenuIn, db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(Menu).where(Menu.name == body.name))).scalar_one_or_none():
        raise HTTPException(400, "路由 name 已存在")
    if body.type not in ("dir", "menu", "button"):
        raise HTTPException(400, "菜单类型仅支持 dir / menu / button")
    menu = Menu(**body.model_dump())
    db.add(menu)
    await db.commit()
    await perm_svc.invalidate_tenant(0)
    return ApiResponse(data={"id": menu.id}, msg="创建成功")


@router.put("/menus/{menu_id}", response_model=ApiResponse[None], summary="编辑菜单",
            dependencies=[Depends(require_perm("system:menu:update"))])
async def update_menu(menu_id: int, body: MenuIn, db: AsyncSession = Depends(get_db)):
    menu = (await db.execute(select(Menu).where(Menu.id == menu_id))).scalar_one_or_none()
    if menu is None:
        raise HTTPException(404, "菜单不存在")
    for k, v in body.model_dump().items():
        setattr(menu, k, v)
    await db.commit()
    await perm_svc.invalidate_tenant(0)
    return ApiResponse(msg="更新成功")


@router.delete("/menus/{menu_id}", response_model=ApiResponse[None], summary="删除菜单",
               dependencies=[Depends(require_perm("system:menu:delete"))])
async def delete_menu(menu_id: int, db: AsyncSession = Depends(get_db)):
    menu = (await db.execute(select(Menu).where(Menu.id == menu_id))).scalar_one_or_none()
    if menu is None:
        raise HTTPException(404, "菜单不存在")
    child = (await db.execute(select(Menu).where(Menu.parent_id == menu_id))).scalars().first()
    if child:
        raise HTTPException(400, "请先删除子节点")
    await db.delete(menu)
    await db.commit()
    await perm_svc.invalidate_tenant(0)
    return ApiResponse(msg="删除成功")
