from contextlib import contextmanager
from datetime import datetime
from html import escape
import os
from pathlib import Path
import sqlite3

import psycopg
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


st.set_page_config(
    page_title="Overload | Training log",
    page_icon="◎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MUSCLE_GROUPS = {
    "Chest": ["Barbell bench press", "Incline dumbbell press", "Cable fly"],
    "Back": ["Lat pulldown", "Barbell row", "Seated cable row"],
    "Shoulders": ["Overhead press", "Dumbbell lateral raise", "Face pull"],
    "Biceps": ["Dumbbell curl", "Barbell curl", "Hammer curl"],
    "Triceps": ["Triceps pushdown", "Overhead extension", "Close-grip bench press"],
    "Quads": ["Barbell squat", "Leg press", "Leg extension"],
    "Hamstrings": ["Romanian deadlift", "Leg curl", "Good morning"],
    "Glutes": ["Hip thrust", "Bulgarian split squat", "Cable kickback"],
    "Calves": ["Standing calf raise", "Seated calf raise"],
    "Core": ["Cable crunch", "Hanging leg raise", "Plank"],
}
DATABASE_PATH = Path(__file__).with_name("workouts.sqlite3")

try:
    DATABASE_URL = st.secrets.get("SUPABASE_DB_URL")
except StreamlitSecretNotFoundError:
    DATABASE_URL = None
DATABASE_URL = DATABASE_URL or os.environ.get("SUPABASE_DB_URL")


@contextmanager
def database_connection():
    if DATABASE_URL:
        with psycopg.connect(DATABASE_URL) as connection:
            yield connection
    else:
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            with connection:
                yield connection
        finally:
            connection.close()


def execute_query(connection, query, parameters=()):
    if DATABASE_URL:
        query = query.replace("?", "%s")
    return connection.execute(query, parameters)


def initialize_database():
    if DATABASE_URL:
        with database_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workout_sets (
                    id BIGSERIAL PRIMARY KEY,
                    exercise TEXT NOT NULL,
                    muscle_group TEXT NOT NULL,
                    weight DOUBLE PRECISION NOT NULL,
                    reps INTEGER NOT NULL,
                    logged_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_exercises (
                    id BIGSERIAL PRIMARY KEY,
                    muscle_group TEXT NOT NULL,
                    exercise TEXT NOT NULL,
                    UNIQUE (muscle_group, exercise)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS exercise_targets (
                    muscle_group TEXT NOT NULL,
                    exercise TEXT NOT NULL,
                    target_load DOUBLE PRECISION,
                    PRIMARY KEY (muscle_group, exercise)
                )
                """
            )
        return

    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workout_sets (
                id INTEGER PRIMARY KEY,
                exercise TEXT NOT NULL,
                muscle_group TEXT NOT NULL,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                logged_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS custom_exercises (
                id INTEGER PRIMARY KEY,
                muscle_group TEXT NOT NULL,
                exercise TEXT NOT NULL,
                UNIQUE (muscle_group, exercise)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS exercise_targets (
                muscle_group TEXT NOT NULL,
                exercise TEXT NOT NULL,
                target_load REAL,
                PRIMARY KEY (muscle_group, exercise)
            )
            """
        )
        target_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(exercise_targets)")
        }
        if "target_load" not in target_columns:
            connection.execute("ALTER TABLE exercise_targets ADD COLUMN target_load REAL")


initialize_database()
if not DATABASE_URL:
    st.warning(
        "Using local SQLite storage. For workout data that survives hosted-app "
        "restarts, add SUPABASE_DB_URL to the app's Streamlit secrets."
    )


def load_workout_sets():
    with database_connection() as connection:
        rows = execute_query(
            connection,
            "SELECT exercise, muscle_group, weight, reps, logged_at FROM workout_sets ORDER BY id"
        ).fetchall()
    return [
        {"exercise": row[0], "group": row[1], "weight": row[2], "reps": row[3], "date": row[4]}
        for row in rows
    ]


def load_custom_exercises():
    with database_connection() as connection:
        rows = execute_query(
            connection,
            "SELECT muscle_group, exercise FROM custom_exercises ORDER BY id"
        ).fetchall()
    for group, exercise in rows:
        MUSCLE_GROUPS.setdefault(group, []).append(exercise)


def load_exercise_targets():
    with database_connection() as connection:
        rows = execute_query(
            connection,
            "SELECT muscle_group, exercise, target_load FROM exercise_targets WHERE target_load IS NOT NULL"
        ).fetchall()
    return {(group, exercise): {"load": load} for group, exercise, load in rows}

load_custom_exercises()

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root {
      --ink: #172820;
      --muted: #657168;
      --paper: #f4f6f0;
      --green: #b6ef63;
      --line: #dce3d9;
      --surface: #ffffff;
      --orange: #f1784b;
    }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
    .stApp { background: var(--paper); }
    .block-container { max-width: 1120px; padding: 2.2rem 2.2rem 4rem; }
    #MainMenu, footer, header { visibility: hidden; }
    .brand-row { display:flex; align-items:center; justify-content:space-between; margin-bottom:2.8rem; }
    .brand { font-family:'Manrope',sans-serif; font-weight:800; letter-spacing:0; font-size:1rem; }
    .brand-mark { display:inline-grid; place-items:center; width:26px; height:26px; border-radius:8px; background:var(--green); margin-right:9px; font-size:17px; }
    .date-chip { font:500 .72rem 'DM Mono',monospace; text-transform:uppercase; color:var(--muted); letter-spacing:0; }
    .hero { display:flex; justify-content:space-between; gap:2rem; align-items:flex-end; margin-bottom:2.1rem; }
    .eyebrow { font:500 .7rem 'DM Mono',monospace; text-transform:uppercase; color:#69776d; margin-bottom:.7rem; }
    .hero h1 { font-family:'Manrope',sans-serif; font-size:clamp(2.3rem, 5vw, 4rem); line-height:.98; letter-spacing:0; margin:0; font-weight:800; }
    .hero h1 span { color:#77867b; font-weight:500; }
    .hero-note { max-width:230px; font-size:.9rem; line-height:1.5; color:var(--muted); margin-bottom:4px; }
    .stat-strip { display:grid; grid-template-columns:repeat(3,1fr); background:var(--ink); color:white; border-radius:12px; padding:1.2rem 1.5rem; margin-bottom:2.2rem; }
    .stat { padding:0 .7rem; border-right:1px solid #405047; }
    .stat:last-child {border:0;}
    .stat-label { font:400 .65rem 'DM Mono',monospace; text-transform:uppercase; color:#b7c1b9; margin-bottom:.4rem; }
    .stat-value { font:700 1.35rem 'Manrope',sans-serif; }
    .stat-value small { color:var(--green); font-size:.8rem; font-weight:500; }
    .section-head { display:flex; justify-content:space-between; align-items:baseline; margin:1.7rem 0 .8rem; }
    .section-head h2 {font:700 1.05rem 'Manrope',sans-serif; margin:0; letter-spacing:0;}
    .section-meta {font:400 .68rem 'DM Mono',monospace; color:var(--muted); text-transform:uppercase;}
    .latest-workout-card {background:var(--ink); color:white; border-radius:12px; padding:1.4rem 1.6rem; margin:0 0 1.6rem;}
    .latest-workout-head {display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin-bottom:1rem;}
    .latest-workout-kicker {font:500 .65rem 'DM Mono',monospace; color:var(--green); text-transform:uppercase; margin-bottom:.35rem;}
    .latest-workout-head h2 {font:700 1.45rem 'Manrope',sans-serif; color:white; margin:0; letter-spacing:0;}
    .latest-workout-date {font:400 .72rem 'DM Mono',monospace; color:#c5cec7;}
    .latest-workout-table {width:100%; border-collapse:collapse; font-size:.82rem;}
    .latest-workout-table thead th {font:400 .62rem 'DM Mono',monospace; color:#aab7ad; text-transform:uppercase; text-align:left; padding:.55rem .45rem; border-bottom:1px solid #405047;}
    .latest-workout-table thead th:first-child {width:28%;}
    .latest-workout-table td {padding:.58rem .45rem; border-bottom:1px solid #34443a; font:400 .78rem 'DM Mono',monospace; color:#f2f5ef;}
    .latest-workout-table .exercise-cell {font:700 .82rem 'Manrope',sans-serif; vertical-align:middle; overflow-wrap:anywhere;}
    .latest-workout-table .exercise-cell span {display:block; font:400 .64rem 'DM Mono',monospace; color:#aab7ad; margin-top:.2rem;}
    .latest-workout-table .target-cell {color:var(--green); white-space:normal; vertical-align:middle;}
    .latest-workout-empty {color:#c5cec7; font-size:.84rem; margin:.35rem 0 0;}
    .workout-panel { background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:1.3rem; }
    .exercise-name {font:700 1.25rem 'Manrope',sans-serif; letter-spacing:0; margin:.15rem 0 .3rem;}
    .exercise-sub {font-size:.8rem; color:var(--muted); margin-bottom:1rem;}
    .set-row {display:grid; grid-template-columns:36px 1fr 1fr 1fr; align-items:center; gap:.65rem; border-top:1px solid #edf0eb; padding:.7rem 0; font-size:.8rem;}
    .set-number {font:500 .68rem 'DM Mono',monospace; color:var(--muted);}
    .set-value {font:500 .8rem 'DM Mono',monospace;}
    .set-head {color:#68736b; font:400 .62rem 'DM Mono',monospace; text-transform:uppercase; padding-bottom:.45rem;}
    .empty-note {font-size:.82rem; color:var(--muted); padding:.8rem 0 .2rem;}
    .history-row {display:flex; justify-content:space-between; border-bottom:1px solid var(--line); padding:.8rem 0; font-size:.82rem;}
    .history-row:last-child {border-bottom:0;}
    .history-detail {color:var(--muted); font:400 .72rem 'DM Mono',monospace; margin-top:.2rem;}
    div[data-testid="stButton"] button {border-radius:8px; border:1px solid var(--line); min-height:42px; font-weight:600; color:var(--ink); background:white; transition:all .15s ease;}
    div[data-testid="stButton"] button:hover {border-color:var(--ink); color:var(--ink);}
    div[data-testid="stButton"] button[kind="primary"] {background:var(--green); border-color:var(--green); color:var(--ink);}
    div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input, div[data-testid="stSelectbox"] div[data-baseweb="select"] {border-radius:8px;}
    div[data-testid="stNumberInput"] button {min-height:unset;}
    div[data-testid="stTabs"] [role="tab"] {font-weight:600;}
    .st-key-muscle-groups [data-testid="stHorizontalBlock"] { flex-wrap:wrap; }
    .st-key-mobile-muscle-group-picker { display:none; }
    @media(max-width:700px) {
      .block-container {padding:1.1rem 1rem 3rem;}
      .brand-row {margin-bottom:2rem;}
      .hero {display:block; margin-bottom:1.5rem;}
      .hero-note {margin-top:.8rem; max-width:300px;}
      .stat-strip {padding:.9rem .35rem; margin-bottom:1.5rem;}
      .stat {padding:0 .55rem;}
      .stat-value {font-size:1rem;}
      .stat-value small {display:block; margin-top:2px;}
      .workout-panel {padding:1rem;}
      .set-row {grid-template-columns:28px 1fr 1fr 1fr; gap:.35rem;}
            .latest-workout-card {padding:1rem .8rem;}
            .latest-workout-table {table-layout:fixed;}
            .latest-workout-table th, .latest-workout-table td {padding:.45rem .25rem; font-size:.68rem;}
            .latest-workout-table .exercise-cell {font-size:.7rem;}
            .st-key-muscle-groups { display:none; }
            .st-key-mobile-muscle-group-picker { display:block; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "workout_sets" not in st.session_state:
    st.session_state.workout_sets = load_workout_sets()
if "selected_group" not in st.session_state:
    st.session_state.selected_group = "Biceps"
if "selected_exercise" not in st.session_state:
    st.session_state.selected_exercise = MUSCLE_GROUPS["Biceps"][0]
if "exercise_targets" not in st.session_state:
    st.session_state.exercise_targets = load_exercise_targets()

today = datetime.now().strftime("%A, %B %-d")
st.markdown(
    f"""
    <div class="brand-row">
      <div class="brand"><span class="brand-mark">↗</span>OVERLOAD</div>
      <div class="date-chip">{today}</div>
    </div>
    <div class="hero">
      <div><div class="eyebrow">Your training, moving forward</div>
      <h1>Earn the<br><span>next rep.</span></h1></div>
      <div class="hero-note">Small, consistent increases add up. Log your work and make your next session count.</div>
    </div>
    """,
    unsafe_allow_html=True,
)


def get_exercise_history(exercise, group=None):
    return [
        item for item in st.session_state.workout_sets
        if item["exercise"] == exercise and (group is None or item["group"] == group)
    ]


@st.fragment
def training_workspace():
    logged = st.session_state.workout_sets
    selected_group = st.session_state.selected_group
    today_key = datetime.now().strftime("%Y-%m-%d")
    today_sets = [item for item in logged if item["date"].startswith(today_key)]
    latest = logged[-1] if logged else None

    groups = list(MUSCLE_GROUPS)
    group_heading, add_exercise_control = st.columns([3, 1])
    with group_heading:
        st.markdown('<div class="section-head"><h2>Choose a muscle group</h2><span class="section-meta">Filter your log</span></div>', unsafe_allow_html=True)
    with add_exercise_control:
        with st.popover("＋ Add exercise", use_container_width=True):
            with st.form("add_exercise_form", clear_on_submit=True):
                new_group = st.selectbox(
                    "Muscle group",
                    groups,
                    index=groups.index(selected_group),
                    key="new_exercise_group",
                )
                new_exercise = st.text_input("Exercise name", key="new_exercise_name")
                add_exercise = st.form_submit_button("Add exercise", use_container_width=True)
            if add_exercise:
                new_exercise = new_exercise.strip()
                if not new_exercise:
                    st.warning("Enter an exercise name first.")
                elif any(existing.casefold() == new_exercise.casefold() for existing in MUSCLE_GROUPS[new_group]):
                    st.warning("That exercise is already in this muscle group.")
                else:
                    with database_connection() as connection:
                        execute_query(
                            connection,
                            "INSERT INTO custom_exercises (muscle_group, exercise) VALUES (?, ?)",
                            (new_group, new_exercise),
                        )
                    MUSCLE_GROUPS[new_group].append(new_exercise)
                    st.session_state.selected_group = new_group
                    st.session_state[f"exercise_{new_group}"] = new_exercise
                    st.session_state.selected_exercise = new_exercise
                    selected_group = new_group
                    st.success(f"Added {new_exercise} to {new_group}.")

    with st.container(key="mobile-muscle-group-picker"):
        mobile_group = st.selectbox(
            "Muscle group",
            groups,
            index=groups.index(selected_group),
            key=f"mobile_group_select_{selected_group}",
        )
    if mobile_group != selected_group:
        selected_group = mobile_group
        st.session_state.selected_group = mobile_group
        st.session_state.selected_exercise = MUSCLE_GROUPS[mobile_group][0]

    with st.container(key="muscle-groups"):
        for start in range(0, len(groups), 5):
            row = st.columns(5)
            for column, group in zip(row, groups[start : start + 5]):
                with column:
                    if st.button(
                        group,
                        key=f"group_{group}",
                        type="primary" if selected_group == group else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state.selected_group = group
                        st.session_state.selected_exercise = MUSCLE_GROUPS[group][0]
                        selected_group = group

    with st.expander(f"Set target load for {selected_group} exercises"):
        with st.form(f"target_form_{selected_group}"):
            target_exercise = st.selectbox(
                "Exercise",
                MUSCLE_GROUPS[selected_group],
                key=f"target_exercise_{selected_group}",
            )
            previous_sets = get_exercise_history(target_exercise, selected_group)
            previous_load = previous_sets[-1]["weight"] if previous_sets else 0.0
            current_target = st.session_state.exercise_targets.get(
                (selected_group, target_exercise), {"load": previous_load}
            )
            target_load = st.number_input(
                "Target load · kg",
                min_value=0.0,
                max_value=500.0,
                value=float(current_target["load"]),
                step=2.5,
                key=f"target_load_{selected_group}_{target_exercise}",
            )
            save_target = st.form_submit_button("Save target", use_container_width=True)
        if save_target:
            with database_connection() as connection:
                execute_query(
                    connection,
                    """
                    INSERT INTO exercise_targets (muscle_group, exercise, target_load)
                    VALUES (?, ?, ?)
                    ON CONFLICT (muscle_group, exercise) DO UPDATE SET
                        target_load = excluded.target_load
                    """,
                    (selected_group, target_exercise, target_load),
                )
            st.session_state.exercise_targets[(selected_group, target_exercise)] = {
                "load": target_load,
            }
            st.success(f"Target load saved for {target_exercise}.")

    group_sets = [item for item in logged if item["group"] == selected_group]
    if group_sets:
        latest_date = group_sets[-1]["date"][:10]
        latest_workout = [
            item for item in group_sets if item["date"].startswith(latest_date)
        ]
        exercises_in_workout = {}
        for item in latest_workout:
            exercises_in_workout.setdefault(item["exercise"], []).append(item)
        table_rows = []
        for exercise, sets in exercises_in_workout.items():
            target = st.session_state.exercise_targets.get(
                (selected_group, exercise)
            )
            if target is None:
                target_label = f"{sets[-1]['weight']:g} kg"
            else:
                target_label = f"{target['load']:g} kg"
            for index, item in enumerate(sets, start=1):
                exercise_cell = (
                    f'<td class="exercise-cell" rowspan="{len(sets)}">{escape(exercise)}'
                    f'<span>{escape(selected_group)}</span></td>'
                    if index == 1
                    else ""
                )
                target_cell = (
                    f'<td class="target-cell" rowspan="{len(sets)}">{target_label}</td>'
                    if index == 1
                    else ""
                )
                table_rows.append(
                    f'<tr>{exercise_cell}<td>Set {index}</td><td>{item["weight"]:g} kg</td>'
                    f'<td>{item["reps"]} reps</td>{target_cell}</tr>'
                )
        workout_content = (
            '<table class="latest-workout-table"><thead><tr><th>Exercise</th><th>Set</th><th>Load</th><th>Reps</th><th>Target load</th></tr></thead>'
            f'<tbody>{"".join(table_rows)}</tbody></table>'
        )
        workout_date = escape(latest_date)
    else:
        workout_content = f'<p class="latest-workout-empty">No {escape(selected_group)} sets logged yet.</p>'
        workout_date = "Ready when you are"
    st.markdown(
        f'<div class="latest-workout-card"><div class="latest-workout-head"><div><div class="latest-workout-kicker">{escape(selected_group)} training log</div><h2>Latest workout</h2></div><div class="latest-workout-date">{workout_date}</div></div>{workout_content}</div>',
        unsafe_allow_html=True,
    )

    if latest:
        load_label = f"{latest['weight']:g} kg <small>last logged</small>"
    else:
        load_label = "— <small>log your first set</small>"
    st.markdown(
        f"""
        <div class="stat-strip">
          <div class="stat"><div class="stat-label">Sets logged</div><div class="stat-value">{len(logged)}</div></div>
          <div class="stat"><div class="stat-label">Exercises today</div><div class="stat-value">{len({item['exercise'] for item in today_sets})}</div></div>
          <div class="stat"><div class="stat-label">Last working weight</div><div class="stat-value">{load_label}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-head"><h2>Build your session</h2><span class="section-meta">02 / log a set</span></div>', unsafe_allow_html=True)
    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        with st.container(border=True):
            exercise = st.selectbox(
                "Exercise",
                MUSCLE_GROUPS[st.session_state.selected_group],
                key=f"exercise_{st.session_state.selected_group}",
                label_visibility="collapsed",
            )
            st.session_state.selected_exercise = exercise
            exercise_sets = get_exercise_history(exercise)
            previous = exercise_sets[-1] if exercise_sets else None
            context = f"Last time: {previous['weight']:g} kg × {previous['reps']} reps" if previous else f"{st.session_state.selected_group} · New exercise"
            st.markdown(f'<div class="exercise-name">{escape(exercise)}</div><div class="exercise-sub">{context}</div>', unsafe_allow_html=True)
            st.markdown('<div class="set-row set-head"><span>SET</span><span>LOAD · KG</span><span>REPS</span><span>STATUS</span></div>', unsafe_allow_html=True)
            if exercise_sets:
                for index, item in enumerate(exercise_sets, start=1):
                    st.markdown(
                        f'<div class="set-row"><span class="set-number">{index:02}</span><span class="set-value">{item["weight"]:g} kg</span><span class="set-value">{item["reps"]}</span><span>✓</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div class="empty-note">Your working sets will show up here.</div>', unsafe_allow_html=True)

        st.write("")
        default_weight = float(previous["weight"]) if previous else 20.0
        default_reps = int(previous["reps"]) if previous else 8
        input_left, input_right = st.columns(2)
        with input_left:
            weight = st.number_input("Load · kg", min_value=0.0, max_value=500.0, value=default_weight, step=2.5, key=f"weight_{exercise}")
        with input_right:
            reps = st.number_input("Reps", min_value=1, max_value=100, value=default_reps, step=1, key=f"reps_{exercise}")
        if st.button("＋  Log set", type="primary", use_container_width=True, key="log_set"):
            entry = {"exercise": exercise, "group": st.session_state.selected_group, "weight": weight, "reps": reps, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
            with database_connection() as connection:
                execute_query(
                    connection,
                    "INSERT INTO workout_sets (exercise, muscle_group, weight, reps, logged_at) VALUES (?, ?, ?, ?, ?)",
                    (entry["exercise"], entry["group"], entry["weight"], entry["reps"], entry["date"]),
                )
            st.session_state.workout_sets.append(entry)

    with right:
        st.markdown('<div class="section-head" style="margin-top:0"><h2>Progress notes</h2><span class="section-meta">03 / history</span></div>', unsafe_allow_html=True)
        history = get_exercise_history(exercise)
        if history:
            for item in history[-5:][::-1]:
                st.markdown(
                    f'<div class="history-row"><div><strong>{escape(exercise)}</strong><div class="history-detail">{item["date"]}</div></div><div class="set-value">{item["weight"]:g} kg × {item["reps"]}</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="workout-panel"><div class="empty-note">Log your first set to start a history for this movement. Next time, your last load and reps will be ready to go.</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-head"><h2>Progression tip</h2></div>', unsafe_allow_html=True)
        st.markdown('<div class="workout-panel"><div class="empty-note" style="color:#172820">Hit your target reps with clean form? Add a small amount of weight next session. Keep the reps honest; progression is earned, not rushed.</div></div>', unsafe_allow_html=True)


training_workspace()
