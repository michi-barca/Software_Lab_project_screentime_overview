import streamlit as st
import pandas as pd
import base64
import io
from datetime import date, timedelta
from github import Github, GithubException

# ── Konfiguration ────────────────────────────────────────────────
PERSONS = ["Anna", "Ben", "Clara"]  # ← Namen hier anpassen

KNOWN_APPS = sorted([
    "Amazon", "Apple Music", "BeReal", "Chrome", "Clash of Clans",
    "Discord", "Disney+", "Duolingo", "Facebook", "Gmail",
    "Google Maps", "HBO Max", "Instagram", "LinkedIn", "Maps",
    "Netflix", "Pinterest", "Reddit", "Safari", "Shazam",
    "Signal", "Snapchat", "Spotify", "Telegram", "TikTok",
    "Tinder", "Twitch", "Twitter", "WhatsApp", "YouTube",
])

CSV_COLUMNS = [
    "date", "person", "total_minutes",
    "app1_name", "app1_minutes",
    "app2_name", "app2_minutes",
    "app3_name", "app3_minutes",
]


# ── GitHub-Verbindung ─────────────────────────────────────────────

def get_repo():
    token = st.secrets["GITHUB_TOKEN"]
    repo_name = st.secrets["GITHUB_REPO"]
    g = Github(token)
    return g.get_repo(repo_name)


def load_csv_from_github(person: str) -> pd.DataFrame:
    """CSV einer Person aus GitHub laden. Gibt leeren DataFrame zurück wenn nicht vorhanden."""
    repo = get_repo()
    path = f"data/{person.lower()}.csv"
    try:
        file = repo.get_contents(path)
        content = base64.b64decode(file.content).decode("utf-8")
        df = pd.read_csv(io.StringIO(content), parse_dates=["date"])
        return df
    except GithubException:
        return pd.DataFrame(columns=CSV_COLUMNS)


def save_csv_to_github(person: str, df: pd.DataFrame) -> None:
    """DataFrame als CSV in GitHub speichern (erstellen oder überschreiben)."""
    repo = get_repo()
    path = f"data/{person.lower()}.csv"
    csv_content = df.to_csv(index=False)

    try:
        existing_file = repo.get_contents(path)
        repo.update_file(
            path=path,
            message=f"data: add entry for {person} on {date.today().isoformat()}",
            content=csv_content,
            sha=existing_file.sha,
        )
    except GithubException:
        repo.create_file(
            path=path,
            message=f"data: create {person.lower()}.csv",
            content=csv_content,
        )


# ── Hilfsfunktionen ──────────────────────────────────────────────

def normalize_app_name(name: str) -> str:
    name = name.strip()
    if not name:
        return name
    for known in KNOWN_APPS:
        if name.lower() == known.lower():
            return known
    return name[0].upper() + name[1:] if name else name


def validate_entry(
    person: str,
    entry_date: date,
    total_minutes: int,
    apps: list,
    existing_df: pd.DataFrame,
) -> list:
    errors = []

    if not existing_df.empty:
        already = existing_df[existing_df["date"].dt.date == entry_date]
        if not already.empty:
            errors.append(
                f"Für den {entry_date.strftime('%d.%m.%Y')} existiert bereits ein Eintrag. "
                "Lösche ihn zuerst weiter unten."
            )

    if total_minutes <= 0:
        errors.append("Gesamtzeit muss größer als 0 Minuten sein.")
    if total_minutes > 1440:
        errors.append("Gesamtzeit kann nicht mehr als 1440 Minuten (24 Std.) betragen.")

    for i, (app_name, app_min) in enumerate(apps, 1):
        if not app_name:
            errors.append(f"App {i}: Name darf nicht leer sein.")
        if app_min < 0:
            errors.append(f"App {i}: Minuten dürfen nicht negativ sein.")
        if total_minutes > 0 and app_min > total_minutes:
            errors.append(f"App {i} ({app_min} min) übersteigt die Gesamtzeit ({total_minutes} min).")

    app_sum = sum(m for _, m in apps)
    if total_minutes > 0 and app_sum > total_minutes:
        errors.append(
            f"Summe der Top-3-Apps ({app_sum} min) übersteigt "
            f"die Gesamtzeit ({total_minutes} min)."
        )

    mins = [m for _, m in apps]
    if mins[0] < mins[1] or mins[1] < mins[2]:
        errors.append(
            "Apps müssen nach Minuten absteigend sortiert sein "
            "(App 1 = meiste Minuten, App 3 = wenigste)."
        )

    names = [n.lower() for n, _ in apps if n]
    if len(names) != len(set(names)):
        errors.append("Jede App darf nur einmal eingetragen werden.")

    return errors


def append_entry(
    existing_df: pd.DataFrame,
    person: str,
    entry_date: date,
    total_minutes: int,
    apps: list,
) -> pd.DataFrame:
    """Neue Zeile zum bestehenden DataFrame hinzufügen und zurückgeben."""
    new_row = {
        "date": entry_date.isoformat(),
        "person": person,
        "total_minutes": total_minutes,
        "app1_name": apps[0][0],
        "app1_minutes": apps[0][1],
        "app2_name": apps[1][0],
        "app2_minutes": apps[1][1],
        "app3_name": apps[2][0],
        "app3_minutes": apps[2][1],
    }
    new_row_df = pd.DataFrame([new_row])
    if existing_df.empty:
        return new_row_df
    return pd.concat([existing_df, new_row_df], ignore_index=True)


def fmt_minutes(m: int) -> str:
    return f"{m // 60}h {m % 60}min" if m >= 60 else f"{m} min"


# ── Streamlit UI ─────────────────────────────────────────────────

st.set_page_config(
    page_title="Bildschirmzeit — Eingabe",
    page_icon="📱",
    layout="centered",
)

st.title("📱 Bildschirmzeit eintragen")
st.caption("Trage hier täglich deine Handy-Nutzungszeit ein.")

# ── 1. Person ─────────────────────────────────────────────────────
st.subheader("1 · Wer bist du?")
person = st.selectbox("Person", PERSONS, label_visibility="collapsed")

with st.spinner("Daten werden geladen..."):
    existing_df = load_csv_from_github(person)

already_today = (
    not existing_df.empty
    and (existing_df["date"].dt.date == date.today()).any()
)
if already_today:
    st.info("Du hast heute bereits eingetragen — scrolle nach unten zum Korrigieren.")

st.divider()

# ── 2. Datum ──────────────────────────────────────────────────────
st.subheader("2 · Datum")
entry_date = st.date_input(
    "Datum",
    value=date.today(),
    max_value=date.today(),
    min_value=date.today() - timedelta(days=7),
    help="Du kannst bis zu 7 Tage rückwirkend eintragen.",
    label_visibility="collapsed",
)

if not existing_df.empty:
    already = existing_df[existing_df["date"].dt.date == entry_date]
    if not already.empty:
        total_ex = int(already["total_minutes"].iloc[0])
        st.warning(
            f"Für den {entry_date.strftime('%d.%m.%Y')} existiert bereits ein Eintrag "
            f"({fmt_minutes(total_ex)}). Lösche ihn zuerst (ganz unten), "
            "bevor du neu einträgst."
        )

st.divider()

# ── 3. Gesamtzeit ─────────────────────────────────────────────────
st.subheader("3 · Gesamte Bildschirmzeit")
st.caption(
    "Den Wert findest du unter: "
    "Einstellungen → Bildschirmzeit (iOS) oder Digitales Wohlbefinden (Android)"
)

col_h, col_m = st.columns(2)
with col_h:
    hours_input = st.number_input("Stunden", min_value=0, max_value=23, value=1, step=1)
with col_m:
    mins_input = st.number_input("Minuten", min_value=0, max_value=59, value=30, step=1)

total_minutes = hours_input * 60 + mins_input

if total_minutes > 0:
    st.caption(f"= **{total_minutes} Minuten** gesamt")

st.divider()

# ── 4. Top-3-Apps ─────────────────────────────────────────────────
st.subheader("4 · Top 3 Apps")
st.caption(
    "Trage die drei meistgenutzten Apps ein — App 1 hat die meisten Minuten, App 3 die wenigsten."
)

apps = []
for i in range(1, 4):
    st.markdown(f"**App {i}**")
    col_name, col_min_h, col_min_m = st.columns([3, 1, 1])

    with col_name:
        options = ["— App wählen —"] + KNOWN_APPS + ["Andere App..."]
        choice = st.selectbox(f"App {i} Name", options, key=f"sel_{i}", label_visibility="collapsed")

        if choice == "Andere App...":
            raw = st.text_input(
                f"App {i} eingeben",
                key=f"custom_{i}",
                placeholder="z.B. Duolingo",
                label_visibility="collapsed",
            )
            app_name = normalize_app_name(raw)
        elif choice == "— App wählen —":
            app_name = ""
        else:
            app_name = choice

        if app_name and choice == "Andere App..." and app_name != raw.strip():
            st.caption(f"Wird gespeichert als: {app_name}")

    with col_min_h:
        st.caption("Std.")
        app_h = st.number_input("h", 0, 23, 0, key=f"app{i}_h", label_visibility="collapsed")
    with col_min_m:
        st.caption("Min.")
        app_m = st.number_input("m", 0, 59, 0, key=f"app{i}_m", label_visibility="collapsed")

    app_minutes = app_h * 60 + app_m
    apps.append((app_name, app_minutes))

    if app_minutes > 0:
        st.caption(f"= {app_minutes} Minuten")

if total_minutes > 0:
    app_sum = sum(m for _, m in apps)
    pct = min(app_sum / total_minutes, 1.0)
    unaccounted = total_minutes - app_sum
    st.progress(
        pct,
        text=f"Top-3 erfasst: {app_sum} min | Sonstige: {max(0, unaccounted)} min",
    )

st.divider()

# ── 5. Speichern ──────────────────────────────────────────────────
st.subheader("5 · Speichern")

if st.button("Eintrag speichern", type="primary", use_container_width=True):
    errors = validate_entry(person, entry_date, total_minutes, apps, existing_df)

    if errors:
        for err in errors:
            st.error(f"• {err}")
    else:
        with st.spinner("Wird in GitHub gespeichert..."):
            updated_df = append_entry(existing_df, person, entry_date, total_minutes, apps)
            save_csv_to_github(person, updated_df)

        st.success(
            f"Gespeichert! {person} · {entry_date.strftime('%d.%m.%Y')} · "
            f"{fmt_minutes(total_minutes)} · "
            f"{apps[0][0]} ({apps[0][1]} min), "
            f"{apps[1][0]} ({apps[1][1]} min), "
            f"{apps[2][0]} ({apps[2][1]} min)"
        )
        st.balloons()
        st.rerun()

st.divider()

# ── 6. Einträge ansehen & löschen ────────────────────────────────
with st.expander(f"Einträge von {person} ansehen & korrigieren"):
    fresh_df = load_csv_from_github(person)

    if fresh_df.empty:
        st.info("Noch keine Einträge vorhanden.")
    else:
        display = fresh_df.sort_values("date", ascending=False).copy()
        display["date"] = display["date"].dt.strftime("%d.%m.%Y")
        display["gesamt"] = display["total_minutes"].apply(fmt_minutes)
        display = display[[
            "date", "gesamt",
            "app1_name", "app1_minutes",
            "app2_name", "app2_minutes",
            "app3_name", "app3_minutes",
        ]]
        display.columns = [
            "Datum", "Gesamt",
            "App 1", "Min 1",
            "App 2", "Min 2",
            "App 3", "Min 3",
        ]
        st.dataframe(display, use_container_width=True, hide_index=True)

        st.markdown("**Eintrag löschen** (um ihn neu einzutragen)")
        dates_available = sorted(fresh_df["date"].dt.date.unique(), reverse=True)

        if dates_available:
            date_to_delete = st.selectbox(
                "Datum auswählen",
                options=dates_available,
                format_func=lambda d: d.strftime("%d.%m.%Y"),
                key="del_date",
            )
            if st.button("Eintrag löschen", type="secondary", key="del_btn"):
                with st.spinner("Wird gelöscht..."):
                    updated = fresh_df[fresh_df["date"].dt.date != date_to_delete].copy()
                    save_csv_to_github(person, updated)
                st.success(
                    f"Eintrag vom {date_to_delete.strftime('%d.%m.%Y')} gelöscht."
                )
                st.rerun()
