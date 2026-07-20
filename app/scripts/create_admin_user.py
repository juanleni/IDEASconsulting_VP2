from __future__ import annotations

import argparse
import asyncio
from getpass import getpass

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.services.auth_service import hash_password


async def run(empresa_nombre: str, email: str, password: str, rol: str) -> None:
    async with AsyncSessionLocal() as session:
        empresa_result = await session.execute(select(Empresa).where(Empresa.razon_social == empresa_nombre))
        empresa = empresa_result.scalar_one_or_none()
        if not empresa:
            empresa = Empresa(razon_social=empresa_nombre, is_active=True)
            session.add(empresa)
            await session.flush()

        user_result = await session.execute(select(Usuario).where(Usuario.email == email))
        user = user_result.scalar_one_or_none()
        if user:
            user.empresa_id = int(empresa.id)
            user.password_hash = hash_password(password)
            user.rol = rol
            action = "actualizado"
        else:
            user = Usuario(
                empresa_id=int(empresa.id),
                email=email,
                password_hash=hash_password(password),
                rol=rol,
            )
            session.add(user)
            action = "creado"

        await session.commit()
        print(f"[OK] Usuario {action}: {email} empresa_id={empresa.id} rol={rol}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crea o actualiza un usuario admin para IDEAS SaaS.")
    parser.add_argument("--empresa", default="Empresa Demo", help="Razon social del tenant.")
    parser.add_argument("--email", required=True, help="Email de login.")
    parser.add_argument("--password", default="", help="Password inicial. Si se omite, se solicita por consola.")
    parser.add_argument("--rol", default="ideas_admin", help="Rol del usuario.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    password = args.password or getpass("Password: ")
    if not password:
        raise SystemExit("Password requerido.")
    asyncio.run(run(args.empresa, args.email, password, args.rol))
