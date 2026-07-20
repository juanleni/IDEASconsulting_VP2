from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine


async def run() -> None:
    print(f"[INFO] DATABASE_URL={settings.database_url}")
    try:
        async with engine.connect() as connection:
            database = await connection.scalar(text("SELECT current_database()"))
            print(f"[OK] Conexion PostgreSQL: {database}")

            vector_available = await connection.scalar(
                text("SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')")
            )
            if vector_available:
                print("[OK] Extension pgvector disponible para instalar.")
            else:
                print("[ERROR] Extension pgvector no disponible en este PostgreSQL.")

            vector_installed = await connection.scalar(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            print(f"[INFO] Extension vector instalada: {bool(vector_installed)}")
    except Exception as exc:
        print(f"[ERROR] No se pudo conectar: {type(exc).__name__}: {exc}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
