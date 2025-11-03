import os
import streamlit as st
from supabase import create_client, Client
from typing import List
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()


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
def fetch_series_by_id(id):
    resp = supabase.table("series").select("*").eq("id", id).limit(1).execute()
    return resp.data[0] if resp.data else None

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
    resp = supabase.table("series_platform").select("platform").execute()
    plats = list({r["platform"] for r in (resp.data or [])})
    return plats

@st.cache_data(show_spinner=False)
def fetch_ratings_for_series(id):
    resp = supabase.table("ratings").select("*").eq("id", id).execute()
    return resp.data or []

def create_watchparty(id: int, host: str, time_iso: str, platforms: str, participants: List[str]):
    payload = {
        "id": id,
        "host": host,
        "time": time_iso,
        "platforms": platforms
    }
    res = supabase.table("watchparties").insert(payload).execute()
    if res.error:
        return False, res.error
    wp = res.data[0]
    wp_id = wp.get("watchparty_id") or wp.get("id")
    for p in participants:
        supabase.table("participants").insert({
            "watchparty_id": wp_id,
            "participant": p
        }).execute()
    fetch_watchparties.clear()
    return True, wp

def add_participant_to_watchparty(watchparty_id: int, participant_id: str):
    res = supabase.table("participants").insert({
        "watchparty_id": watchparty_id,
        "participant": participant_id
    }).execute()
    fetch_watchparties.clear()
    return res

def remove_participant_from_watchparty(watchparty_id: int, participant_id: str):
    """Elimina al usuario de una watchparty si ya está dentro"""
    res = supabase.table("participants").delete()\
        .eq("watchparty_id", watchparty_id)\
        .eq("participant", participant_id)\
        .execute()
    fetch_watchparties.clear()
    return res


def add_rating(user_id: str, id: int, stars: int, review: str = "", status: str = "watched"):
    payload = {
        "user_id": user_id,
        "id": id,
        "stars": stars,
        "review": review,
        "status": status
    }
    res = supabase.table("ratings").insert(payload).execute()
    fetch_ratings_for_series.clear()
    return res


def add_to_watchlist(user_id: str, id: int):
    return add_rating(user_id, id, stars=None, review="", status="watchlist")

SERIES_IMAGES = {
    "How I Met Your Mother": "https://disney.images.edge.bamgrid.com/ripcut-delivery/v2/variant/disney/559b4b05-9c8e-4e19-89d2-30a74febb0c0/compose?aspectRatio=1.78&format=webp&width=1200",
    "Suits ": "https://image-cdn.netflixjunkie.com/wp-content/uploads/imago0141810645h-scaled-e1693036504112.jpg",
    "The Big Bang Theory ": "https://beam-images.warnermediacdn.com/BEAM_LWM_DELIVERABLES/c8ea8e19-cae7-4683-9b62-cdbbed744784/914da85b-244a-11ef-8e04-12093494333d?host=wbd-images.prod-vod.h264.io&partner=beamcom",
    "New Girl ": "https://adictasromantica.com/wp-content/uploads/2018/01/new-girl.jpg?w=640",
    "Brooklyn 99": "https://i.blogs.es/397810/brooklyn-99-temporada-8/650_1200.jpeg",
    "Community ": "https://encrypted-tbn1.gstatic.com/images?q=tbn:ANd9GcTPuFUIZ_IOYN8XQzLL0XXcKT7j-JbnqFcOUCUw-h6EyIupeJeIqDCECItir7yldkLCHiBj1w",
    "The O.C.": "https://beam-images.warnermediacdn.com/BEAM_LWM_DELIVERABLES/893e4fea-3137-44c7-a6ab-9f6ee9914981/4b51289ba9bbdeae7cf80ca1f7bbf3b7eea6a4d3.jpg?host=wbd-images.prod-vod.h264.io&partner=beamcom&w=500",
    "The Flash ": "https://ntvb.tmsimg.com/assets/p10781465_b_h8_ay.jpg?w=960&h=540g",
    "Supergirl ": "https://film-book.com/wp-content/uploads/2021/02/supergirl-season-six-tv-show-poster-01-700x400-1.jpg",
    "WandaVision": "https://disney.images.edge.bamgrid.com/ripcut-delivery/v2/variant/disney/44f18e37-cce7-4813-b407-fc8d2ebe3f60/compose?aspectRatio=1.78&format=webp&width=1200",
    "Yellowstone": "https://www.mlive.com/resizer/v2/LOGYPARDQBCKDML2IIH5ESOIGI.jpg?auth=06545d3a992e72cb2da7aa4566c7965ecd5806936e71a13329850544269079b6&width=800&smart=true&quality=90",
    "The Office (US)": "https://resizing.flixster.com/KHP8WIWqGr-3MmT1Sa9GvDtb3Q8=/fit-in/705x460/v2/https://resizing.flixster.com/-XZAfHZM39UwaGJIFWKAE8fS0ak=/v3/t/assets/p185008_b_h9_ac.jpg",
    "The Summer I Turned Pretty": "https://m.media-amazon.com/images/S/pv-target-images/4a68ee50fe8a1fb1147ad9fca8d2c48e4c86c8243397c3d687e54a3e1bfcf322.png",
    "The Bear": "https://s10019.cdn.ncms.io/wp-content/uploads/2024/05/The-Bear.png",
    "Gilmore Girls ": "https://beam-images.warnermediacdn.com/BEAM_LWM_DELIVERABLES/72bd8235-6bf8-41ef-bc78-14e0f7292c73/76f121d1-fb04-11ef-93b6-12953788022d?host=wbd-images.prod-vod.h264.io&partner=beamcom"
}
def get_image_for_series(name: str) -> str:
    return SERIES_IMAGES.get(name, "https://via.placeholder.com/300x450?text=No+Image")


# -----------------------
# UI
# -----------------------
st.set_page_config(page_title="ScreenMates", layout="wide")
st.markdown("""
<style>
/* Fondo general */
body, .stApp {
    background-color: #0e1117;
    color: #f5f5f5;
    font-family: 'Inter', sans-serif;
}

/* Títulos */
h1, h2, h3, h4 {
    color: #ff6b6b;
}

/* Botones */
.stButton>button {
    background-color: #c91a4f;
    color: white;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    border: none;
    transition: 0.2s;
}
.stButton>button:hover {
    background-color: #63b3ed;
}

/* Inputs */
.stTextInput>div>div>input, .stTextArea>div>textarea {
    border-radius: 6px;
    border: 1px solid #444;
    background-color: #1a1c22;
    color: #fff;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #161a20;
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='margin-bottom:0.2rem'>ScreenMates </h1>", unsafe_allow_html=True)


# Sidebar
with st.sidebar:
    st.header("Perfil")
    users = fetch_users()
    user = next((u for u in users if u.get("user_id") == DEFAULT_USER_ID), None)
    if user:
        st.subheader(user.get("name", DEFAULT_USER_ID))
    else:
        st.subheader(DEFAULT_USER_ID)

    st.write("Pestañas")
    default_page = st.session_state.get("page", "Home")
    pages = ["Home", "Series", "Watch Parties", "Trending", "Plataformas", "Mi Watchlist", "Party Lobby"]

# Si la página actual no existe en la lista (por ejemplo, Party Lobby), usamos "Home" por defecto
    default_page = st.session_state.get("page", "Home")
    if default_page not in pages:
        default_page = "Home"

    page = st.radio(
        "",
        pages,
        index=pages.index(default_page)
    )
st.session_state["page"] = page

#-----------------------
#Home Overview FORMA GRID
#-----------------------

if page == "Home": 
    st.subheader("Mis watchlists y acciones rápidas") 
    col1, col2 = st.columns([3, 1])

    # 🔹 Trending Section 
    with col1: 
        st.markdown("## 🎬 En tendencia") 
        series = fetch_series(limit=20) 
        sorted_trend = sorted(series, key=lambda s: (s.get("rating") or 0), reverse=True)[:15]
       

        # 💠 Estilos del grid
        st.markdown("""
        <style>
        .series-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
          gap: 20px;
          margin-top: 1rem;
        }
        .series-item {
          background-color: #1a1c22;
          border-radius: 12px;
                aspect-ratio: 7 / 3;
                    width:500px;
          text-align: center;
                
          padding: 12px;
          box-shadow: 0 0 8px rgba(0,0,0,0.4);
          transition: transform 0.25s ease;
            width: 380px;
        }
        .series-item:hover {
          transform: translateY(-5px);
        }
        .series-item img {
          width: 100%;
          border-radius: 12px;
          height: 290px;
          object-fit: cover;
                    display: block;
                    align-items: center;
        }
        .series-item h4 {
          color: #ff6b6b;
          margin: 0.4rem 0 0.2rem;
          font-size: 1rem;
        }
        .series-item p {
          color: #bbb;
          margin: 0;
          font-size: 0.85rem;
        }
        </style>
        """, unsafe_allow_html=True)






        # 💠 Contenedor del grid
        st.markdown("<div class='series-grid'>", unsafe_allow_html=True)
        

        for s in sorted_trend:
            name = s.get("name", "Serie sin nombre")
            img_url = get_image_for_series(name)
            genre = s.get("genre", "—")
            year = s.get("year", "—")
            rating = s.get("rating", "—")
            series_id = s.get("id")

            

            st.markdown(
        f"""
        <div class='series-item'>
            <img src="{img_url}" alt="{name}">
            <h4>{name}</h4>
            <p>{genre} • {year}</p>
            <p>⭐ {rating}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
            if st.button("Ver detalles", key=f"details_{series_id}"):
                st.session_state["open_series"] = series_id
                st.session_state["page"] = "Series"
                st.rerun()



        st.markdown("</div>", unsafe_allow_html=True)
        
    

    # 🔹 Quick Watchparty Form 
    with col2: 
        st.markdown("### 🍿 Crea una watch party") 
        series_list = fetch_series(limit=200) 
        series_names = {str(s.get("id")): s.get("name") for s in series_list} 
        sel = st.selectbox("Series", options=list(series_names.keys()), format_func=lambda x: series_names[x])

        date = st.date_input("Fecha", value=datetime.now().date()) 
        time = st.time_input("Hora", value=datetime.now().time()) 
        dt = datetime.combine(date, time)

        platform = st.text_input("Plataforma (ej. Netflix)") 
        invited = st.text_input("Invita participantes (user_id separados con coma)") 
        if st.button("Crear watchparty"): 
            ok, wp = create_watchparty(int(sel), DEFAULT_USER_ID, dt.isoformat(), platform, [p.strip() for p in invited.split(",") if p.strip()]) 
            if ok: 
                st.success("Watchparty creada!✅") 
            else: 
                st.error(f"Error creando watchparty: {wp}")


# -----------------------
# Series catalogue
# -----------------------
if page == "Series":
    st.header("Catálogo de Series")

    selected_series = None
    series = fetch_series(limit=200)
    users = fetch_users()

    # Si hay una serie abierta (guardada en session_state)
    series_to_open = st.session_state.get("open_series", None)
    if series_to_open:
        selected_series = fetch_series_by_id(series_to_open)

    # Detalles de serie
    if selected_series:
        st.markdown("---")
        st.subheader(selected_series.get("name"))
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"*Género:* {selected_series.get('genre', '—')}")
            st.markdown(f"*Año:* {selected_series.get('year', '—')}")
            st.markdown(f"*Episodios:* {selected_series.get('episodes', '—')}")
            st.markdown(f"*Plataformas:* {', '.join([p['platform'] for p in (supabase.table('series_platform').select('platform').eq('id', selected_series.get('id')).execute().data or [])]) or '—'}")
            st.markdown(f"*Rating promedio:* {selected_series.get('rating', '—')}")

            st.markdown("### Reseñas de la comunidad")
            reviews = fetch_ratings_for_series(selected_series.get("id"))
            if not reviews:
                st.write("No hay reseñas todavía.")
            else:
                for r in reviews:
                    u = next((uu for uu in users if uu.get("user_id") == r.get("user_id")), {})
                    st.write(f"- *{u.get('name', r.get('user_id'))}* — {r.get('stars') or '-'} ★: {r.get('review') or ''}")

            st.markdown("### Acciones")
            if st.button("Agregar a mi watchlist"):
                # 🧹 Eliminar cualquier registro previo de esa serie para este usuario
                supabase.table("ratings") \
                    .delete() \
                    .eq("user_id", DEFAULT_USER_ID) \
                    .eq("id", selected_series.get("id")) \
                    .execute()

                # 💾 Insertar nuevamente con estado "watchlist"
                res = supabase.table("ratings").insert({
                    "user_id": DEFAULT_USER_ID,
                    "id": selected_series.get("id"),
                    "stars": None,
                    "review": "",
                    "status": "watchlist"
                }).execute()

                if not res or getattr(res, "error", None):
                    st.error("No se pudo agregar a la watchlist")
                else:
                    st.success("Agregada a la watchlist correctamente")
        


            if st.button("⬅ Volver al catálogo"):
                if "open_series" in st.session_state:
                    del st.session_state["open_series"]
                st.rerun()

        with col2:
            st.markdown("### Calificar esta serie")
            stars = st.slider("Estrellas", 0, 10, 4)
            review_text = st.text_area("Reseña", height=120)
            if st.button("Enviar reseña"):
                supabase.table("ratings") \
                    .delete() \
                    .eq("user_id", DEFAULT_USER_ID) \
                    .eq("id", selected_series.get("id")) \
                    .execute()
                res = add_rating(
                    DEFAULT_USER_ID,
                    selected_series.get("id"),
                    stars,
                    review_text,
                    status="watched"
                )
                if not res or getattr(res, "error", None):
                    st.error("No se pudo enviar la reseña")
                else:
                    st.success("¡Gracias por tu reseña!")
                    fetch_ratings_for_series.clear()



    # Catálogo
    else:
        if st.button("🏠 Volver al Home"):
            st.session_state["page"] = "Home"
            st.query_params["page"] = "Home"
            st.rerun()

        # 💅 Estilos tipo Netflix pero con tamaño fijo
        st.markdown("""
        <style>
        /* ======= GRID ======= */
        .series-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(260px, 0px)); /* ancho fijo */
          justify-content: center; /* centra el grid horizontalmente */
          gap: 28px;
          margin-top: 2rem;
        }

        /* ======= CARD ======= */
        .series-card {
          position: relative;
          width: 650px;       /* ancho fijo */
          height: 430px;      /* alto fijo */
          border-radius: 12px;
          overflow: hidden;
          background-color: #1a1c22;
          box-shadow: 0 4px 10px rgba(0,0,0,0.3);
          transition: transform 0.25s ease, box-shadow 0.25s ease;
          flex-shrink: 0;
        }

        .series-card:hover {
          transform: scale(1.05);
          box-shadow: 0 8px 20px rgba(0,0,0,0.6);
        }

        /* ======= IMAGEN ======= */
        .series-card img {
          width: 100%;
          height: 100%;
          object-fit: cover; /* mantiene proporción */
          border-radius: 12px;
          transition: opacity 0.25s ease, transform 0.25s ease;
        }

        /* ======= OVERLAY ======= */
        .series-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.75);
          opacity: 0;
          transition: opacity 0.3s ease;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          padding: 10px;
          text-align: center;
        }

        .series-card:hover .series-overlay {
          opacity: 1;
        }

        .series-overlay h4 {
          color: #fff;
          font-size: 1rem;
          margin-bottom: 6px;
        }

        .series-overlay p {
          color: #bbb;
          font-size: 0.85rem;
          margin: 0;
        }

        /* ======= BOTÓN ======= */
        .details-btn {
          background-color: #ff2e63;
          color: white;
          border: none;
          border-radius: 8px;
          padding: 0.5rem 1rem;
          margin-top: 10px;
          cursor: pointer;
          transition: background 0.25s ease;
        }

        .details-btn:hover {
          background-color: #63b3ed;
        }
        </style>
        """, unsafe_allow_html=True)

        # 💠 Grilla principal
        st.markdown("<div class='series-grid'>", unsafe_allow_html=True)

        for s in series:
            name = s.get("name", "Sin nombre")
            genre = s.get("genre", "—")
            year = s.get("year", "—")
            rating = s.get("rating", "—")
            episodes = s.get("episodes", "—")
            img = get_image_for_series(name)
            series_id = s.get("id")

            st.markdown(
                f"""
                <div class="series-card">
                    <img src="{img}" alt="{name}">
                    <div class="series-overlay">
                        <h4>{name}</h4>
                        <p>{genre} • {year}</p>
                        <p>⭐ {rating} — {episodes} episodios</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # 🔹 Botón Streamlit real debajo de la card
            if st.button(f"Ver detalles de {name}", key=f"open_{series_id}"):
                st.session_state["open_series"] = series_id
                st.session_state["page"] = "Series"
                st.query_params["page"] = "Series"
                st.query_params["series_id"] = str(series_id)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# -----------------------
# Watch Parties
# -----------------------
if page == "Watch Parties":
    st.header("🍿 Watch Parties")
    wps = fetch_watchparties()

    if not wps:
        st.info("No hay watch parties todavía.")
    else:
        # 🎨 CSS para las tarjetas
        st.markdown("""
        <style>
        .wp-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
          gap: 20px;
          margin-top: 1.5rem;
        }
        .wp-card {
          background-color: #1a1c22;
          border-radius: 10px;
          padding: 16px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.4);
          transition: transform 0.25s ease;
        }
        .wp-card:hover {
          transform: translateY(-4px);
        }
        .wp-title {
          color: #ff6b6b;
          font-weight: 600;
          margin-bottom: 4px;
        }
        .wp-details {
          color: #ddd;
          font-size: 0.9rem;
        }
        .wp-participants {
          color: #bbb;
          font-size: 0.85rem;
          margin-top: 8px;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("<div class='wp-grid'>", unsafe_allow_html=True)
        for wp in wps:
            # Obtener el ID de la watchparty
            wp_id = wp.get("watchparty_id") or wp.get("id")

            # 1️⃣ Obtener la serie asociada a la watchparty
            series_id = wp.get("series")
            series_obj = {}
            if series_id:
                series_resp = supabase.table("series").select("name").eq("id", series_id).execute()
                if series_resp.data:
                    series_obj = series_resp.data[0]

            # 2️⃣ Obtener el nombre del anfitrión (host)
            host_username = wp.get("host")
            if host_username:
                host_resp = supabase.table("users").select("name").eq("user_id", wp.get("host")).execute()
                if host_resp.data:
                    host_username = host_resp.data[0].get("name")

            # 3️⃣ Obtener los participantes (convertir user_id → username)
            participants_resp = supabase.table("participants").select("*").eq("watchparty_id", wp_id).execute()
            participants = [p.get("participant") for p in (participants_resp.data or [])]

            usernames = []
            if participants:
                users_resp = supabase.table("users").select("user_id, name").in_("user_id", participants).execute()
                usernames = [u.get("name") for u in (users_resp.data or [])]

            # 4️⃣ Mostrar la card
            with st.container():
                st.markdown(f"""
                <div class='wp-card'>
                    <div class='wp-title'>{series_obj.get('name','(No title)')}</div>
                    <div class='wp-details'>Anfitrión: <b>{host_username or '—'}</b></div>
                    <div class='wp-details'>🕒 {wp.get('time') or '—'}</div>
                    <div class='wp-participants'>👥 Participantes: {', '.join(usernames) or '—'}</div>
                </div>
                """, unsafe_allow_html=True)

                # 🧩 Si el usuario ya está en la party
                if DEFAULT_USER_ID in participants:
                    st.success("✅ Ya estás en esta party!")

                    c1, c2 = st.columns([1, 1])
                    with c1:
                        if st.button(f"Ingresa el Lobby 🎬", key=f"enter_{wp_id}"):
                            st.session_state["page"] = "Party Lobby"
                            st.session_state["open_party"] = wp_id
                            st.rerun()
                    with c2:
                        if st.button(f"Dejar ❌", key=f"leave_{wp_id}"):
                            remove_participant_from_watchparty(wp_id, DEFAULT_USER_ID)
                            st.success("Dejaste la party 👋")
                            st.rerun()

                # 🧩 Si NO está en la party todavía
                else:
                    if st.button("Unirse", key=f"join_{wp_id}"):
                        ok, err = add_participant_to_watchparty(wp_id, DEFAULT_USER_ID)
                        if ok:
                            st.success("Te uniste de manera exitosa! ✅")
                            st.rerun()
                        else:
                            st.warning(err or "Ya estás en esta party.")
        
        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------
# Party Lobby
# -----------------------
if page == "Party Lobby":
    wp_id = st.session_state.get("open_party", None)

    if not wp_id:
        st.warning("No hay party seleccionada. Ingresa el lobby en la sección de Watch Parties.")
    else:
        # 🔹 Buscar la watchparty
        wp = None
        for key in ["watchparty_id", "id"]:
            try:
                res = supabase.table("watchparties").select("*").eq(key, wp_id).execute()
                if res.data:
                    wp = res.data[0]
                    break
            except Exception:
                continue

        if not wp:
            st.error("❌ No se encontró esta Watch Party en la base de datos.")
        else:
            # ✅ Buscar la serie asociada correctamente
            series_obj = {}
            series_id = wp.get("series")
            if series_id:
                s_res = supabase.table("series").select("name").eq("id", series_id).execute()
                if s_res.data:
                    series_obj = s_res.data[0]

            # ✅ Obtener nombre del anfitrión
            host_username = wp.get("host")
            if host_username:
                host_res = supabase.table("users").select("name").eq("user_id", wp.get("host")).execute()
                if host_res.data:
                    host_username = host_res.data[0].get("name")

            # ✅ Obtener nombres de los participantes
            participants_resp = supabase.table("participants").select("participant").eq("watchparty_id", wp_id).execute()
            participant_ids = [p.get("participant") for p in (participants_resp.data or [])]

            participant_names = []
            if participant_ids:
                users_res = supabase.table("users").select("user_id, name").in_("user_id", participant_ids).execute()
                participant_names = [u.get("name") for u in (users_res.data or [])]

            # 🖥️ Mostrar datos
            st.header(f"🎬 Watch Party — {series_obj.get('name', '(No title)')}")
            st.markdown(f"**Anfitrión:** {host_username or '—'}")
            st.markdown(f"**Hora:** {wp.get('time', '—')}")
            st.markdown(f"**Plataforma:** {wp.get('platforms', '—')}")
            st.markdown(f"**Participantes:** {', '.join(participant_names) or '—'}")

            if st.button("⬅ Volver a Watch Parties"):
                del st.session_state["open_party"]
                st.session_state["page"] = "Watch Parties"
                st.rerun()

# -----------------------
# Trending
# -----------------------
if page == "Trending":
    st.header("🔥 Trending & Recomendaciones")

    series = fetch_series(limit=200)
    users = fetch_users()
    top_rated = sorted(series, key=lambda s: (s.get("rating") or 0), reverse=True)[:10]
    recent_ratings = supabase.table("ratings").select("*").order("id", desc=True).limit(10).execute().data or []

    # 🎨 CSS para el diseño dividido
    st.markdown("""
    <style>
    .trend-container {
        display: grid;
        grid-template-columns: 1.5fr 1fr;
        gap: 30px;
        margin-top: 1.5rem;
    }
    .trend-card, .friends-card {
        background-color: #1a1c22;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    }
    .trend-title {
        color: #ff6b6b;
        font-weight: 700;
        font-size: 1.4rem;
        margin-bottom: 1rem;
    }
    .series-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #2a2d33;
        transition: background 0.2s ease;
    }
    .series-item:hover {
        background: rgba(255,255,255,0.03);
    }
    .series-name {
        color: #f1f1f1;
        font-weight: 600;
    }
    .series-meta {
        color: #aaa;
        font-size: 0.85rem;
    }
    .series-rating {
        color: #ffd43b;
        font-weight: 600;
    }
    .friend-item {
        border-bottom: 1px solid #2a2d33;
        padding: 6px 0;
        font-size: 0.9rem;
    }
    .friend-name {
        color: #63b3ed;
        font-weight: 500;
    }
    .friend-series {
        color: #f5f5f5;
        font-weight: 500;
    }
    .friend-stars {
        color: #ffd43b;
        margin-left: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    # 🧱 Contenedor principal
    st.markdown("<div class='trend-container'>", unsafe_allow_html=True)

    # 🔹 COLUMNA IZQUIERDA – Top Rated
    st.markdown("<div class='trend-card'>", unsafe_allow_html=True)
    st.markdown("<div class='trend-title'>⭐ Top Ratings</div>", unsafe_allow_html=True)

    for s in top_rated:
        st.markdown(f"""
        <div class='series-item'>
            <div>
                <div class='series-name'>{s.get("name", "—")}</div>
                <div class='series-meta'>{s.get("genre","—")} • {s.get("year","—")}</div>
            </div>
            <div class='series-rating'>⭐ {s.get("rating","—")}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # 🔹 COLUMNA DERECHA – Friends' Picks
    st.markdown("<div class='friends-card'>", unsafe_allow_html=True)
    st.markdown("<div class='trend-title'>👥 Favoritas de tus amigos</div>", unsafe_allow_html=True)

    if not recent_ratings:
        st.markdown("<p style='color:#bbb;'>Sin ratings recientes.</p>", unsafe_allow_html=True)
    else:
        for r in recent_ratings:
            u = next((uu for uu in users if uu.get("user_id") == r.get("user_id")), {})
            s = fetch_series_by_id(r.get("id")) or {}
            stars = "★" * int(r.get("stars") or 0)
            st.markdown(f"""
            <div class='friend-item'>
                <span class='friend-name'>{u.get('name','Unknown')}</span> rated 
                <span class='friend-series'>{s.get('name','—')}</span>
                <span class='friend-stars'>{stars}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------
# Platforms
# -----------------------
if page == "Plataformas":
    st.header("Plataformas")
    st.write("💡Platformas disponibles")

    plats = fetch_platforms()

    # 💅 Estilos visuales
    st.markdown("""
    <style>
    .platform-container {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 40px;
      margin-top: 2rem;
    }

    .platform-card {
      background-color: #1a1c22;
      border-radius: 14px;
      padding: 1.2rem 1.5rem;
      box-shadow: 0 4px 12px rgba(0,0,0,0.35);
      transition: transform 0.25s ease, box-shadow 0.25s ease;
                gap: 40px;
    }

    .platform-card:hover {
      transform: translateY(-5px);
      box-shadow: 0 8px 20px rgba(0,0,0,0.55);
    }

    .platform-title {
      font-size: 1.3rem;
      font-weight: 600;
      margin-bottom: 0.8rem;
      color: #ff6b6b;
    }

    .platform-list {
      list-style: none;
      padding-left: 0;
      margin: 0;
    }

    .platform-list li {
      color: #ddd;
      font-size: 0.95rem;
      margin: 0.3rem 0;
    }

    .platform-list li::before {
      content: "🎬 ";
      opacity: 0.8;
    }

    /* Colores temáticos por plataforma */
    .PrimeVideo .platform-title { color: #00a8e1; }
    .DisneyPlus .platform-title { color: #006ce0; }
    .Netflix .platform-title { color: #e50914; }
    .HBO .platform-title { color: #6f42c1; }
    .MercadoPlay .platform-title { color: #ffb300; }

    </style>
    """, unsafe_allow_html=True)

    # 💠 Contenedor de plataformas
    st.markdown("<div class='platform-container'>", unsafe_allow_html=True)

    for name in plats:
        try:
            # Series en esta plataforma
            ids_res = supabase.table("series_platform").select("id").eq("platform", name).execute()
            ids = [r["id"] for r in (ids_res.data or [])]

            if ids:
                series_res = supabase.table("series").select("*").in_("id", ids).execute()
                series_list = series_res.data or []

                # Bloque HTML
                st.markdown(
                    f"""
                    <div class='platform-card {name.replace(' ', '').replace('+','Plus')}'>
                        <div class='platform-title'>{name}</div>
                        <ul class='platform-list'>
                            {''.join([f"<li>{s.get('name')} ({s.get('year')})</li>" for s in series_list])}
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        except Exception as e:
            st.error(f"Error cargando platforma {name}: {e}")

    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------
# My Watchlist
# -----------------------
if page == "Mi Watchlist":
    st.header("Mi Watchlist / Mis ratings")
    my_ratings = supabase.table("ratings").select("*").eq("user_id", DEFAULT_USER_ID).execute().data or []
    watchlist = [r for r in my_ratings if r.get("status") == "watchlist"]
    watched = [r for r in my_ratings if r.get("status") == "watched"]

    st.subheader("Pendientes")
    for r in watchlist:
        s = fetch_series_by_id(r.get("id"))
        st.write(f"- {s.get('name')}")

        if st.button(f"Marcar como vista", key=f"mark_{r.get('id')}"):
            # 🔹 Eliminar primero el registro con status="watchlist"
            supabase.table("ratings") \
                .delete() \
                .eq("user_id", DEFAULT_USER_ID) \
                .eq("id", r.get("id")) \
                .eq("status", "watchlist") \
                .execute()

            # 🔹 Luego agregar la serie como vista
            add_rating(DEFAULT_USER_ID, r.get("id"), stars=7, review="", status="watched")

            st.rerun()


    st.subheader("Vistas")
    for r in watched:
        s = fetch_series_by_id(r.get("id"))
        st.write(f"- {s.get('name')} — {r.get('stars') or '-'} ★ — {r.get('review') or ''}")