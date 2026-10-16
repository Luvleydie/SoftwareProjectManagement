"""Provision the local XAMPP database without replacing existing users or data.

Run from backend: .venv/Scripts/python.exe scripts/init_mysql.py
If root has a password, set JURIDIA_MYSQL_ADMIN_PASSWORD in the environment.
Credentials are saved to the ignored backend/.env and never printed.
"""
import os
import re
import secrets
import sys
from pathlib import Path

import pymysql
from dotenv import dotenv_values, set_key


BACKEND = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND / '.env'


def main() -> int:
    settings = {**dotenv_values(ENV_FILE), **os.environ}
    host = settings.get('JURIDIA_MYSQL_HOST', '127.0.0.1')
    port = int(settings.get('JURIDIA_MYSQL_PORT', '3306'))
    database = settings.get('JURIDIA_MYSQL_DATABASE', 'juridia')
    username = settings.get('JURIDIA_MYSQL_USER', 'juridia_app')
    if host not in {'127.0.0.1', 'localhost'} or port != 3306:
        raise ValueError('Este script solo prepara XAMPP local en el puerto 3306.')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', database):
        raise ValueError('Nombre de base no válido.')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}', username) or username == 'root':
        raise ValueError('Usa un usuario dedicado con nombre válido, distinto de root.')

    password = settings.get('JURIDIA_MYSQL_PASSWORD')
    with pymysql.connect(
        host=host, port=port, user=os.getenv('JURIDIA_MYSQL_ADMIN_USER', 'root'),
        password=os.getenv('JURIDIA_MYSQL_ADMIN_PASSWORD', ''),
        charset='utf8mb4', connect_timeout=5, autocommit=True,
    ) as admin:
        with admin.cursor() as cursor:
            cursor.execute('SELECT Host FROM mysql.user WHERE User = %s', (username,))
            existing_hosts = {row[0] for row in cursor.fetchall()}
            if existing_hosts:
                # Never change credentials or permissions of an existing account.
                if not password:
                    raise ValueError('El usuario ya existe; configura su contraseña en backend/.env. No se modificó.')
                with pymysql.connect(
                    host=host, port=port, user=username, password=password,
                    database=database, charset='utf8mb4', connect_timeout=5,
                ) as configured:
                    with configured.cursor() as check:
                        check.execute('SELECT 1')
                print('La conexión dedicada existente funciona. No se modificaron cuentas ni datos.')
                return 0

            cursor.execute(
                f'CREATE DATABASE IF NOT EXISTS `{database}` '
                'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
            )
            password = password or secrets.token_urlsafe(36)
            for account_host in ('127.0.0.1', 'localhost'):
                cursor.execute('CREATE USER %s@%s IDENTIFIED BY %s', (username, account_host, password))
                cursor.execute(
                    f'GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX ON `{database}`.* TO %s@%s',
                    (username, account_host),
                )

    # Database-specific privileges; no global privileges and no DROP permission.
    for key, value in {
        'JURIDIA_MYSQL_HOST': host,
        'JURIDIA_MYSQL_PORT': str(port),
        'JURIDIA_MYSQL_DATABASE': database,
        'JURIDIA_MYSQL_USER': username,
        'JURIDIA_MYSQL_PASSWORD': password,
    }.items():
        set_key(ENV_FILE, key, value)
    with pymysql.connect(
        host=host, port=port, user=username, password=password,
        database=database, charset='utf8mb4', connect_timeout=5,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    print(f'Base {database} y usuario dedicado preparados en {host}:{port}. Credenciales guardadas en backend/.env.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except pymysql.MySQLError as error:
        # Driver messages may contain host/user names; avoid echoing connection data.
        print(f'No fue posible preparar MySQL (código {error.args[0]}). Comprueba XAMPP y el acceso administrador.', file=sys.stderr)
        sys.exit(1)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
