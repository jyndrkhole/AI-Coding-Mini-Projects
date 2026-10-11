from __future__ import annotations

import re
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


@dataclass
class QueryResult:
    sql: str
    columns: list[str]
    rows: list[tuple]
    truncated: bool


_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|"
    r"GRANT|REVOKE|LOAD|CALL|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b",
    re.IGNORECASE,
)


def quote_ident(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def connect(
    host: str,
    user: str,
    password: str,
    database: str,
    *,
    use_ssl: bool = True,
    ssl_ca: str | None = None,
) -> MySQLConnection:
    options: dict = {
        "host": host,
        "user": user,
        "password": password,
        "database": database,
        "connection_timeout": 15,
        "ssl_disabled": not use_ssl,
    }
    if use_ssl and ssl_ca:
        options["ssl_ca"] = ssl_ca
        options["ssl_verify_cert"] = True
    return mysql.connector.connect(**options)


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
    *,
    use_ssl: bool = True,
    ssl_ca: str | None = None,
) -> InspectionResult:
    conn = connect(
        host,
        user,
        password,
        database,
        use_ssl=use_ssl,
        ssl_ca=ssl_ca,
    )
    try:
        return inspect_connection(conn)
    finally:
        conn.close()


def _rows_as_records(columns: list[str], rows: list[tuple]) -> list[dict]:
    records = []
    for row in rows:
        record = {}
        for column, value in zip(columns, row):
            if isinstance(value, (bytes, bytearray)):
                record[column] = value.decode("utf-8", "replace")
            else:
                record[column] = value
        records.append(record)
    return records


def preview_view(
    host: str,
    user: str,
    password: str,
    database: str,
    view_name: str,
    *,
    limit: int = 100,
    use_ssl: bool = True,
    ssl_ca: str | None = None,
) -> QueryResult:
    limit = max(1, min(int(limit), 1000))
    sql = (
        f"SELECT * FROM {quote_ident(database)}.{quote_ident(view_name)} "
        f"LIMIT {limit}"
    )
    return run_select(
        host,
        user,
        password,
        database,
        sql,
        allowed_view=view_name,
        use_ssl=use_ssl,
        ssl_ca=ssl_ca,
        max_rows=limit,
    )


def run_select(
    host: str,
    user: str,
    password: str,
    database: str,
    sql: str,
    *,
    allowed_view: str,
    use_ssl: bool = True,
    ssl_ca: str | None = None,
    max_rows: int = 1000,
) -> QueryResult:
    statement = sql.strip().rstrip(";")
    if not statement:
        raise ValueError("Enter a SELECT statement")
    if ";" in statement:
        raise ValueError("Only one SQL statement is allowed")
    if not re.match(r"^SELECT\b", statement, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed")
    if _FORBIDDEN_SQL.search(statement):
        raise ValueError("That statement is not allowed")
    if allowed_view.lower() not in statement.lower():
        raise ValueError("The query must reference this view")

    max_rows = max(1, min(int(max_rows), 1000))
    conn = connect(
        host,
        user,
        password,
        database,
        use_ssl=use_ssl,
        ssl_ca=ssl_ca,
    )
    cursor = conn.cursor()
    try:
        cursor.execute(statement)
        columns = [item[0] for item in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        if truncated:
            rows = rows[:max_rows]
        return QueryResult(sql=statement, columns=columns, rows=rows, truncated=truncated)
    finally:
        cursor.close()
        conn.close()


def query_records(result: QueryResult) -> list[dict]:
    return _rows_as_records(result.columns, result.rows)


POLICY_COLUMN_ALIASES = (
    "policynumber",
    "policy_number",
    "policy_no",
    "policy number",
)


def detect_policy_column(columns: list[str]) -> str | None:
    lowered = {name.lower(): name for name in columns}
    for alias in POLICY_COLUMN_ALIASES:
        if alias in lowered:
            return lowered[alias]
    for name in columns:
        compact = name.lower().replace("_", "").replace(" ", "")
        if "policy" in compact and "number" in compact:
            return name
    return None


def classify_case_views(
    views: list[ViewInfo],
    *,
    summary_name: str | None = None,
    details_name: str | None = None,
) -> tuple[ViewInfo | None, ViewInfo | None]:
    by_name = {view.name.lower(): view for view in views}
    summary = by_name.get((summary_name or "").lower()) if summary_name else None
    details = by_name.get((details_name or "").lower()) if details_name else None
    if summary is None:
        summary = next((view for view in views if "summar" in view.name.lower()), None)
    if details is None:
        details = next((view for view in views if "detail" in view.name.lower()), None)
    if summary is None and views:
        summary = views[0]
    if details is None:
        details = summary
    return summary, details


def execute_select(
    host: str,
    user: str,
    password: str,
    database: str,
    sql: str,
    *,
    allowed_view: str,
    params: tuple = (),
    use_ssl: bool = True,
    ssl_ca: str | None = None,
    max_rows: int = 5000,
) -> QueryResult:
    statement = sql.strip().rstrip(";")
    if not statement:
        raise ValueError("Enter a SELECT statement")
    if ";" in statement:
        raise ValueError("Only one SQL statement is allowed")
    if not re.match(r"^SELECT\b", statement, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed")
    if _FORBIDDEN_SQL.search(statement):
        raise ValueError("That statement is not allowed")
    if allowed_view.lower() not in statement.lower():
        raise ValueError("The query must reference this view")

    max_rows = max(1, min(int(max_rows), 5000))
    conn = connect(
        host,
        user,
        password,
        database,
        use_ssl=use_ssl,
        ssl_ca=ssl_ca,
    )
    cursor = conn.cursor()
    try:
        cursor.execute(statement, params)
        columns = [item[0] for item in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        if truncated:
            rows = rows[:max_rows]
        return QueryResult(sql=statement, columns=columns, rows=rows, truncated=truncated)
    finally:
        cursor.close()
        conn.close()


def count_view_rows(
    host: str,
    user: str,
    password: str,
    database: str,
    view_name: str,
    *,
    column: str | None = None,
    values: list | None = None,
    use_ssl: bool = True,
    ssl_ca: str | None = None,
) -> int:
    if values and column:
        placeholders = ", ".join(["%s"] * len(values))
        sql = (
            f"SELECT COUNT(*) FROM {quote_ident(database)}.{quote_ident(view_name)} "
            f"WHERE {quote_ident(column)} IN ({placeholders})"
        )
        params = tuple(values)
    else:
        sql = f"SELECT COUNT(*) FROM {quote_ident(database)}.{quote_ident(view_name)}"
        params = ()
    result = execute_select(
        host,
        user,
        password,
        database,
        sql,
        allowed_view=view_name,
        params=params,
        use_ssl=use_ssl,
        ssl_ca=ssl_ca,
        max_rows=1,
    )
    if not result.rows:
        return 0
    return int(result.rows[0][0])


def fetch_view_ordered(
    host: str,
    user: str,
    password: str,
    database: str,
    view_name: str,
    *,
    order_column: str | None = None,
    descending: bool = True,
    limit: int = 2000,
    use_ssl: bool = True,
    ssl_ca: str | None = None,
) -> QueryResult:
    sql = f"SELECT * FROM {quote_ident(database)}.{quote_ident(view_name)}"
    if order_column:
        direction = "DESC" if descending else "ASC"
        sql += f" ORDER BY {quote_ident(order_column)} {direction}"
    sql += f" LIMIT {max(1, min(int(limit), 5000))}"
    return execute_select(
        host,
        user,
        password,
        database,
        sql,
        allowed_view=view_name,
        use_ssl=use_ssl,
        ssl_ca=ssl_ca,
        max_rows=limit,
    )


def fetch_rows_by_values(
    host: str,
    user: str,
    password: str,
    database: str,
    view_name: str,
    *,
    column: str,
    values: list,
    descending: bool = True,
    use_ssl: bool = True,
    ssl_ca: str | None = None,
) -> QueryResult:
    if not values:
        return QueryResult(sql="", columns=[], rows=[], truncated=False)
    placeholders = ", ".join(["%s"] * len(values))
    direction = "DESC" if descending else "ASC"
    sql = (
        f"SELECT * FROM {quote_ident(database)}.{quote_ident(view_name)} "
        f"WHERE {quote_ident(column)} IN ({placeholders}) "
        f"ORDER BY {quote_ident(column)} {direction}"
    )
    return execute_select(
        host,
        user,
        password,
        database,
        sql,
        allowed_view=view_name,
        params=tuple(values),
        use_ssl=use_ssl,
        ssl_ca=ssl_ca,
        max_rows=5000,
    )
