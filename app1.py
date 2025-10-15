import os
import streamlit as st
from supabase import create_client, Client
from typing import List, Dict
from datetime import datetime

# -----------------------
# Config / client setup
# -----------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DEFAULT_USER_ID = os.environ.get("DEFAULT_USER_ID", "user_1")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Set SUPABASE_URL and SUPABASE_KEY as environment variables.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------
# Utility helpers
# -----------------------
@st.cache_data(show_spinner=False)
def fetch_series(limit=100):
    resp = supabase.table("series").select("*").limit(limit).execute()
    return resp.data or []

@st.cache_data(show_spinner=False)
def fetch_series_by_id(series_id):
    resp = supabase.table("series").select("*").eq("id", series_id).single().execute()
    return resp.data

@st.cache_data(show_spinner=False)
def fetch_watchparties(limit=100):
    resp = supabase.table("watchparties").select("*").limit(limit).execute()
    return resp.data or []

@st.cache_data(show_spinner=False)
def fetch_users():
    resp = supabase.table("users").select("*").execute()
    return resp.data or []

@st.cache_data(show_spinner=False)
def fetch_platforms():
    resp = supabase.table("series_platform").select("*").execute()
    return resp.data or []

@st.cache_data(show_spinner=False)
def fetch_ratings_for_series(series_id):
    resp = supabase.table("ratings").select("*").eq("series_id", series_id).execute()
    return resp.data or []

def create_watchparty(series_id: int, host: str, time_iso: str, platforms: str, participants: List[str]):
    payload = {
        "series_id": series_id,
        "host": host,
        "time": time_iso,
        "platforms": platforms
    }
    res = supabase.table("watchparties").insert(payload).execute()
    if res.error:
        return False, res.error
    wp = res.data[0]
    wp_id = wp.get("watchparty_id") or wp.get("id")  # depends on schema
    # insert participants rows
    for p in participants:
        supabase.table("participants").insert({
            "watchparty_id": wp_id,
            "participant": p
        }).execute()
    # clear caches
    fetch_watchparties.clear()
    return True, wp

def add_participant_to_watchparty(watchparty_id: int, participant_id: str):
    res = supabase.table("participants").insert({
        "watchparty_id": watchparty_id,
        "participant": participant_id
    }).execute()
    fetch_watchparties.clear()
    return res

def add_rating(user_id: str, series_id: int, stars: int, review: str = "", status: str = "watched"):
    payload = {
        "user_id": user_id,
        "series_id": series_id,
        "stars": stars,
        "review": review,
        "status": status
    }
    res = supabase.table("ratings").insert(payload).execute()
    fetch_ratings_for_series.clear()
    return res

def add_to_watchlist(user_id: str, series_id: int):
    return add_rating(user_id, series_id, stars=None, review="", status="watchlist")

# -----------------------
# UI
# -----------------------
st.set_page_config(page_title="WatchParty - prototype", layout="wide")
st.markdown("<h1 style='margin-bottom:0.2rem'>WatchParty — prototype</h1>", unsafe_allow_html=True)
st.write("Sketch-driven prototype connected to Supabase")

# Sidebar (profile / navigation)
with st.sidebar:
    st.header("Profile")
    users = fetch_users()
    user = next((u for u in users if u.get("user_id") == DEFAULT_USER_ID), None)
    if user:
        st.subheader(user.get("name", DEFAULT_USER_ID))
    else:
        st.subheader(DEFAULT_USER_ID)
    st.write("Quick links")
    page = st.radio("", ["Home", "Series", "Watch Parties", "Trending", "Platforms", "My Watchlist"])

# Home Overview
if page == "Home":
    st.subheader("Your watchlists & quick actions")
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### Trending now")
        series = fetch_series(limit=20)
        # simple trending: highest rating or recent
        sorted_trend = sorted(series, key=lambda s: (s.get("rating") or 0), reverse=True)[:10]

        for s in sorted_trend:
            st.markdown(f"**{s.get('name')}** — {s.get('genre')} — {s.get('year')}")
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("Details", key=f"home_details_{s.get('id')}"):
                    st.session_state["open_series"] = s.get("id")
                    page = "Series"
                    st.experimental_rerun()
            with c2:
                st.write(f"Rating: {s.get('rating') or '—'}")

    with col2:
        st.markdown("### Create quick watch party")
        series_list = fetch_series(limit=200)
        series_names = {str(s.get("id")): s.get("name") for s in series_list}
        sel = st.selectbox("Series", options=list(series_names.keys()), format_func=lambda x: series_names[x])
        dt = st.datetime_input("Date & time", value=datetime.now())
        platform = st.text_input("Platform (e.g. Netflix)")
        invited = st.text_input("Invite participants (comma separated user_id)")
        if st.button("Create"):
            ok, wp = create_watchparty(int(sel), DEFAULT_USER_ID, dt.isoformat(), platform, [p.strip() for p in invited.split(",") if p.strip()])
            if ok:
                st.success("Watch party created")
            else:
                st.error(f"Error: {wp}")

# Series grid and details
if page == "Series":
    st.header("Series catalogue")
    series = fetch_series(limit=200)

    # optional direct open if clicked from other pages
    series_to_open = st.session_state.get("open_series", None)
    if series_to_open:
        selected_series = fetch_series_by_id(series_to_open)
    else:
        # simple grid
        grid_cols = st.columns(4)
        for i, s in enumerate(series):
            c = grid_cols[i % 4]
            with c:
                st.markdown(f"### {s.get('name')}")
                st.write(f"{s.get('genre')} • {s.get('year')}")
                st.write(f"Episodes: {s.get('episodes') or '-'}")
                if st.button("Open", key=f"open_{s.get('id')}"):
                    selected_series = fetch_series_by_id(s.get('id'))
                    st.session_state["open_series"] = s.get('id')
                    st.experimental_rerun()
        selected_series = None

    if selected_series:
        st.markdown("---")
        st.subheader(selected_series.get("name"))
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**Genre:** {selected_series.get('genre')}")
            st.markdown(f"**Year:** {selected_series.get('year')}")
            st.markdown(f"**Episodes:** {selected_series.get('episodes')}")
            st.markdown(f"**Platform:** {selected_series.get('platform') or '—'}")
            st.markdown(f"**Aggregated rating:** {selected_series.get('rating') or '—'}")
            st.markdown("### Community reviews")
            reviews = fetch_ratings_for_series(selected_series.get("id"))
            if not reviews:
                st.write("No reviews yet.")
            else:
                for r in reviews:
                    u = next((uu for uu in users if uu.get("user_id") == r.get("user_id")), {})
                    st.write(f"- **{u.get('name', r.get('user_id'))}** — {r.get('stars') or '-'} ★: {r.get('review') or ''}")

            st.markdown("### Actions")
            if st.button("Add to my watchlist"):
                res = add_to_watchlist(DEFAULT_USER_ID, selected_series.get("id"))
                if res.error:
                    st.error("Could not add to watchlist")
                else:
                    st.success("Added to watchlist")
        with col2:
            st.markdown("### Rate this series")
            stars = st.slider("Stars", 0, 5, 4)
            review_text = st.text_area("Review", height=120)
            if st.button("Submit rating"):
                res = add_rating(DEFAULT_USER_ID, selected_series.get("id"), stars, review_text, status="watched")
                if res.error:
                    st.error("Could not submit rating")
                else:
                    st.success("Thanks for the rating!")
                    fetch_ratings_for_series.clear()

# Watch Parties page
if page == "Watch Parties":
    st.header("Watch Parties")
    wps = fetch_watchparties()
    if not wps:
        st.info("No watch parties yet.")
    else:
        for wp in wps:
            series_obj = fetch_series_by_id(wp.get("series_id")) if wp.get("series_id") else {}
            st.markdown(f"**{series_obj.get('name','—')}** hosted by {wp.get('host')} — {wp.get('time')}")
            participants_resp = supabase.table("participants").select("*").eq("watchparty_id", wp.get("watchparty_id") or wp.get("id")).execute()
            participants = participants_resp.data or []
            st.write("Participants:", ", ".join([p.get("participant") for p in participants]) or "—")
            if st.button("Join", key=f"join_{wp.get('watchparty_id')}"):
                add_participant_to_watchparty(wp.get("watchparty_id") or wp.get("id"), DEFAULT_USER_ID)
                st.experimental_rerun()

    st.markdown("---")
    st.subheader("Create a watch party")
    all_series = fetch_series(limit=200)
    series_map = {str(s.get("id")): s.get("name") for s in all_series}
    sel_series = st.selectbox("Series", options=list(series_map.keys()), format_func=lambda x: series_map[x])
    host_dt = st.datetime_input("Date & time", value=datetime.now())
    platform = st.text_input("Platform")
    participants_input = st.text_input("Invite participants (comma sep user_id)")
    if st.button("Create watch party (full form)"):
        ok, wp = create_watchparty(int(sel_series), DEFAULT_USER_ID, host_dt.isoformat(), platform, [p.strip() for p in participants_input.split(",") if p.strip()])
        if ok:
            st.success("Watch party created.")
        else:
            st.error(f"Error creating: {wp}")

# Trending page
if page == "Trending":
    st.header("Trending & Recommendations")
    series = fetch_series(limit=200)
    top_rated = sorted(series, key=lambda s: (s.get("rating") or 0), reverse=True)[:8]
    st.subheader("Top rated")
    cols = st.columns(4)
    for i, s in enumerate(top_rated):
        c = cols[i % 4]
        with c:
            st.markdown(f"**{s.get('name')}**")
            st.write(f"{s.get('rating') or '—'} ★")

    st.markdown("---")
    st.subheader("Your friends' activity (recent ratings)")
    recent_ratings = supabase.table("ratings").select("*").order("id", desc=True).limit(10).execute().data or []
    for r in recent_ratings:
        u = next((uu for uu in users if uu.get("user_id") == r.get("user_id")), {})
        s = fetch_series_by_id(r.get("series_id")) or {}
        st.write(f"{u.get('name','Unknown')} rated {s.get('name','—')} — {r.get('stars') or '-'}")

# Platforms page
if page == "Platforms":
    st.header("Platforms")
    plats = fetch_platforms()
    st.write("Available platforms")
    for p in plats:
        name = p.get("platform")
        st.markdown(f"### {name}")
        res = supabase.table("series").select("*").ilike("platform", f"%{name}%").limit(50).execute()
        for s in (res.data or []):
            st.write(f"- {s.get('name')} ({s.get('year')})")

# My Watchlist page
if page == "My Watchlist":
    st.header("My Watchlist / My ratings")
    my_ratings = supabase.table("ratings").select("*").eq("user_id", DEFAULT_USER_ID).execute().data or []
    watchlist = [r for r in my_ratings if r.get("status") == "watchlist"]
    watched = [r for r in my_ratings if r.get("status") == "watched"]

    st.subheader("To watch")
    for r in watchlist:
        s = fetch_series_by_id(r.get("series_id"))
        st.write(f"- {s.get('name')}")
        if st.button(f"Mark watched {r.get('series_id')}", key=f"mark_{r.get('id')}"):
            # turn status to watched by inserting new rating (simple approach)
            add_rating(DEFAULT_USER_ID, r.get("series_id"), stars=4, review="", status="watched")
            st.experimental_rerun()

    st.subheader("Watched")
    for r in watched:
        s = fetch_series_by_id(r.get("series_id"))
        st.write(f"- {s.get('name')} — {r.get('stars') or '-'} ★ — {r.get('review') or ''}")
