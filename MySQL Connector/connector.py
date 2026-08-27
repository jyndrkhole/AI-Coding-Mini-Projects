import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

required = ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
missing = [name for name in required if not os.getenv(name)]
if missing:
    raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

conn = mysql.connector.connect(
    host=os.environ["MYSQL_HOST"],
    user=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASSWORD"],
    database=os.environ["MYSQL_DATABASE"],
)
cursor = conn.cursor()

cursor.execute("SELECT USER(), CURRENT_USER(), DATABASE()")
session_user, current_user, database = cursor.fetchone()
print("Connected successfully" if conn.is_connected() else "Failed")
print(f"Session user : {session_user}")
print(f"Current user : {current_user}")
print(f"Database     : {database}")

print("\nGrants:")
cursor.execute("SHOW GRANTS")
for (grant,) in cursor.fetchall():
    print(f"  {grant}")

user_name, host = current_user.split("@", 1)
grantees = [f"'{user_name}'@'{host}'", f"'{user_name}'@'%'"]

print("\nSchema privileges:")
cursor.execute(
    """
    SELECT TABLE_SCHEMA, PRIVILEGE_TYPE, IS_GRANTABLE
    FROM information_schema.SCHEMA_PRIVILEGES
    WHERE GRANTEE IN (%s, %s)
    ORDER BY TABLE_SCHEMA, PRIVILEGE_TYPE
    """,
    grantees,
)
schema_privs = cursor.fetchall()
if schema_privs:
    for schema, privilege, grantable in schema_privs:
        print(f"  {schema}: {privilege} (grantable={grantable})")
else:
    print("  None listed in information_schema.SCHEMA_PRIVILEGES")

print("\nTable privileges:")
cursor.execute(
    """
    SELECT TABLE_SCHEMA, TABLE_NAME, PRIVILEGE_TYPE, IS_GRANTABLE
    FROM information_schema.TABLE_PRIVILEGES
    WHERE GRANTEE IN (%s, %s)
    ORDER BY TABLE_SCHEMA, TABLE_NAME, PRIVILEGE_TYPE
    """,
    grantees,
)
table_privs = cursor.fetchall()
if table_privs:
    for schema, table, privilege, grantable in table_privs:
        print(f"  {schema}.{table}: {privilege} (grantable={grantable})")
else:
    print("  None listed in information_schema.TABLE_PRIVILEGES")

print("\nView access:")
cursor.execute(
    """
    SELECT TABLE_NAME, IS_UPDATABLE, CHECK_OPTION, SECURITY_TYPE, VIEW_DEFINITION
    FROM information_schema.VIEWS
    WHERE TABLE_SCHEMA = DATABASE()
    ORDER BY TABLE_NAME
    """
)
views = cursor.fetchall()
if not views:
    print("  No views found")
else:
    for view_name, is_updatable, check_option, security_type, definition in views:
        print(f"\n  View: {database}.{view_name}")
        print(f"    Updatable    : {is_updatable}")
        print(f"    Check option : {check_option}")
        print(f"    Security     : {security_type}")

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
        if view_privs:
            print("    Privileges:")
            for privilege, grantable in view_privs:
                print(f"      {privilege} (grantable={grantable})")
        else:
            print("    Privileges: none listed")

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
        if col_privs:
            print("    Column privileges:")
            for column, privilege, grantable in col_privs:
                print(f"      {column}: {privilege} (grantable={grantable})")

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
        print("    Columns:")
        if columns:
            for column, column_type, nullable, key, extra in columns:
                extras = [part for part in (key, extra) if part]
                suffix = f" [{', '.join(extras)}]" if extras else ""
                print(f"      {column} {column_type} nullable={nullable}{suffix}")
        else:
            print("      No columns visible")

        if definition:
            print(f"    Definition:\n      {definition}")
        else:
            print("    Definition: not visible (SHOW VIEW privilege required)")

cursor.close()
conn.close()
