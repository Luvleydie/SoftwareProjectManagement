"""Copy legacy users/artifacts into configured MySQL, leaving SQLite untouched.

Duplicate rows are skipped only when their complete content matches. Conflicts
abort the transaction. Sessions are intentionally omitted: users sign in again.
"""
import argparse
import sys
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.database import engine  # noqa: E402
from app.main import Artifact, Base, UserRow  # noqa: E402


def migrate(source: Path) -> dict[str, int]:
    if not source.is_file():
        raise ValueError('No existe la base SQLite de origen.')
    if engine.dialect.name not in {'mysql', 'mariadb'}:
        raise ValueError('La base de destino debe ser MySQL/MariaDB.')
    # URI mode=ro prevents both creating and changing the original SQLite file.
    sqlite = create_engine(f'sqlite:///file:{source.resolve().as_posix()}?mode=ro&uri=true')
    source_metadata = MetaData()
    source_users = Table('users', source_metadata, autoload_with=sqlite)
    source_artifacts = Table('artifacts', source_metadata, autoload_with=sqlite)
    Base.metadata.create_all(engine)
    counts = {'users_copied': 0, 'users_skipped': 0, 'artifacts_copied': 0, 'artifacts_skipped': 0}
    try:
        with sqlite.connect() as original, Session(engine) as destination, destination.begin():
            for table, model, label in (
                (source_users, UserRow, 'users'), (source_artifacts, Artifact, 'artifacts'),
            ):
                for row in original.execute(select(table)).mappings():
                    values = dict(row)
                    # Reflected SQLite JSON is decoded by SQLAlchemy's JSON type.
                    existing = destination.get(model, values['id'])
                    if existing:
                        if any(getattr(existing, key) != value for key, value in values.items()):
                            raise ValueError(f'Conflicto en {label}: se canceló la copia sin reemplazar datos.')
                        counts[f'{label}_skipped'] += 1
                        continue
                    if model is UserRow and destination.scalar(select(UserRow.id).where(UserRow.email == values['email'])):
                        raise ValueError('Conflicto de correo en users: se canceló la copia sin reemplazar datos.')
                    if model is Artifact and not destination.get(UserRow, values['owner_id']):
                        raise ValueError('Artefacto sin propietario: se canceló la copia.')
                    destination.add(model(**values))
                    destination.flush()
                    counts[f'{label}_copied'] += 1
    finally:
        sqlite.dispose()
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=BACKEND / 'juridia.db')
    args = parser.parse_args()
    try:
        print(migrate(args.source))
        print('SQLite conservado. Las sesiones anteriores requieren iniciar sesión de nuevo.')
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except SQLAlchemyError:
        print('Falló la migración. No se confirmó la copia; revisa la conexión y el esquema de las bases.', file=sys.stderr)
        sys.exit(1)
