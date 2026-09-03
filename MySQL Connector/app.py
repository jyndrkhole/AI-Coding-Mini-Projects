import os

import streamlit as st
from dotenv import load_dotenv

from inspector import run_inspection

load_dotenv()

st.set_page_config(
    page_title="MySQL Connector Inspector",
    page_icon="🗄️",
    layout="wide",
)

st.title("MySQL Connector Inspector")
st.caption("Connect to a MySQL database and review session info, grants, and view access.")

with st.form("connection_form"):
    col1, col2 = st.columns(2)

    with col1:
        host = st.text_input("Host", value=os.getenv("MYSQL_HOST", ""))
        user = st.text_input("User", value=os.getenv("MYSQL_USER", ""))

    with col2:
        database = st.text_input("Database", value=os.getenv("MYSQL_DATABASE", ""))
        password = st.text_input(
            "Password",
            value=os.getenv("MYSQL_PASSWORD", ""),
            type="password",
        )

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
                result = run_inspection(host, user, password, database)
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
