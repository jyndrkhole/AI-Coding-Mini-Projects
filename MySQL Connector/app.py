import hashlib
import hmac
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspector import (
    classify_case_views,
    detect_policy_column,
    count_view_rows,
    fetch_rows_by_values,
    fetch_view_ordered,
    preview_view,
    query_records,
    quote_ident,
    run_inspection,
    run_select,
)

load_dotenv()

st.set_page_config(
    page_title="Case Viewer",
    page_icon="🗄️",
    layout="wide",
)

APP_CSS = """
<style>
.stApp {
    background:
        radial-gradient(900px 280px at 8% -8%, rgba(15, 107, 92, 0.10), transparent 60%),
        #F3F0E8;
}
[data-testid="stHeader"] {
    background: transparent;
}
[data-testid="stBaseButton-header"] {
    display: none;
}
.app-hero a,
.guide-card a {
    display: none;
}
[data-testid="stDecoration"] {
    background: linear-gradient(90deg, #0F6B5C, #C4A35A);
    height: 3px;
}
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 3rem;
    max-width: 1180px;
}
.app-hero {
    padding: 0 0 0.85rem 0;
    margin-bottom: 0.9rem;
    border-bottom: 1px solid #E2D9CC;
}
.app-hero h1 {
    margin: 0 0 0.25rem 0;
    color: #16302B;
    letter-spacing: -0.02em;
}
.app-hero p {
    margin: 0;
    max-width: 40rem;
    color: #5E6B66;
    font-size: 1.05rem;
}
.section-label {
    margin: 0 0 0.35rem 0;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6A6258;
}
div[data-testid="stForm"] {
    background: #FFFCF7;
    border: 1px solid #E2D9CC;
    border-radius: 0.9rem;
    padding: 0.85rem 1rem 0.35rem 1rem;
    box-shadow: 0 10px 30px rgba(28, 43, 39, 0.04);
}
div[data-testid="stAlert"] {
    border-radius: 0.75rem;
}
.guide-card {
    background: #FFFCF7;
    border: 1px solid #E2D9CC;
    border-radius: 0.85rem;
    padding: 0.9rem 1rem 0.2rem 1rem;
    min-height: 7.2rem;
}
.guide-card h3 {
    margin: 0 0 0.25rem 0;
    color: #16302B;
}
.guide-card p {
    margin: 0;
    color: #5E6B66;
}
</style>
"""


def apply_theme() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def render_hero(subtitle: str = "") -> None:
    detail = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="app-hero">
            <h1>Case Viewer</h1>
            {detail}
        </div>
        """,
        unsafe_allow_html=True,
    )


apply_theme()


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


_CONNECTION_KEYS = (
    "connection",
    "inspection",
    "summary_view",
    "details_view",
    "policy_column",
    "summary_query",
    "selected_policies",
    "selected_carriers",
    "details_query",
    "details_for",
    "last_activity",
    "summary_total",
)
_CONNECTION_PREFIXES = ("preview_", "view_query_", "view_for_", "view_count_", "limit_", "sql_")


def _idle_seconds() -> int:
    raw = _setting("SESSION_IDLE_MINUTES", "30").strip()
    try:
        minutes = int(raw)
    except ValueError:
        minutes = 30
    return max(1, minutes) * 60


def _idle_expired() -> bool:
    last = st.session_state.get("last_activity")
    if not last:
        return False
    return time.time() - float(last) >= _idle_seconds()


def _disconnect() -> None:
    for key in list(st.session_state.keys()):
        if key in _CONNECTION_KEYS or str(key).startswith(_CONNECTION_PREFIXES):
            del st.session_state[key]


@st.fragment(run_every=timedelta(minutes=1))
def _watch_idle() -> None:
    if st.session_state.get("inspection") and _idle_expired():
        st.rerun()


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

    render_hero("Enter the share password to continue. Database credentials are entered next and are not stored.")
    _, gate, _ = st.columns([1, 1.15, 1])
    with gate, st.form("share_gate"):
        provided = st.text_input("Access password", type="password")
        submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        if passwords_match(provided, expected):
            st.session_state.share_ok = True
            st.rerun()
        st.error("Incorrect access password")
    st.stop()


SUMMARY_COLUMNS = (
    "policy_number",
    "PolicyNumber",
    "application_reference_number",
    "insured_name",
    "agent_name",
    "AgentName",
    "carrier_id",
    "carrier_name",
    "plan_name",
    "PlanName",
    "product_cusip_number",
    "qualified_plan_type_code",
    "application_status",
    "ApplicationStatus",
    "application_submission_channel",
    "status_category",
    "effective_date",
    "EffectiveDate",
    "received_date",
    "ReceivedDate",
    "gross_amount",
    "GrossAmount",
    "category",
    "sub_category",
)


def _named_column(names: list[str], aliases: tuple[str, ...]) -> str | None:
    lookup = {name.lower(): name for name in names}
    for alias in aliases:
        found = lookup.get(alias.lower())
        if found:
            return found
    return None


def _carrier_columns(names: list[str]) -> tuple[str | None, str | None]:
    return (
        _named_column(names, ("carrier_id", "CarrierId", "CarrierID")),
        _named_column(names, ("carrier_name", "CarrierName")),
    )


def _cell_text(row: dict, column: str | None) -> str:
    if not column:
        return ""
    raw = row.get(column)
    if raw is None:
        return ""
    return str(raw).strip()


def _carrier_label(row: dict, id_column: str | None, name_column: str | None) -> str | None:
    ident = _cell_text(row, id_column)
    name = _cell_text(row, name_column)
    if name and ident:
        return f"{name} ({ident})"
    if name:
        return name
    if ident:
        return f"ID {ident}"
    return None


def _carrier_options(records: list[dict], id_column: str | None, name_column: str | None) -> list[str]:
    values = []
    seen = set()
    for record in records:
        label = _carrier_label(record, id_column, name_column)
        if not label or label in seen:
            continue
        seen.add(label)
        values.append(label)
    return sorted(values, key=str.lower)


def _selection_ids_and_names(selected: list[str]) -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    names: set[str] = set()
    for label in selected:
        if label.startswith("ID ") and " (" not in label:
            ids.add(label[3:])
            continue
        name, separator, ident = label.rpartition(" (")
        if separator and ident.endswith(")"):
            ids.add(ident[:-1])
            if name:
                names.add(name)
        else:
            names.add(label)
    return ids, names


def _row_matches_carriers(
    row: dict,
    id_column: str | None,
    name_column: str | None,
    selected: list[str],
) -> bool:
    if not selected:
        return True
    ids, names = _selection_ids_and_names(selected)
    ident = _cell_text(row, id_column)
    name = _cell_text(row, name_column)
    if id_column and ident:
        return ident in ids
    if name_column and name:
        return name in names
    return False


def _policy_options(records: list[dict], policy_column: str) -> list[str]:
    values = []
    seen = set()
    for record in records:
        raw = record.get(policy_column)
        if raw is None or str(raw).strip() == "":
            continue
        value = str(raw)
        if value not in seen:
            seen.add(value)
            values.append(value)
    return sorted(values, reverse=True)


def _summary_records(records: list[dict]) -> list[dict]:
    if not records:
        return []
    available = list(records[0].keys())
    lookup = {name.lower(): name for name in available}
    chosen = []
    for name in SUMMARY_COLUMNS:
        actual = lookup.get(name.lower())
        if actual and actual not in chosen:
            chosen.append(actual)
    for name in available:
        if name not in chosen:
            chosen.append(name)
    return [{name: record.get(name) for name in chosen} for record in records]


def _tab_label(view_name: str) -> str:
    label = view_name[3:] if view_name.lower().startswith("vw_") else view_name
    words = label.replace("_", " ").strip()
    if words.lower() == "lat":
        return "LAT"
    return words.title()


def _other_case_views(views, summary_view) -> list:
    summary_name = summary_view.name.lower() if summary_view else ""
    return [view for view in views if view.name.lower() != summary_name]


def _load_ordered_view(connection: dict, view_name: str, policy_column: str | None):
    try:
        return fetch_view_ordered(
            **connection,
            view_name=view_name,
            order_column=policy_column,
            descending=True,
            limit=2000,
        )
    except Exception as exc:
        if not policy_column or "1054" not in str(exc):
            raise
        return fetch_view_ordered(
            **connection,
            view_name=view_name,
            order_column=None,
            descending=True,
            limit=2000,
        )


def _counted_records(records: list[dict], total: int) -> list[dict]:
    label = f"Rows ({total:,})"
    counted = []
    for index, record in enumerate(records, start=1):
        counted.append({label: index, **record})
    return counted


def _render_table(records: list[dict], *, total: int, truncated: bool = False) -> None:
    shown = len(records)
    if shown == 0:
        st.info("0 rows")
        return
    header_total = total if shown < total or not truncated else shown
    if shown < total:
        st.caption(f"Showing {shown:,} of {total:,} rows")
    elif truncated:
        st.caption(f"Showing the first {shown:,} rows. More rows match.")
    st.dataframe(_counted_records(records, header_total), width="stretch", hide_index=True)


def _render_case_view(
    view,
    connection: dict,
    selected: list[str],
    carriers: list[str] | None = None,
) -> None:
    carriers = list(carriers or [])
    policy_column = _policy_column_for(view)
    narrowed = list(selected) if selected and policy_column else []
    cache_key = (view.name, tuple(narrowed))
    query_key = f"view_query_{view.name}"
    count_key = f"view_count_{view.name}"
    for_key = f"view_for_{view.name}"
    if st.session_state.get(for_key) != cache_key:
        try:
            if narrowed:
                query = fetch_rows_by_values(
                    **connection,
                    view_name=view.name,
                    column=policy_column,
                    values=narrowed,
                    descending=True,
                )
            else:
                query = _load_ordered_view(connection, view.name, policy_column)
            total = count_view_rows(
                **connection,
                view_name=view.name,
                column=policy_column if narrowed else None,
                values=narrowed or None,
            )
        except Exception as exc:
            st.session_state[query_key] = None
            st.session_state[count_key] = None
            st.session_state[for_key] = cache_key
            st.error(f"Could not load {view.name}: {exc}")
            return
        st.session_state[query_key] = query
        st.session_state[count_key] = total
        st.session_state[for_key] = cache_key

    query = st.session_state.get(query_key)
    if not query:
        return
    records = _summary_records(query_records(query))
    total = st.session_state.get(count_key)
    if total is None:
        total = len(records)
    truncated = bool(query.truncated and len(records) >= int(total))
    if carriers:
        try:
            names = _view_column_names(view)
            if records:
                names = list(dict.fromkeys([*names, *records[0].keys()]))
            id_column, name_column = _carrier_columns(names)
            if not id_column and not name_column:
                st.info(
                    f"`{view.name}` has no carrier name or ID column, so the carrier filter was not applied."
                )
            else:
                records = [
                    row
                    for row in records
                    if _row_matches_carriers(row, id_column, name_column, carriers)
                ]
                total = len(records)
                truncated = False
                st.caption(f"{len(carriers)} carrier(s) selected.")
        except Exception as exc:
            st.warning(f"Carrier filter was not applied to {view.name}: {exc}")
    if narrowed:
        st.caption(f"{len(narrowed)} selected case(s) from `{view.name}`")
    elif policy_column:
        st.caption(f"All rows from `{view.name}`. Select cases on Summary to narrow this list.")
    else:
        st.caption(f"All rows from `{view.name}`")
    _render_table(records, total=int(total), truncated=truncated)
    _render_sql_runner(connection["database"], view.name, connection)


def _render_sql_runner(database: str, view_name: str, connection: dict) -> None:
    st.markdown("**Query this view**")
    default_sql = (
        f"SELECT * FROM {quote_ident(database)}.{quote_ident(view_name)} LIMIT 100"
    )
    row_limit = st.number_input(
        "Row limit",
        min_value=1,
        max_value=1000,
        value=100,
        key=f"limit_{view_name}",
    )
    sql_text = st.text_area(
        "SQL (SELECT only, this view)",
        value=default_sql,
        height=80,
        key=f"sql_{view_name}",
    )
    load_col, run_col = st.columns(2)
    load_clicked = load_col.button(
        "Load SELECT *",
        key=f"load_{view_name}",
        width="stretch",
    )
    run_clicked = run_col.button(
        "Run SQL",
        key=f"run_{view_name}",
        width="stretch",
    )
    preview_key = f"preview_{view_name}"
    if load_clicked or run_clicked:
        try:
            if load_clicked:
                query = preview_view(
                    **connection,
                    view_name=view_name,
                    limit=int(row_limit),
                )
            else:
                query = run_select(
                    **connection,
                    sql=sql_text,
                    allowed_view=view_name,
                    max_rows=int(row_limit),
                )
        except Exception as exc:
            st.error(f"Query failed: {exc}")
        else:
            st.session_state[preview_key] = query

    query = st.session_state.get(preview_key)
    if not query:
        return
    st.caption(query.sql)
    records = query_records(query)
    shown = len(records)
    _render_table(
        records,
        total=shown,
        truncated=bool(query.truncated),
    )


def _view_column_names(view) -> list[str]:
    if view is None:
        return []
    return [column[0] for column in view.columns]


def _policy_column_for(view) -> str | None:
    names = _view_column_names(view)
    lookup = {name.lower(): name for name in names}
    configured = _setting("POLICY_COLUMN").strip()
    if configured and configured.lower() in lookup:
        return lookup[configured.lower()]
    return detect_policy_column(names)


def _load_case_data(connection: dict, result) -> None:
    summary_view, details_view = classify_case_views(
        result.views,
        summary_name=_setting("SUMMARY_VIEW") or None,
        details_name=_setting("DETAILS_VIEW") or None,
    )
    st.session_state.summary_view = summary_view
    st.session_state.details_view = details_view
    if summary_view is None:
        st.session_state.summary_query = None
        return
    policy_column = _policy_column_for(summary_view)
    summary_query = _load_ordered_view(connection, summary_view.name, policy_column)
    if policy_column and "ORDER BY" not in summary_query.sql.upper():
        policy_column = None
    st.session_state.policy_column = policy_column
    st.session_state.summary_query = summary_query
    try:
        st.session_state.summary_total = count_view_rows(
            **connection,
            view_name=summary_view.name,
        )
    except Exception:
        st.session_state.summary_total = len(summary_query.rows)
    st.session_state.pop("selected_policies", None)
    st.session_state.pop("selected_carriers", None)
    st.session_state.pop("details_query", None)
    st.session_state.pop("details_for", None)


require_share_access()

session_expired = False
if st.session_state.get("inspection") and _idle_expired():
    _disconnect()
    session_expired = True

public = is_public_host()
render_hero()
if session_expired:
    st.info("This session ended after a period of inactivity. Connect again.")

if public:
    st.info(
        "This is a shared inspector. It does not save your database password. "
        "Use a read-only MySQL user, require SSL, and allow this app's host to reach port 3306."
    )

use_ssl = _setting("MYSQL_SSL", "true").strip().lower() not in {"0", "false", "no"}
ssl_ca = "" if public else _setting("MYSQL_SSL_CA")

default_host = "" if public else _setting("MYSQL_HOST")
default_user = "" if public else _setting("MYSQL_USER")
default_database = "" if public else _setting("MYSQL_DATABASE")

saved_connection = st.session_state.get("connection") or {}
already_connected = bool(st.session_state.get("inspection"))
if already_connected:
    database_name = saved_connection.get("database") or "database"
    host_name = saved_connection.get("host") or "host"
    form_area = st.expander(
        f"Database connection · {database_name} on {host_name}",
        expanded=False,
        key=f"connection_panel_{st.session_state.get('connection_panel', 0)}",
    )
else:
    st.markdown('<p class="section-label">Database connection</p>', unsafe_allow_html=True)
    form_area = st.container()

with form_area:
    with st.form("connection_form"):
        col1, col2 = st.columns(2)

        with col1:
            host = st.text_input("Host", value=default_host)
            user = st.text_input("User", value=default_user)

        with col2:
            database = st.text_input("Database", value=default_database)
            password = st.text_input("Password", type="password")

        submitted = st.form_submit_button("Connect & Inspect", type="primary", width="stretch")

connection = {
    "host": host,
    "user": user,
    "password": password,
    "database": database,
    "use_ssl": use_ssl,
    "ssl_ca": ssl_ca.strip() or None,
}

if submitted:
    missing = [
        label
        for label, value in [
            ("Host", connection["host"]),
            ("User", connection["user"]),
            ("Password", connection["password"]),
            ("Database", connection["database"]),
        ]
        if not value.strip()
    ]
    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
    else:
        with st.spinner("Connecting and inspecting..."):
            try:
                result = run_inspection(**connection)
            except Exception as exc:
                st.error(f"Connection failed: {exc}")
            else:
                st.session_state.connection = connection
                st.session_state.inspection = result
                for key in list(st.session_state.keys()):
                    if str(key).startswith(("preview_", "view_query_", "view_for_")):
                        del st.session_state[key]
                try:
                    _load_case_data(connection, result)
                except Exception as exc:
                    st.session_state.summary_query = None
                    st.session_state.summary_warning = str(exc)
                else:
                    st.session_state.pop("summary_warning", None)
                st.session_state.connection_panel = int(st.session_state.get("connection_panel", 0)) + 1
                st.rerun()

result = st.session_state.get("inspection")
connection = st.session_state.get("connection", connection)

if result:
    status_col, disconnect_col = st.columns([5, 1])
    with status_col:
        if result.connected:
            st.success("Connected successfully")
        else:
            st.warning("Connection established but status check failed")
    with disconnect_col:
        if st.button("Disconnect", width="stretch"):
            _disconnect()
            st.rerun()

    summary_warning = st.session_state.pop("summary_warning", None)
    if summary_warning:
        st.warning(f"Could not load case summary: {summary_warning}")

    summary_view = st.session_state.get("summary_view")
    case_views = _other_case_views(result.views, summary_view)
    tab_labels = ["Summary"] + [_tab_label(view.name) for view in case_views]
    tabs = st.tabs(tab_labels)
    summary_tab = tabs[0]
    policy_column = st.session_state.get("policy_column")
    summary_query = st.session_state.get("summary_query")
    summary_rows = query_records(summary_query) if summary_query else []
    policy_selected: list[str] = []
    carrier_selected: list[str] = []

    with summary_tab:
        if not result.views:
            st.info("No views found in the current database")
        elif not summary_view:
            st.info("No summary view is available")
        else:
            st.caption(
                f"Summary from `{result.database}.{summary_view.name}`"
                + (f", ordered by `{policy_column}` descending" if policy_column else "")
            )
            summary_total = int(st.session_state.get("summary_total") or len(summary_rows))
            column_names = _view_column_names(summary_view)
            if summary_rows:
                column_names = list(dict.fromkeys([*column_names, *summary_rows[0].keys()]))
            try:
                carrier_id_column, carrier_name_column = _carrier_columns(column_names)
                carrier_options = _carrier_options(
                    summary_rows,
                    carrier_id_column,
                    carrier_name_column,
                )
                carrier_filter_error = False
            except Exception as exc:
                carrier_id_column, carrier_name_column = None, None
                carrier_options = []
                carrier_filter_error = True
                st.warning(f"Could not build the carrier filter: {exc}")

            show_policy = bool(policy_column)
            show_carrier = bool(carrier_id_column or carrier_name_column)
            if not show_policy:
                st.warning("No Policy Number column was found. Showing the summary view as-is.")
            if not show_carrier and not carrier_filter_error:
                st.caption(
                    "Carrier filter is unavailable because this view has no carrier_name or carrier_id column."
                )
            if show_policy and show_carrier:
                policy_col, carrier_col = st.columns(2)
            else:
                policy_col = carrier_col = st.container()
            if show_policy:
                with policy_col:
                    policy_selected = st.multiselect(
                        "Cases (Policy Numbers)",
                        options=_policy_options(summary_rows, policy_column),
                        key="selected_policies",
                        help="Select one or more policies to narrow the other tabs.",
                    )
            if show_carrier:
                with carrier_col:
                    carrier_selected = st.multiselect(
                        "Carrier (Name / ID)",
                        options=carrier_options,
                        key="selected_carriers",
                        help="Select one or more carriers. Views without these columns stay unfiltered.",
                    )
                    if not carrier_options:
                        st.caption("No carrier name or ID values were found in the loaded rows.")

            visible = []
            for row in _summary_records(summary_rows):
                if policy_selected and str(row.get(policy_column)) not in set(policy_selected):
                    continue
                if carrier_selected and not _row_matches_carriers(
                    row,
                    carrier_id_column,
                    carrier_name_column,
                    carrier_selected,
                ):
                    continue
                visible.append(row)
            filtered = bool(policy_selected or carrier_selected)
            visible_total = len(visible) if filtered else summary_total
            _render_table(
                visible,
                total=visible_total,
                truncated=bool(
                    not filtered
                    and summary_query
                    and summary_query.truncated
                    and len(summary_rows) >= summary_total
                ),
            )
            if policy_selected or carrier_selected:
                parts = []
                if policy_selected:
                    parts.append(f"{len(policy_selected)} case(s)")
                if carrier_selected:
                    parts.append(f"{len(carrier_selected)} carrier(s)")
                st.caption(f"{' and '.join(parts)} selected. Open another tab to see those cases.")
            elif show_policy or show_carrier:
                st.caption("Select policy numbers or carriers to narrow the other tabs.")
            if not case_views:
                st.info("This database has no other views. Connect to a database that grants more views to see them as tabs.")
            _render_sql_runner(result.database, summary_view.name, connection)


    for tab, view in zip(tabs[1:], case_views):
        with tab:
            _render_case_view(view, connection, policy_selected, carrier_selected)

if st.session_state.get("inspection") and not session_expired:
    st.session_state.last_activity = time.time()
    _watch_idle()
