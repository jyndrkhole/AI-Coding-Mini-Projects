import os

from dotenv import load_dotenv

from inspector import run_inspection

load_dotenv()

required = ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
missing = [name for name in required if not os.getenv(name)]
if missing:
    raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

result = run_inspection(
    host=os.environ["MYSQL_HOST"],
    user=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASSWORD"],
    database=os.environ["MYSQL_DATABASE"],
)

print("Connected successfully" if result.connected else "Failed")
print(f"Session user : {result.session_user}")
print(f"Current user : {result.current_user}")
print(f"Database     : {result.database}")

print("\nGrants:")
for grant in result.grants:
    print(f"  {grant}")

print("\nSchema privileges:")
if result.schema_privileges:
    for schema, privilege, grantable in result.schema_privileges:
        print(f"  {schema}: {privilege} (grantable={grantable})")
else:
    print("  None listed in information_schema.SCHEMA_PRIVILEGES")

print("\nTable privileges:")
if result.table_privileges:
    for schema, table, privilege, grantable in result.table_privileges:
        print(f"  {schema}.{table}: {privilege} (grantable={grantable})")
else:
    print("  None listed in information_schema.TABLE_PRIVILEGES")

print("\nView access:")
if not result.views:
    print("  No views found")
else:
    for view in result.views:
        print(f"\n  View: {result.database}.{view.name}")
        print(f"    Updatable    : {view.updatable}")
        print(f"    Check option : {view.check_option}")
        print(f"    Security     : {view.security_type}")

        if view.privileges:
            print("    Privileges:")
            for privilege, grantable in view.privileges:
                print(f"      {privilege} (grantable={grantable})")
        else:
            print("    Privileges: none listed")

        if view.column_privileges:
            print("    Column privileges:")
            for column, privilege, grantable in view.column_privileges:
                print(f"      {column}: {privilege} (grantable={grantable})")

        print("    Columns:")
        if view.columns:
            for column, column_type, nullable, key, extra in view.columns:
                extras = [part for part in (key, extra) if part]
                suffix = f" [{', '.join(extras)}]" if extras else ""
                print(f"      {column} {column_type} nullable={nullable}{suffix}")
        else:
            print("      No columns visible")

        if view.definition:
            print(f"    Definition:\n      {view.definition}")
        else:
            print("    Definition: not visible (SHOW VIEW privilege required)")
