from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: type[ModelT], session: AsyncSession, empresa_id: int) -> None:
        self.model = model
        self.session = session
        self.empresa_id = int(empresa_id)

    def _tenant_stmt(self) -> Select[tuple[ModelT]]:
        return select(self.model).where(getattr(self.model, "empresa_id") == self.empresa_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        stmt = self._tenant_stmt().limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, object_id: int) -> ModelT | None:
        stmt = self._tenant_stmt().where(getattr(self.model, "id") == int(object_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> ModelT:
        payload = dict(data)
        payload["empresa_id"] = self.empresa_id
        obj = self.model(**payload)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update(self, object_id: int, data: dict) -> ModelT | None:
        obj = await self.get(object_id)
        if not obj:
            return None
        for key, value in data.items():
            if key in {"id", "empresa_id"}:
                continue
            setattr(obj, key, value)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete(self, object_id: int) -> bool:
        obj = await self.get(object_id)
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.commit()
        return True

