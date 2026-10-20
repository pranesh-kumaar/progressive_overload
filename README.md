# Overload | Training log

Track workout sets, exercise targets, and training history.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://blank-app-template.streamlit.app/)

### Run locally

Prerequisite: install `uv` if you don't already have it.

```
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

1. Sync the dependencies

   ```
   $ uv sync
   ```

2. Run the app

   ```
   $ uv run streamlit run streamlit_app.py
   ```

### Deploy with persistent workout storage

The app uses SQLite locally. For workout logs that survive hosted-app restarts,
create a Supabase project and copy its PostgreSQL connection URI. In Streamlit
Community Cloud, open the app's **Settings → Secrets** and add:

```toml
SUPABASE_DB_URL = "postgresql://..."
```

Keep the real connection URI private; do not commit it. The app creates its
tables on first start and saves workout sets, custom exercises, and target loads
to Supabase. Without this secret, it uses local SQLite and displays a warning
that hosted storage may not persist.

The workout workspace uses a Streamlit fragment, so its interactions rerun the
workspace rather than the app's entire script. Workout records are written
directly to the database and are not stored in Streamlit's data cache.
