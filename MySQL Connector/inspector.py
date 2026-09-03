from __future__ import annotations

from dataclasses import dataclass, field

import mysql.connector
from mysql.connector import MySQLConnection


@dataclass
class ViewInfo:
    name: str
    updatable: str
    check_option: str | None
    security_type: str | None
    privileges: list[tuple[str, str]]
    column_privileges: list[tuple[str, str, str]]
    columns: list[tuple[str, str, str, str, str]]
    definition: str | None


@dataclass
class InspectionResult:
    connected: bool
    session_user: str
    current_user: str
    database: str
    grants: list[str] = field(default_factory=list)
    schema_privileges: list[tuple[str, str, str]] = field(default_factory=list)
    table_privileges: list[tuple[str, str, str, str]] = field(default_factory=list)
    views: list[ViewInfo] = field(default_factory=list)


def connect(
    host: str,
    user: str,
    password: str,
    database: str,
) -> MySQLConnection:
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
    )


def _grantees(current_user: str) -> list[str]:
    user_name, host = current_user.split("@", 1)
    return [f"'{user_name}'@'{host}'", f"'{user_name}'@'%'"]


def inspect_connection(conn: MySQLConnection) -> InspectionResult:
    cursor = conn.cursor()

    cursor.execute("SELECT USER(), CURRENT_USER(), DATABASE()")
    session_user, current_user, database = cursor.fetchone()
    grantees = _grantees(current_user)

    cursor.execute("SHOW GRANTS")
    grants = [row[0] for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT TABLE_SCHEMA, PRIVILEGE_TYPE, IS_GRANTABLE
        FROM information_schema.SCHEMA_PRIVILEGES
        WHERE GRANTEE IN (%s, %s)
        ORDER BY TABLE_SCHEMA, PRIVILEGE_TYPE
        """,
        grantees,
    )
    schema_privileges = cursor.fetchall()

    cursor.execute(
        """
        SELECT TABLE_SCHEMA, TABLE_NAME, PRIVILEGE_TYPE, IS_GRANTABLE
        FROM information_schema.TABLE_PRIVILEGES
        WHERE GRANTEE IN (%s, %s)
        ORDER BY TABLE_SCHEMA, TABLE_NAME, PRIVILEGE_TYPE
        """,
        grantees,
    )
    table_privileges = cursor.fetchall()

    cursor.execute(
        """
        SELECT TABLE_NAME, IS_UPDATABLE, CHECK_OPTION, SECURITY_TYPE, VIEW_DEFINITION
        FROM information_schema.VIEWS
        WHERE TABLE_SCHEMA = DATABASE()
        ORDER BY TABLE_NAME
        """
    )
    views: list[ViewInfo] = []
    for view_name, is_updatable, check_option, security_type, definition in cursor.fetchall():
        cursor.execute(
            """
            SELECT PRIVILEGE_TYPE, IS_GRANTABLE
            FROM information_schema.TABLE_PRIVILEGES
            WHERE GRANTEE IN (%s, %s)
              AND TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            ORDER BY PRIVILEGE_TYPE
            """,
            (*grantees, view_name),
        )
        view_privs = cursor.fetchall()

        cursor.execute(
            """
            SELECT COLUMN_NAME, PRIVILEGE_TYPE, IS_GRANTABLE
            FROM information_schema.COLUMN_PRIVILEGES
            WHERE GRANTEE IN (%s, %s)
              AND TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            ORDER BY COLUMN_NAME, PRIVILEGE_TYPE
            """,
            (*grantees, view_name),
        )
        col_privs = cursor.fetchall()

        cursor.execute(
            """
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, EXTRA
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (view_name,),
        )
        columns = cursor.fetchall()

        views.append(
            ViewInfo(
                name=view_name,
                updatable=is_updatable,
                check_option=check_option,
                security_type=security_type,
                privileges=view_privs,
                column_privileges=col_privs,
                columns=columns,
                definition=definition,
            )
        )

    cursor.close()

    return InspectionResult(
        connected=conn.is_connected(),
        session_user=session_user,
        current_user=current_user,
        database=database,
        grants=grants,
        schema_privileges=schema_privileges,
        table_privileges=table_privileges,
        views=views,
    )


def run_inspection(
    host: str,
    user: str,
    password: str,
    database: str,
) -> InspectionResult:
    conn = connect(host, user, password, database)
    try:
        return inspect_connection(conn)
    finally:
        conn.close()
