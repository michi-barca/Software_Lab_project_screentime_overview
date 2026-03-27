import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. SETUP & DESIGN
st.set_page_config(page_title="Screen Time Dashboard", layout="wide")

# Custom CSS für die "Karten"-Optik (optional, für den Profi-Look)
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# 2. HEADER
col_title, col_nav = st.columns([3, 1])
with col_title:
    st.title("Dashboard app")
with col_nav:
    st.write("")  # Abstand
    st.radio("", ["Tag", "Woche", "Monat"], horizontal=True, label_visibility="collapsed")

st.markdown("---")

# 3. KPI REIHE (Die 4 Karten oben)
# Hier arbeitet der "Data Engineer" an den Werten
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("Heute gesamt", "3h 24min", "+18 min vs gestern")
with kpi2:
    st.metric("Durchschnitt pro Tag", "2h 33min", "-12 min vs Vorwoche", delta_color="inverse")
with kpi3:
    st.metric("Entsperrungen", "47x", "+6 vs gestern")
with kpi4:
    st.metric("Limit-Streak", "5 Tage", "Ziel: 7 Tage", delta_color="off")

st.write("")  # Abstandhalter

# 4. DAS HAUPT-GRID (2 Spalten x 2 Zeilen)
row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)

# --- ZEILE 1: Täglich & Kategorien ---
with row1_col1:
    st.subheader("Tägliche Nutzung — diese Woche")
    # Beispiel-Daten für den Balken-Chart
    days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    usage = [120, 150, 80, 200, 180, 210, 190]
    fig_daily = px.bar(x=days, y=usage, color_discrete_sequence=['#4CAF50'])
    fig_daily.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_daily, use_container_width=True)

with row1_col2:
    st.subheader("Kategorien")
    # Doughnut Chart (Donut)
    labels = ['Social', 'Produktiv', 'Unterhaltung', 'Sonstiges']
    values = [40, 23, 22, 15]
    fig_donut = px.pie(names=labels, values=values, hole=0.7,
                       color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_donut.update_layout(height=300, showlegend=True)
    st.plotly_chart(fig_donut, use_container_width=True)

# --- ZEILE 2: Top Apps & Limit ---
with row2_col1:
    st.subheader("Top Apps heute")
    # Hier nutzen wir einfache Progress-Bars für den Look aus dem Bild
    apps = [("Instagram", 72, "1h 12m", "orange"), ("YouTube", 55, "55m", "blue"),
            ("WhatsApp", 41, "41m", "green"), ("TikTok", 34, "34m", "purple")]

    for app_name, val, time_str, color in apps:
        col_app, col_bar = st.columns([1, 3])
        col_app.write(f"**{app_name}**")
        col_bar.progress(val, text=time_str)

with row2_col2:
    st.subheader("Limit eingehalten")
    st.write("Ziel: max. 3h/Tag")
    # Hier könnte eine Heatmap oder eine einfache Tabelle mit farbigen Boxen hin
    st.info("💡 Diese Woche: 5/7 Tage das Limit eingehalten!")
    # Als Platzhalter für die grünen Boxen:
    st.write("🟩 🟩 ⬜ 🟩 🟩 🟩 🟩")

# Beispiel für die Logik in der app.py
user_options = ["Henning", "Michi", "Nils", "Alle"]
selected_user = st.sidebar.selectbox("User auswählen", user_options)

if selected_user == "Alle":
    st.header("👥 Team-Statistiken")

    # 1. Gesamtzeit aller User summieren
    total_team_time = df['Dauer_Minuten'].sum()
    st.metric("Team Gesamtzeit", f"{total_team_time // 60}h {total_team_time % 60}m")

    # 2. Vergleichs-Chart
    # Wir gruppieren nach User UND Datum
    team_compare = df.groupby(['User', 'Datum'])['Dauer_Minuten'].sum().reset_index()
    fig = px.line(team_compare, x='Datum', y='Dauer_Minuten', color='User', title="Wer nutzt wie viel?")
    st.plotly_chart(fig, use_container_width=True)

else:
    # Hier kommt euer bisheriger Code für den einzelnen User hin
    st.header(f"📱 Statistik für {selected_user}")
    user_df = df[df['User'] == selected_user]
    # ... Rest des Dashboards