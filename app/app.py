"""
Dashboard — Vols et retards aériens US
Lit les agrégats gold depuis PostgreSQL.
"""

import os
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Connexion PostgreSQL ────────────────────────────────────────────
DB_PARAMS = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "flights"),
    "user": os.getenv("DB_USER", "dataviz"),
    "password": os.getenv("DB_PASSWORD", "dataviz123"),
}

CATEGORICAL_PALETTE = [
    "#3D7ADB", "#E5A030", "#2FAC91", "#D94E72",
    "#8B6CC1", "#C75C2A", "#4AABB3", "#8E8E8E",
]


@st.cache_data(ttl=600)
def run_query(query: str) -> pd.DataFrame:
    with psycopg2.connect(**DB_PARAMS) as conn:
        return pd.read_sql(query, conn)


# ── Config page ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Vols US — Dashboard",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Vols et retards aériens — États-Unis")
st.caption("Source : Bureau of Transportation Statistics (BTS) · 2023-2024")

# ── Filtres ──────────────────────────────────────────────────────────
st.sidebar.header("Filtres")

try:
    carriers = run_query(
        "SELECT DISTINCT carrier_name FROM gold_monthly_carrier ORDER BY carrier_name"
    )
    carrier_list = carriers["carrier_name"].tolist()
except Exception:
    carrier_list = []

selected_carriers = st.sidebar.multiselect(
    "Compagnies aériennes",
    options=carrier_list,
    default=carrier_list[:5] if carrier_list else [],
)

year_filter = st.sidebar.radio("Année", options=["Toutes", "2023", "2024"], index=0)

# ── Clause SQL filtres ───────────────────────────────────────────────
def where_clause(table_alias: str = "") -> str:
    prefix = f"{table_alias}." if table_alias else ""
    clauses = []
    if selected_carriers:
        names = ", ".join(f"'{c}'" for c in selected_carriers)
        clauses.append(f"{prefix}carrier_name IN ({names})")
    if year_filter != "Toutes":
        clauses.append(f"{prefix}year = {year_filter}")
    return "WHERE " + " AND ".join(clauses) if clauses else ""


# ── KPI ──────────────────────────────────────────────────────────────
st.markdown("---")

try:
    wc = where_clause()
    kpi = run_query(f"""
        SELECT
            ROUND(AVG(on_time_pct)::numeric, 1)   AS on_time,
            ROUND(AVG(avg_arr_delay)::numeric, 1)  AS avg_delay,
            ROUND(AVG(cancel_pct)::numeric, 2)     AS cancel_rate,
            SUM(total_flights)                      AS total_flights
        FROM gold_monthly_carrier
        {wc}
    """)
    row = kpi.iloc[0]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🎯 Taux de ponctualité", f"{row['on_time']} %")
    k2.metric("⏱️ Retard moyen arrivée", f"{row['avg_delay']} min")
    k3.metric("❌ Taux d'annulation", f"{row['cancel_rate']} %")
    k4.metric("🛫 Total vols", f"{int(row['total_flights']):,}".replace(",", " "))
except Exception as e:
    st.warning(f"Impossible de charger les KPI. Vérifiez que le pipeline gold a été exécuté. ({e})")
    st.stop()

# ── Graphique 1 : Évolution mensuelle de la ponctualité ─────────────
st.markdown("---")
st.subheader("📈 Contexte — Évolution mensuelle de la ponctualité")
st.markdown(
    "Ce graphique montre l'évolution du taux de ponctualité mois par mois. "
    "Les creux saisonniers (été, fêtes) révèlent les périodes critiques."
)

try:
    wc = where_clause()
    monthly = run_query(f"""
        SELECT year, month,
               ROUND(AVG(on_time_pct)::numeric, 1) AS on_time_pct,
               SUM(total_flights) AS total_flights
        FROM gold_monthly_carrier
        {wc}
        GROUP BY year, month
        ORDER BY year, month
    """)
    monthly["period"] = monthly.apply(
        lambda r: f"{int(r['year'])}-{int(r['month']):02d}", axis=1
    )

    fig1 = px.line(
        monthly, x="period", y="on_time_pct",
        labels={"period": "Mois", "on_time_pct": "Ponctualité (%)"},
        markers=True,
    )
    fig1.update_traces(line_color=CATEGORICAL_PALETTE[0], line_width=2, marker_size=6)
    fig1.update_layout(
        yaxis_range=[50, 100],
        hovermode="x unified",
        margin=dict(l=40, r=20, t=20, b=40),
        plot_bgcolor="white",
    )
    fig1.update_xaxes(showgrid=False)
    fig1.update_yaxes(gridcolor="#E8E8E8", gridwidth=1)
    st.plotly_chart(fig1, use_container_width=True)
except Exception as e:
    st.error(f"Erreur graphique mensuel : {e}")

# ── Graphique 2 : Retard moyen par compagnie ────────────────────────
st.markdown("---")
st.subheader("📊 Constat — Retard moyen par compagnie")
st.markdown(
    "Classement des compagnies par retard moyen à l'arrivée. "
    "Les compagnies en haut du classement sont celles qui pénalisent le plus les passagers."
)

try:
    wc = where_clause()
    by_carrier = run_query(f"""
        SELECT carrier_name,
               ROUND(AVG(avg_arr_delay)::numeric, 1) AS avg_delay,
               SUM(total_flights) AS flights
        FROM gold_monthly_carrier
        {wc}
        GROUP BY carrier_name
        ORDER BY avg_delay DESC
        LIMIT 15
    """)

    fig2 = px.bar(
        by_carrier, x="avg_delay", y="carrier_name",
        orientation="h",
        labels={"avg_delay": "Retard moyen (min)", "carrier_name": "Compagnie"},
        text="avg_delay",
    )
    fig2.update_traces(
        marker_color=CATEGORICAL_PALETTE[3],
        textposition="outside",
        texttemplate="%{text} min",
    )
    fig2.update_layout(
        yaxis=dict(autorange="reversed"),
        margin=dict(l=20, r=60, t=20, b=40),
        plot_bgcolor="white",
    )
    fig2.update_xaxes(showgrid=True, gridcolor="#E8E8E8")
    fig2.update_yaxes(showgrid=False)
    st.plotly_chart(fig2, use_container_width=True)
except Exception as e:
    st.error(f"Erreur graphique compagnies : {e}")

# ── Graphique 3 : Causes de retard ──────────────────────────────────
st.markdown("---")
st.subheader("🔍 Analyse — Répartition des causes de retard")
st.markdown(
    "Comprendre la part de chaque cause permet d'identifier les leviers d'action : "
    "la compagnie peut agir sur ses propres retards, mais pas sur la météo."
)

try:
    wc = where_clause()
    causes = run_query(f"""
        SELECT
            ROUND(AVG(pct_carrier_delay)::numeric, 1)       AS "Compagnie",
            ROUND(AVG(pct_weather_delay)::numeric, 1)       AS "Météo",
            ROUND(AVG(pct_nas_delay)::numeric, 1)           AS "Contrôle aérien",
            ROUND(AVG(pct_security_delay)::numeric, 1)      AS "Sécurité",
            ROUND(AVG(pct_late_aircraft_delay)::numeric, 1) AS "Avion en retard"
        FROM gold_delay_causes
        {wc}
    """)
    causes_melted = causes.melt(var_name="Cause", value_name="Part (%)")

    fig3 = px.bar(
        causes_melted, x="Cause", y="Part (%)",
        color="Cause",
        color_discrete_sequence=CATEGORICAL_PALETTE,
        text="Part (%)",
    )
    fig3.update_traces(textposition="outside", texttemplate="%{text}%")
    fig3.update_layout(
        showlegend=False,
        margin=dict(l=40, r=20, t=20, b=40),
        plot_bgcolor="white",
    )
    fig3.update_xaxes(showgrid=False)
    fig3.update_yaxes(showgrid=True, gridcolor="#E8E8E8")
    st.plotly_chart(fig3, use_container_width=True)
except Exception as e:
    st.error(f"Erreur graphique causes : {e}")

# ── Graphique 4 : Top 10 routes les plus en retard ──────────────────
st.markdown("---")
st.subheader("🗺️ Recommandation — Routes à surveiller")
st.markdown(
    "Ces routes cumulent volume élevé et retards fréquents. "
    "Ce sont les priorités d'optimisation pour améliorer la ponctualité globale."
)

try:
    top_routes = run_query("""
        SELECT origin || ' → ' || dest AS route,
               total_flights,
               ROUND(avg_arr_delay::numeric, 1) AS avg_delay,
               ROUND(on_time_pct::numeric, 1) AS on_time_pct
        FROM gold_routes
        ORDER BY total_flights * (100 - on_time_pct) DESC
        LIMIT 10
    """)

    fig4 = px.scatter(
        top_routes, x="total_flights", y="avg_delay",
        size="total_flights", text="route",
        labels={
            "total_flights": "Nombre de vols",
            "avg_delay": "Retard moyen (min)",
        },
        color_discrete_sequence=[CATEGORICAL_PALETTE[2]],
    )
    fig4.update_traces(textposition="top center", marker=dict(opacity=0.7))
    fig4.update_layout(
        margin=dict(l=40, r=20, t=20, b=40),
        plot_bgcolor="white",
    )
    fig4.update_xaxes(showgrid=True, gridcolor="#E8E8E8")
    fig4.update_yaxes(showgrid=True, gridcolor="#E8E8E8")
    st.plotly_chart(fig4, use_container_width=True)
except Exception as e:
    st.error(f"Erreur graphique routes : {e}")

# ── Footer ───────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Données : Bureau of Transportation Statistics (BTS) — "
    "Reporting Carrier On-Time Performance · 2023-2024"
)
