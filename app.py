import streamlit as st
import pandas as pd
import sqlite3
import uuid
from datetime import date, datetime, timedelta

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="FinOps360",
    page_icon="💰",
    layout="wide"
)

DATABASE = "finops.db"


# --------------------------------------------------
# DATABASE
# --------------------------------------------------
def get_connection():
    return sqlite3.connect(DATABASE, timeout=30)


# --------------------------------------------------
# VISITOR ANALYTICS DATABASE
# --------------------------------------------------

def init_visitor_tracking():
    """Create visitor analytics table safely."""

    conn = get_connection()

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                visit_date TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_app_visits_visit_date
            ON app_visits(visit_date)
            """
        )

        conn.commit()

    finally:
        conn.close()


def track_current_session():
    """
    Create one browser session and keep updating
    its last_seen time.
    """

    if "finops_session_id" not in st.session_state:

        st.session_state.finops_session_id = str(
            uuid.uuid4()
        )

        now = datetime.now()

        conn = get_connection()

        try:

            conn.execute(
                """
                INSERT INTO app_visits
                (
                    session_id,
                    visit_date,
                    last_seen
                )
                VALUES (?, ?, ?)
                """,
                (
                    st.session_state.finops_session_id,
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%Y-%m-%d %H:%M:%S")
                )
            )

            conn.commit()

        finally:
            conn.close()

    else:

        now = datetime.now()

        conn = get_connection()

        try:

            conn.execute(
                """
                UPDATE app_visits
                SET last_seen = ?
                WHERE session_id = ?
                """,
                (
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                    st.session_state.finops_session_id
                )
            )

            conn.commit()

        finally:
            conn.close()


def load_usage_analytics():

    conn = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                session_id,
                visit_date,
                last_seen
            FROM app_visits
            ORDER BY visit_date ASC
            """,
            conn
        )

    finally:
        conn.close()


# --------------------------------------------------
# INITIALIZE VISITOR TRACKING
# --------------------------------------------------

init_visitor_tracking()
track_current_session()


# --------------------------------------------------
# APP USAGE ANALYTICS
# --------------------------------------------------

def show_usage_analytics():

    st.subheader("📊 App Usage Analytics")

    visits = load_usage_analytics()

    if visits.empty:

        st.info("No visitor data available yet.")

        return

    # Convert dates safely
    visits["visit_date"] = pd.to_datetime(
        visits["visit_date"],
        errors="coerce"
    )

    visits["last_seen"] = pd.to_datetime(
        visits["last_seen"],
        errors="coerce"
    )

    visits = visits.dropna(
        subset=["visit_date"]
    )

    # --------------------------------------------------
    # BASIC METRICS
    # --------------------------------------------------

    total_visits = len(visits)

    unique_visitors = visits[
        "session_id"
    ].nunique()

    today = pd.Timestamp(
        date.today()
    )

    today_visits = int(
        (
            visits["visit_date"].dt.normalize()
            == today
        ).sum()
    )

    active_cutoff = pd.Timestamp(
        datetime.now()
        - timedelta(minutes=15)
    )

    active_sessions = int(
        (
            visits["last_seen"]
            >= active_cutoff
        ).sum()
    )

    # --------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "👀 Total Visits",
            total_visits
        )

    with col2:

        st.metric(
            "👤 Unique Visitors",
            unique_visitors
        )

    with col3:

        st.metric(
            "🟢 Active Sessions",
            active_sessions
        )

    with col4:

        st.metric(
            "📅 Today",
            today_visits
        )

    st.caption(
        "Visitor statistics are estimated from browser "
        "sessions. A new browser session is counted as a "
        "new visit."
    )

    # --------------------------------------------------
    # VISITOR TREND
    # --------------------------------------------------

    st.markdown("### 📈 Visitor Trend")

    trend_view = st.radio(
        "View",
        [
            "Monthly",
            "Yearly"
        ],
        horizontal=True,
        key="visitor_trend"
    )

    # ==================================================
    # MONTHLY GRAPH
    # ==================================================

    if trend_view == "Monthly":

        monthly = (
            visits
            .assign(
                month=visits[
                    "visit_date"
                ].dt.to_period("M")
            )
            .groupby("month")
            .size()
            .rename("Visitors")
        )

        current_month = (
            pd.Timestamp.today()
            .to_period("M")
        )

        start_month = (
            current_month - 11
        )

        month_index = pd.period_range(
            start=start_month,
            end=current_month,
            freq="M"
        )

        monthly = monthly.reindex(
            month_index,
            fill_value=0
        )

        monthly.index = monthly.index.strftime(
            "%b %Y"
        )

        st.line_chart(
            monthly,
            use_container_width=True
        )

    # ==================================================
    # YEARLY GRAPH
    # ==================================================

    else:

        yearly = (
            visits
            .assign(
                year=visits[
                    "visit_date"
                ].dt.year
            )
            .groupby("year")
            .size()
            .rename("Visitors")
        )

        current_year = date.today().year

        # Show current year + previous 4 years
        year_index = pd.Index(
            range(
                current_year - 4,
                current_year + 1
            ),
            name="Year"
        )

        yearly = yearly.reindex(
            year_index,
            fill_value=0
        )

        st.bar_chart(
            yearly,
            use_container_width=True
        )

    # --------------------------------------------------
    # DAILY VISITOR TREND
    # --------------------------------------------------

    st.markdown("### 📅 Recent Daily Visits")

    daily = (
        visits
        .assign(
            day=visits[
                "visit_date"
            ].dt.date
        )
        .groupby("day")
        .size()
        .rename("Visits")
    )

    last_30_days = pd.date_range(
        end=pd.Timestamp.today(),
        periods=30,
        freq="D"
    )

    daily_index = pd.Index(
        last_30_days.date
    )

    daily = daily.reindex(
        daily_index,
        fill_value=0
    )

    st.area_chart(
        daily,
        use_container_width=True
    )

    st.divider()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Dashboard",
        "💳 Expenses",
        "🧾 Invoices",
        "🏢 Vendors",
        "📈 Reports"
    ]
)


# ==================================================
# EXPENSE PAGE
# ==================================================
if page == "💳 Expenses":

    st.title("💳 Expense Management")

    st.caption(
        "Record and manage company expenses"
    )

    st.divider()

    st.subheader("➕ Add New Expense")

    with st.form(
        "expense_form",
        clear_on_submit=True
    ):

        col1, col2 = st.columns(2)

        with col1:

            expense_date = st.date_input(
                "Expense Date",
                value=date.today()
            )

            category = st.selectbox(
                "Category",
                [
                    "Software",
                    "Cloud",
                    "Hardware",
                    "Travel",
                    "Office",
                    "Marketing",
                    "Utilities",
                    "Other"
                ]
            )

            amount = st.number_input(
                "Amount (₹)",
                min_value=0.0,
                step=500.0,
                format="%.2f"
            )

        with col2:

            department = st.selectbox(
                "Department",
                [
                    "Engineering",
                    "Finance",
                    "Operations",
                    "Sales",
                    "Marketing",
                    "HR"
                ]
            )

            description = st.text_input(
                "Description",
                placeholder="Example: AWS cloud services"
            )

        submitted = st.form_submit_button(
            "➕ Add Expense",
            use_container_width=True
        )

        if submitted:

            if amount <= 0:

                st.error(
                    "Please enter an amount greater than ₹0."
                )

            elif not description.strip():

                st.error(
                    "Please enter a description."
                )

            else:

                add_expense(
                    expense_date.strftime(
                        "%Y-%m-%d"
                    ),
                    category,
                    department,
                    amount,
                    description.strip()
                )

                st.success(
                    f"Expense of ₹{amount:,.2f} "
                    "added successfully!"
                )

                st.rerun()

    st.divider()

    st.subheader(
        "📋 Expense Transactions"
    )

    expenses = load_expenses()

    if expenses.empty:

        st.info(
            "No expense transactions found."
        )

    else:

        display_expenses = expenses.copy()

        display_expenses["amount"] = (
            display_expenses["amount"]
            .apply(
                lambda x:
                f"₹{x:,.2f}"
            )
        )

        display_expenses.columns = [
            "ID",
            "Date",
            "Category",
            "Department",
            "Amount",
            "Description"
        ]

        st.dataframe(
            display_expenses,
            use_container_width=True,
            hide_index=True
        )


# ==================================================
# VENDOR PAGE
# ==================================================
elif page == "🏢 Vendors":

    st.title(
        "🏢 Vendor Management"
    )

    st.caption(
        "Manage vendors used for invoices and payments"
    )

    st.divider()

    st.subheader(
        "➕ Add New Vendor"
    )

    with st.form(
        "vendor_form",
        clear_on_submit=True
    ):

        vendor_name = st.text_input(
            "Vendor Name",
            placeholder="Example: Amazon Web Services"
        )

        submitted = st.form_submit_button(
            "🏢 Add Vendor",
            use_container_width=True
        )

        if submitted:

            if not vendor_name.strip():

                st.error(
                    "Please enter a vendor name."
                )

            else:

                conn = get_connection()

                try:

                    conn.execute(
                        """
                        INSERT INTO vendors
                        (vendor_name)
                        VALUES (?)
                        """,
                        (
                            vendor_name.strip(),
                        )
                    )

                    conn.commit()

                    st.success(
                        f"Vendor '{vendor_name}' "
                        "added successfully!"
                    )

                    st.rerun()

                except sqlite3.IntegrityError:

                    st.error(
                        "This vendor already exists."
                    )

                finally:

                    conn.close()

    st.divider()

    st.subheader(
        "📋 Registered Vendors"
    )

    vendors = load_vendors()

    if vendors.empty:

        st.info(
            "No vendors found."
        )

    else:

        st.metric(
            "Total Vendors",
            len(vendors)
        )

        vendor_display = vendors.copy()

        vendor_display.columns = [
            "Vendor ID",
            "Vendor Name"
        ]

        st.dataframe(
            vendor_display,
            use_container_width=True,
            hide_index=True
        )


# ==================================================
# INVOICE PAGE
# ==================================================
elif page == "🧾 Invoices":

    st.title(
        "🧾 Invoice Management"
    )

    st.caption(
        "Track vendor invoices and payment status"
    )

    st.divider()

    vendors = load_vendors()

    st.subheader(
        "➕ Create New Invoice"
    )

    if vendors.empty:

        st.warning(
            "No vendors found in the database."
        )

    else:

        with st.form(
            "invoice_form",
            clear_on_submit=True
        ):

            col1, col2 = st.columns(2)

            with col1:

                vendor_names = (
                    vendors["vendor_name"]
                    .tolist()
                )

                selected_vendor = st.selectbox(
                    "Vendor",
                    vendor_names
                )

                invoice_number = st.text_input(
                    "Invoice Number",
                    placeholder="Example: INV-2026-006"
                )

                amount = st.number_input(
                    "Invoice Amount (₹)",
                    min_value=0.0,
                    step=1000.0,
                    format="%.2f"
                )

            with col2:

                invoice_date = st.date_input(
                    "Invoice Date",
                    value=date.today()
                )

                due_date = st.date_input(
                    "Due Date",
                    value=date.today()
                )

                status = st.selectbox(
                    "Payment Status",
                    [
                        "Pending",
                        "Paid"
                    ]
                )

            submitted = st.form_submit_button(
                "🧾 Create Invoice",
                use_container_width=True
            )

            if submitted:

                if not invoice_number.strip():

                    st.error(
                        "Please enter an invoice number."
                    )

                elif amount <= 0:

                    st.error(
                        "Invoice amount must be greater than ₹0."
                    )

                elif due_date < invoice_date:

                    st.error(
                        "Due date cannot be before invoice date."
                    )

                else:

                    selected_vendor_id = vendors[
                        vendors["vendor_name"]
                        == selected_vendor
                    ]["vendor_id"].iloc[0]

                    try:

                        add_invoice(
                            int(
                                selected_vendor_id
                            ),
                            invoice_number.strip(),
                            invoice_date.strftime(
                                "%Y-%m-%d"
                            ),
                            due_date.strftime(
                                "%Y-%m-%d"
                            ),
                            amount,
                            status
                        )

                        st.success(
                            f"Invoice {invoice_number} "
                            "created successfully!"
                        )

                        st.rerun()

                    except sqlite3.IntegrityError:

                        st.error(
                            "Invoice number already exists."
                        )

    st.divider()

    invoices = load_invoices()

    if invoices.empty:

        st.info(
            "No invoices found."
        )

    else:

        pending = invoices[
            invoices["status"]
            == "Pending"
        ]

        paid = invoices[
            invoices["status"]
            == "Paid"
        ]

        today = pd.Timestamp(
            date.today()
        )

        overdue = invoices[
            (
                invoices["status"]
                == "Pending"
            )
            &
            (
                pd.to_datetime(
                    invoices["due_date"]
                )
                < today
            )
        ]

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Pending Payments",
                f"₹{pending['amount'].sum():,.0f}"
            )

        with col2:

            st.metric(
                "Paid Invoices",
                f"₹{paid['amount'].sum():,.0f}"
            )

        with col3:

            st.metric(
                "Overdue Invoices",
                str(len(overdue))
            )

        st.divider()

        if not overdue.empty:

            st.error(
                f"⚠️ {len(overdue)} "
                "invoice(s) are overdue!"
            )

            overdue_display = overdue[
                [
                    "invoice_number",
                    "vendor_name",
                    "due_date",
                    "amount",
                    "status"
                ]
            ].copy()

            overdue_display["amount"] = (
                overdue_display["amount"]
                .apply(
                    lambda x:
                    f"₹{x:,.0f}"
                )
            )

            st.dataframe(
                overdue_display,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.success(
                "✅ No overdue pending invoices."
            )

        st.subheader(
            "📋 All Invoices"
        )

        invoice_display = invoices[
            [
                "invoice_number",
                "vendor_name",
                "invoice_date",
                "due_date",
                "amount",
                "status"
            ]
        ].copy()

        invoice_display["amount"] = (
            invoice_display["amount"]
            .apply(
                lambda x:
                f"₹{x:,.0f}"
            )
        )

        st.dataframe(
            invoice_display,
            use_container_width=True,
            hide_index=True
        )


# ==================================================
# REPORTS PAGE
# ==================================================
elif page == "📈 Reports":

    st.title(
        "📈 Financial Reports"
    )

    st.caption(
        "Live financial and operations analytics"
    )

    expenses = load_expenses()
    invoices = load_invoices()
    budgets = load_budgets()

    st.subheader(
        "🔎 Report Filters"
    )

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:

        categories = (
            ["All"]
            +
            sorted(
                expenses[
                    "category"
                ]
                .dropna()
                .unique()
                .tolist()
            )
        )

        selected_category = st.selectbox(
            "Category",
            categories
        )

    with filter_col2:

        departments = (
            ["All"]
            +
            sorted(
                expenses[
                    "department"
                ]
                .dropna()
                .unique()
                .tolist()
            )
        )

        selected_department = st.selectbox(
            "Department",
            departments
        )

    filtered_expenses = expenses.copy()

    if selected_category != "All":

        filtered_expenses = (
            filtered_expenses[
                filtered_expenses[
                    "category"
                ]
                == selected_category
            ]
        )

    if selected_department != "All":

        filtered_expenses = (
            filtered_expenses[
                filtered_expenses[
                    "department"
                ]
                == selected_department
            ]
        )

    total_expenses = (
        filtered_expenses[
            "amount"
        ].sum()
    )

    pending_payments = (
        invoices[
            invoices["status"]
            == "Pending"
        ]["amount"].sum()
    )

    paid_invoices = (
        invoices[
            invoices["status"]
            == "Paid"
        ]["amount"].sum()
    )

    total_budget = (
        budgets[
            "budget_amount"
        ].sum()
    )

    budget_utilization = (
        total_expenses
        /
        total_budget
        *
        100
        if total_budget > 0
        else 0
    )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Total Expenses",
            f"₹{total_expenses:,.0f}"
        )

    with col2:

        st.metric(
            "Pending Payments",
            f"₹{pending_payments:,.0f}"
        )

    with col3:

        st.metric(
            "Paid Invoices",
            f"₹{paid_invoices:,.0f}"
        )

    with col4:

        st.metric(
            "Budget Utilization",
            f"{budget_utilization:.1f}%"
        )

    st.divider()

    st.subheader(
        "📊 Expense Analysis"
    )

    left, right = st.columns(2)

    with left:

        st.markdown(
            "### 💰 Expense by Category"
        )

        if not filtered_expenses.empty:

            category_expenses = (
                filtered_expenses
                .groupby("category")[
                    "amount"
                ]
                .sum()
                .sort_values(
                    ascending=False
                )
            )

            st.bar_chart(
                category_expenses,
                use_container_width=True
            )

        else:

            st.info(
                "No expense data available."
            )

    with right:

        st.markdown(
            "### 🏢 Expense by Department"
        )

        if not filtered_expenses.empty:

            department_expenses = (
                filtered_expenses
                .groupby("department")[
                    "amount"
                ]
                .sum()
                .sort_values(
                    ascending=False
                )
            )

            st.bar_chart(
                department_expenses,
                use_container_width=True
            )

        else:

            st.info(
                "No expense data available."
            )

    st.divider()

    st.subheader(
        "📈 Monthly Expense Trend"
    )

    if not filtered_expenses.empty:

        monthly_expenses = (
            filtered_expenses.copy()
        )

        monthly_expenses[
            "expense_date"
        ] = pd.to_datetime(
            monthly_expenses[
                "expense_date"
            ],
            errors="coerce"
        )

        monthly_summary = (
            monthly_expenses
            .dropna(
                subset=[
                    "expense_date"
                ]
            )
            .assign(
                month=lambda df:
                df[
                    "expense_date"
                ]
                .dt
                .to_period("M")
                .astype(str)
            )
            .groupby("month")[
                "amount"
            ]
            .sum()
            .sort_index()
        )

        st.line_chart(
            monthly_summary,
            use_container_width=True
        )

    else:

        st.info(
            "No monthly expense data available."
        )

    st.divider()

    st.subheader(
        "⚠️ Budget Monitoring"
    )

    if budget_utilization >= 90:

        st.error(
            f"Critical: "
            f"{budget_utilization:.1f}% "
            "of the budget has been utilized."
        )

    elif budget_utilization >= 75:

        st.warning(
            f"Warning: "
            f"{budget_utilization:.1f}% "
            "of the budget has been utilized."
        )

    else:

        st.success(
            f"Budget utilization is healthy "
            f"at {budget_utilization:.1f}%."
        )

    st.divider()

    st.subheader(
        "📥 Export Report"
    )

    if not filtered_expenses.empty:

        csv_data = (
            filtered_expenses
            .to_csv(index=False)
            .encode("utf-8")
        )

        st.download_button(
            label="📥 Download Expense Report",
            data=csv_data,
            file_name=(
                "finops_expense_report.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )

    else:

        st.info(
            "No expense data available for export."
        )

    st.divider()

    st.subheader(
        "🚨 Smart Invoice Alerts"
    )

    today = pd.Timestamp(
        date.today()
    )

    overdue = invoices[
        (
            invoices["status"]
            == "Pending"
        )
        &
        (
            pd.to_datetime(
                invoices["due_date"]
            )
            < today
        )
    ]

    if not overdue.empty:

        st.error(
            f"🚨 {len(overdue)} "
            "overdue invoice(s) "
            "require immediate attention."
        )

        st.dataframe(
            overdue[
                [
                    "invoice_number",
                    "vendor_name",
                    "due_date",
                    "amount",
                    "status"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "✅ No overdue pending invoices."
        )

    st.divider()

    st.subheader(
        "📊 Spending Insights"
    )

    if not filtered_expenses.empty:

        category_spending = (
            filtered_expenses
            .groupby("category")[
                "amount"
            ]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        average_spending = (
            category_spending.mean()
        )

        if average_spending > 0:

            highest_category = (
                category_spending.idxmax()
            )

            highest_amount = (
                category_spending.max()
            )

            ratio = (
                highest_amount
                /
                average_spending
            )

            if ratio >= 1.5:

                st.warning(
                    f"⚠️ High spending detected "
                    f"in **{highest_category}**: "
                    f"₹{highest_amount:,.0f}. "
                    f"This is {ratio:.1f}× "
                    "the average category spending."
                )

            else:

                st.success(
                    "✅ Spending is distributed "
                    "normally across categories."
                )

            st.dataframe(
                category_spending
                .rename(
                    "Total Spending"
                )
                .to_frame()
                .style.format(
                    "₹{:,.0f}"
                ),
                use_container_width=True
            )

    else:

        st.info(
            "No expense data available."
        )

    st.divider()

    st.subheader(
        "💼 Financial Health Summary"
    )

    if budget_utilization >= 90:

        risk_level = "🔴 High Risk"

        recommendation = (
            "Budget utilization is very high. "
            "Review expenses and control "
            "additional spending."
        )

    elif budget_utilization >= 75:

        risk_level = "🟡 Moderate Risk"

        recommendation = (
            "Budget utilization is approaching "
            "the limit. Monitor spending carefully."
        )

    else:

        risk_level = "🟢 Low Risk"

        recommendation = (
            "Financial utilization is currently "
            "within a healthy range."
        )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Financial Risk Level",
            risk_level
        )

    with col2:

        st.metric(
            "Budget Remaining",
            f"₹{max(total_budget - total_expenses, 0):,.0f}"
        )

    st.info(
        f"💡 Recommendation: "
        f"{recommendation}"
    )


# ==================================================
# DASHBOARD
# ==================================================
else:

    st.title(
        "💰 FinOps360"
    )

    st.caption(
        "Finance & Operations Analytics Dashboard"
    )

    # --------------------------------------------------
    # APP USAGE ANALYTICS
    # --------------------------------------------------

    show_usage_analytics()

    # --------------------------------------------------
    # FINANCIAL DATA
    # --------------------------------------------------

    expenses = load_expenses()
    invoices = load_invoices()
    budgets = load_budgets()

    total_expenses = (
        expenses["amount"].sum()
    )

    pending_invoices = (
        invoices[
            invoices["status"]
            == "Pending"
        ]["amount"].sum()
    )

    paid_invoices = (
        invoices[
            invoices["status"]
            == "Paid"
        ]["amount"].sum()
    )

    total_budget = (
        budgets[
            "budget_amount"
        ].sum()
    )

    budget_utilization = (
        total_expenses
        /
        total_budget
        *
        100
        if total_budget > 0
        else 0
    )

    st.divider()

    # --------------------------------------------------
    # FINANCIAL KPI CARDS
    # --------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Total Expenses",
            f"₹{total_expenses:,.0f}"
        )

    with col2:

        st.metric(
            "Pending Invoices",
            f"₹{pending_invoices:,.0f}"
        )

    with col3:

        st.metric(
            "Paid Invoices",
            f"₹{paid_invoices:,.0f}"
        )

    with col4:

        st.metric(
            "Budget Utilization",
            f"{budget_utilization:.1f}%"
        )

    st.divider()

    # --------------------------------------------------
    # CHARTS
    # --------------------------------------------------

    left, right = st.columns(2)

    with left:

        st.subheader(
            "📊 Expense by Category"
        )

        if not expenses.empty:

            category_expenses = (
                expenses
                .groupby("category")[
                    "amount"
                ]
                .sum()
                .sort_values(
                    ascending=False
                )
            )

            st.bar_chart(
                category_expenses,
                use_container_width=True
            )

        else:

            st.info(
                "No expense data available."
            )

    with right:

        st.subheader(
            "🏢 Expense by Department"
        )

        if not expenses.empty:

            department_expenses = (
                expenses
                .groupby("department")[
                    "amount"
                ]
                .sum()
                .sort_values(
                    ascending=False
                )
            )

            st.bar_chart(
                department_expenses,
                use_container_width=True
            )

        else:

            st.info(
                "No expense data available."
            )

    st.divider()

    # --------------------------------------------------
    # INVOICE OVERVIEW
    # --------------------------------------------------

    st.subheader(
        "🧾 Invoice Overview"
    )

    if invoices.empty:

        st.info(
            "No invoices found."
        )

    else:

        invoice_display = invoices[
            [
                "invoice_number",
                "vendor_name",
                "invoice_date",
                "due_date",
                "amount",
                "status"
            ]
        ].copy()

        invoice_display["amount"] = (
            invoice_display["amount"]
            .apply(
                lambda x:
                f"₹{x:,.0f}"
            )
        )

        st.dataframe(
            invoice_display,
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # --------------------------------------------------
    # BUDGET VS ACTUAL
    # --------------------------------------------------

    st.subheader(
        "📊 Budget vs Actual"
    )

    if budgets.empty:

        st.info(
            "No budget data available."
        )

    else:

        actual = (
            expenses
            .groupby("category")[
                "amount"
            ]
            .sum()
            .rename("Actual")
        )

        budget = (
            budgets
            .groupby("category")[
                "budget_amount"
            ]
            .sum()
            .rename("Budget")
        )

        budget_analysis = pd.concat(
            [
                budget,
                actual
            ],
            axis=1
        ).fillna(0)

        budget_analysis[
            "Utilization %"
        ] = 0.0

        valid_budget = (
            budget_analysis[
                "Budget"
            ] > 0
        )

        budget_analysis.loc[
            valid_budget,
            "Utilization %"
        ] = (
            budget_analysis.loc[
                valid_budget,
                "Actual"
            ]
            /
            budget_analysis.loc[
                valid_budget,
                "Budget"
            ]
            *
            100
        )

        st.dataframe(
            budget_analysis.style.format(
                {
                    "Budget":
                        "₹{:,.0f}",
                    "Actual":
                        "₹{:,.0f}",
                    "Utilization %":
                        "{:.1f}%"
                }
            ),
            use_container_width=True
        )
