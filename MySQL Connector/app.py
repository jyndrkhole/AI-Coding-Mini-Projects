import hashlib
import hmac
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspector import run_inspection

load_dotenv()

st.set_page_config(
    page_title="MySQL Connector Inspector",
    page_icon="🗄️",
    layout="wide",
)


def _setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets[name]
        if value is not None:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def is_public_host() -> bool:
    flag = _setting("APP_PUBLIC", "").strip().lower()
    if flag in {"1", "true", "yes"}:
        return True
    if flag in {"0", "false", "no"}:
        return False
    return Path("/mount/src").exists()


def passwords_match(provided: str, expected: str) -> bool:
    left = hashlib.sha256(provided.encode("utf-8")).digest()
    right = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(left, right)


def require_share_access() -> bool:
    expected = _setting("APP_ACCESS_PASSWORD").strip()
    public = is_public_host()

    if public and not expected:
        st.error(
            "This public app is locked until an access password is set. "
            "In Streamlit Cloud, open Manage app → Settings → Secrets and add "
            "`APP_ACCESS_PASSWORD` plus `APP_PUBLIC = \"true\"`."
        )
        st.stop()

    if not expected:
        return True

    if st.session_state.get("share_ok"):
        return True

    st.title("MySQL Connector Inspector")
    st.caption("Enter the share password to continue. Database credentials are entered next and are not stored.")
    with st.form("share_gate"):
        provided = st.text_input("Access password", type="password")
        submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        if passwords_match(provided, expected):
            st.session_state.share_ok = True
            st.rerun()
        st.error("Incorrect access password")
    st.stop()


require_share_access()

public = is_public_host()
st.title("MySQL Connector Inspector")
st.caption("Connect to a MySQL database and review session info, grants, and view access.")

if public:
    st.info(
        "This is a shared inspector. It does not save your database password. "
        "Use a read-only MySQL user, require SSL, and allow this app's host to reach port 3306."
    )

with st.sidebar:
    st.subheader("Connection security")
    use_ssl = st.checkbox(
        "Require SSL/TLS",
        value=_setting("MYSQL_SSL", "true").strip().lower() not in {"0", "false", "no"},
        help="Keep this on for any database that is not on the same private network.",
    )
    ssl_ca = st.text_input(
        "SSL CA file path (optional)",
        value=_setting("MYSQL_SSL_CA") if not public else "",
        help="Path to a CA bundle if your provider requires it, such as Amazon RDS.",
    )
    st.caption("Do not use an admin account. Prefer a user with SELECT and SHOW VIEW only.")

default_host = "" if public else _setting("MYSQL_HOST")
default_user = "" if public else _setting("MYSQL_USER")
default_database = "" if public else _setting("MYSQL_DATABASE")

with st.form("connection_form"):
    col1, col2 = st.columns(2)

    with col1:
        host = st.text_input("Host", value=default_host)
        user = st.text_input("User", value=default_user)

    with col2:
        database = st.text_input("Database", value=default_database)
        password = st.text_input("Password", type="password")

    submitted = st.form_submit_button("Connect & Inspect", type="primary", use_container_width=True)

if submitted:
    missing = [
        label
        for label, value in [
            ("Host", host),
            ("User", user),
            ("Password", password),
            ("Database", database),
        ]
        if not value.strip()
    ]
    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
    else:
        with st.spinner("Connecting and inspecting..."):
            try:
                result = run_inspection(
                    host,
                    user,
                    password,
                    database,
                    use_ssl=use_ssl,
                    ssl_ca=ssl_ca.strip() or None,
                )
            except Exception as exc:
                st.error(f"Connection failed: {exc}")
            else:
                if result.connected:
                    st.success("Connected successfully")
                else:
                    st.warning("Connection established but status check failed")

                st.subheader("Session")
                session_cols = st.columns(3)
                session_cols[0].metric("Session user", result.session_user)
                session_cols[1].metric("Current user", result.current_user)
                session_cols[2].metric("Database", result.database)

                st.subheader("Grants")
                if result.grants:
                    for grant in result.grants:
                        st.code(grant, language="sql")
                else:
                    st.info("No grants found")

                st.subheader("Schema privileges")
                if result.schema_privileges:
                    st.dataframe(
                        [
                            {
                                "Schema": schema,
                                "Privilege": privilege,
                                "Grantable": grantable,
                            }
                            for schema, privilege, grantable in result.schema_privileges
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("None listed in information_schema.SCHEMA_PRIVILEGES")

                st.subheader("Table privileges")
                if result.table_privileges:
                    st.dataframe(
                        [
                            {
                                "Schema": schema,
                                "Table": table,
                                "Privilege": privilege,
                                "Grantable": grantable,
                            }
                            for schema, table, privilege, grantable in result.table_privileges
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("None listed in information_schema.TABLE_PRIVILEGES")

                st.subheader("View access")
                if not result.views:
                    st.info("No views found in the current database")
                else:
                    for view in result.views:
                        with st.expander(f"{result.database}.{view.name}", expanded=False):
                            detail_cols = st.columns(3)
                            detail_cols[0].write(f"**Updatable:** {view.updatable}")
                            detail_cols[1].write(f"**Check option:** {view.check_option or '—'}")
                            detail_cols[2].write(f"**Security:** {view.security_type or '—'}")

                            st.markdown("**Privileges**")
                            if view.privileges:
                                st.dataframe(
                                    [
                                        {"Privilege": p, "Grantable": g}
                                        for p, g in view.privileges
                                    ],
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            else:
                                st.caption("None listed")

                            st.markdown("**Column privileges**")
                            if view.column_privileges:
                                st.dataframe(
                                    [
                                        {
                                            "Column": col,
                                            "Privilege": p,
                                            "Grantable": g,
                                        }
                                        for col, p, g in view.column_privileges
                                    ],
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            else:
                                st.caption("None listed")

                            st.markdown("**Columns**")
                            if view.columns:
                                st.dataframe(
                                    [
                                        {
                                            "Column": col,
                                            "Type": col_type,
                                            "Nullable": nullable,
                                            "Key": key or "",
                                            "Extra": extra or "",
                                        }
                                        for col, col_type, nullable, key, extra in view.columns
                                    ],
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            else:
                                st.caption("No columns visible")

                            st.markdown("**Definition**")
                            if view.definition:
                                st.code(view.definition, language="sql")
                            else:
                                st.caption("Not visible (SHOW VIEW privilege required)")
