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
# -----------------------
# Config / client setup
# -----------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
# ID inicial (fijo)
INITIAL_USER_ID = os.environ.get("DEFAULT_USER_ID", "U1")

# Inicializar estado de usuario si no existe
if "current_user_id" not in st.session_state:
    st.session_state["current_user_id"] = INITIAL_USER_ID

# ⚠️ CLAVE: Ahora DEFAULT_USER_ID cambia según lo que elijas en el dropdown
DEFAULT_USER_ID = st.session_state["current_user_id"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if "show_tutorial" not in st.session_state:
    st.session_state["show_tutorial"] = True  # Activado por defecto

def show_page_guide(page_name):
    """Muestra una guía descartable específica para cada página"""
    
    # Si el usuario desactivó el tutorial, no mostrar nada
    if not st.session_state.get("show_tutorial"):
        return

    # Diccionario con el contenido de ayuda por página
    guides = {
        "Home": """
            ### 🏠 Bienvenido al Home
            - **Izquierda:** Mira las series que son tendencia hoy.
            - **Derecha:** Crea una nueva *Watch Party*. Selecciona la serie, la fecha y tus amigos.
            - **Tip:** ¡Si la serie tiene plataformas cargadas, aparecerán en un menú desplegable!
        """,
        "Series": """
            ### 🔎 Catálogo de Series
            - **Filtros:** Usa los controles superiores para buscar por género, año o cantidad de episodios.
            - **Detalles:** Haz clic en "Ver detalles" para ver la sinopsis, plataformas y reseñas.
            - **Acciones:** Desde el detalle puedes agregar series a tu *Watchlist* o dejar tu propia reseña.
        """,
        "Watch Parties": """
            ### 🍿 Tus Eventos
            - Aquí verás todas las watchparties programadas.
            - **Unirse:** Si te invitaron, verás un botón para confirmar asistencia.
            - **Lobby:** Cuando llegue la hora, entra al "Lobby" para ver quiénes están conectados.
        """,
        "Plataformas": """
            ### 📺 Dónde ver
            - Explora el catálogo filtrado por servicios de streaming (Netflix, Disney+, etc.).
            - Haz clic en una plataforma para ver qué series están disponibles allí.
        """,
        "Party Lobby": """
            ### 🛋️ Sala de Espera (Lobby)
            - Aquí es donde se reúnen antes de dar "Play".
            - Verifica que todos tus amigos estén en la lista de "Participantes en sala".
        """,
        "Trending": """
            ### 🎞️ Series en tendencia
            - Aquí podrás ver las series mejor rateadas y las favoritos de tus amigos.
            - Encuentra las reseñas que compartieron y las series que les gustaron.
        """,
        "Mi Watchlist": """
            ### 📝 Qué ver a continuación
            - Lleva registro de tus series pendientes, ratealas, o márcalas como vista.
            - No hace falta perderse en un mar de series por ver, están todas aquí.
        """
    }

    content = guides.get(page_name)
    
    if content:
        with st.info("💡 Guía rápida (puedes ocultar esto en el menú lateral)"):
            col_text, col_btn = st.columns([4, 1])
            with col_text:
                st.markdown(content)
            with col_btn:
                if st.button("Entendido, ocultar guías", key=f"close_{page_name}"):
                    st.session_state["show_tutorial"] = False
                    st.rerun()
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
    resp = supabase.table("series").select("platforms").execute()
    data = resp.data or []
    unique_plats = set()
    for row in data:
        if row.get("platforms"): 
            for p in row["platforms"]:
                unique_plats.add(p)
                
    return sorted(list(unique_plats))

@st.cache_data(show_spinner=False)
def fetch_ratings_for_series(id):
    resp = supabase.table("ratings").select("*").eq("id", id).execute()
    return resp.data or []

def create_watchparty(series_id: int, host: str, time_iso: str, platforms: str, participants: List[str]):
    try:
        res_ids = supabase.table("watchparties").select("watchparty_id").execute()
        all_ids = [r["watchparty_id"] for r in (res_ids.data or [])]
        
        max_num = 0
        for wid in all_ids:
            try:
                num = int(wid.replace("W", ""))
                if num > max_num: max_num = num
            except:
                continue
        
        new_id = f"W{max_num + 1}"

        clean_participants = list(participants) if participants else []

        payload = {
            "watchparty_id": new_id,
            "series": series_id,
            "host": host,
            "time": time_iso,
            "platforms": platforms,
            "participants": clean_participants 
        }

        res = supabase.table("watchparties").insert(payload).execute()

        if hasattr(res, 'error') and res.error:
            return False, f"Supabase Error: {res.error}"
            
        return True, res.data[0]

    except Exception as e:
        return False, f"Python Error: {str(e)}"

def add_participant_to_watchparty(watchparty_id: str, participant_id: str):
    current_wp = supabase.table("watchparties").select("participants").eq("watchparty_id", watchparty_id).single().execute()
    current_list = current_wp.data.get("participants") or []

    if participant_id not in current_list:
        current_list.append(participant_id)

        res = supabase.table("watchparties").update({"participants": current_list}).eq("watchparty_id", watchparty_id).execute()
        fetch_watchparties.clear()
        return True, None
    else:
        return False, "User already in party"

def remove_participant_from_watchparty(watchparty_id: str, participant_id: str):
    current_wp = supabase.table("watchparties").select("participants").eq("watchparty_id", watchparty_id).single().execute()
    current_list = current_wp.data.get("participants") or []
    
    if participant_id in current_list:
        current_list.remove(participant_id)

        res = supabase.table("watchparties").update({"participants": current_list}).eq("watchparty_id", watchparty_id).execute()
        fetch_watchparties.clear()
        return res
    return None

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
    
    current_user_obj = next((u for u in users if u.get("user_id") == DEFAULT_USER_ID), None)
    
    if current_user_obj:
        st.subheader(f"Hola, {current_user_obj.get('name')} 👋")
    else:
        st.subheader(DEFAULT_USER_ID)

    st.write("Pestañas")
    pages = ["Home", "Series", "Watch Parties", "Trending", "Plataformas", "Mi Watchlist", "Party Lobby"]

    default_page = st.session_state.get("page", "Home")
    if default_page not in pages:
        default_page = "Home"

    page = st.radio(
        "Ir a:",
        pages,
        index=pages.index(default_page)
    )

    st.session_state["page"] = page

    st.markdown("---")
    st.write("🔧 Configuración")

    if st.checkbox("Mostrar guías de ayuda", value=st.session_state.get("show_tutorial", True)):
        st.session_state["show_tutorial"] = True
    else:
        st.session_state["show_tutorial"] = False

    st.markdown("### 👤 Cambiar Usuario")
    
    name_to_id = {u['name']: u['user_id'] for u in users if u.get('name')}
    id_to_name = {v: k for k, v in name_to_id.items()}

    current_name_selection = id_to_name.get(DEFAULT_USER_ID)
    
    if current_name_selection:
        selected_user_name = st.selectbox(
            "Sesión activa:",
            options=list(name_to_id.keys()),
            index=list(name_to_id.keys()).index(current_name_selection),
            key="user_switcher_sidebar"
        )

        new_user_id = name_to_id[selected_user_name]
        if new_user_id != st.session_state["current_user_id"]:
            st.session_state["current_user_id"] = new_user_id
            st.toast(f"Cambiando perfil a {selected_user_name}...", icon="🔄")
            st.rerun()

#-----------------------
#Home Overview
#-----------------------

if page == "Home": 
    st.subheader("Mis watchlists y acciones rápidas")
    col1, col2 = st.columns([3, 1])
    show_page_guide("Home")
    with col1: 
        st.markdown("## 🎬 En tendencia") 
        series = fetch_series(limit=20) 
        sorted_trend = sorted(series, key=lambda s: (s.get("rating") or 0), reverse=True)[:15]
 
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

    with col2: 
        st.markdown("### 🍿 Crea una watch party") 

        if 'series' not in locals():
            series = fetch_series(limit=200)

        series_map = {str(s["id"]): s for s in series} 
        sel = st.selectbox(
        "Series", 
        options=list(series_map.keys()), 
        format_func=lambda x: series_map[x]["name"]
    )

        current_series = next((s for s in series if str(s["id"]) == str(sel)), None)
        
        available_platforms = current_series.get("platforms") or []

        if available_platforms:
            platform = st.selectbox("Plataforma", options=available_platforms)
        else:
            platform = st.text_input("Plataforma (ej. Netflix)")

        date = st.date_input("Fecha", value=datetime.now().date()) 
        time = st.time_input("Hora", key="time_input", value=st.session_state.get("time_input", datetime.now().time()))
        dt = datetime.combine(date, time)

        all_users = fetch_users()
        user_map = {u['name']: u['user_id'] for u in all_users if u.get('name')}
        
        selected_names = st.multiselect(
            "Invita participantes", 
            options=list(user_map.keys()),
            placeholder="Selecciona amigos..."
        )

        if st.button("Crear watchparty"): 
            st.info("Procesando...")

            invited_ids = [user_map[name] for name in selected_names]

            ok, msg = create_watchparty(
                int(sel), 
                DEFAULT_USER_ID, 
                dt.isoformat(), 
                platform, 
                invited_ids 
            ) 
            
            if ok: 
                st.success("Watchparty creada exitosamente!") 
            else: 
                st.error(f"Falló: {msg}")

# -----------------------
# Series catalogue
# -----------------------
if page == "Series":
    st.header("Catálogo de Series")
    show_page_guide("Series")
    selected_series = None
    all_series = fetch_series(limit=500)
    series = all_series 
    user_data = supabase.table("users").select("platforms").eq("user_id", DEFAULT_USER_ID).single().execute()
    my_platforms_set = set(user_data.data.get("platforms") or [])
    with st.expander("🔎 Buscar o filtrar catálogo", expanded=False):
        search_query = st.text_input("Buscar por título", placeholder="Ej: Breaking Bad")

        genres_list = sorted({s.get("genre") for s in all_series if s.get("genre")})
        years_list = sorted({s.get("year") for s in all_series if s.get("year")})
        episodes_values = [s.get("episodes") for s in all_series if isinstance(s.get("episodes"), (int, float))]
        min_eps, max_eps = (min(episodes_values), max(episodes_values)) if episodes_values else (0, 0)


        col1, col2, col3 = st.columns(3)
        with col1:
            selected_genre = st.selectbox("Filtrar por género", ["Todos"] + genres_list)
        with col2:
            selected_year = st.selectbox("Filtrar por año", ["Todos"] + [str(y) for y in years_list])
        with col3:
            filter_by_my_platforms = st.checkbox("Series disponibles en mis plataformas)")
            if filter_by_my_platforms and not my_platforms_set:
                 st.caption("⚠️ No tienes plataformas configuradas en tu perfil.")
            ep_min, ep_max = st.slider(
                "Rango de episodios",
                min_value=int(min_eps),
                max_value=int(max_eps),
                value=(int(min_eps), int(max_eps))
            )
        filtered = []
        
        filters_active = (
            search_query or 
            selected_genre != "Todos" or 
            selected_year != "Todos" or 
            episodes_values != "Todos" or 
            filter_by_my_platforms 
        )

        if filters_active:
            for s in all_series:
                name_match = not search_query or search_query.lower() in s.get("name", "").lower()
                genre_match = selected_genre == "Todos" or s.get("genre") == selected_genre
                year_match = selected_year == "Todos" or str(s.get("year")) == selected_year
                episodes_match = ep_min <= (s.get("episodes") or 0) <= ep_max
                platform_match = True
                if filter_by_my_platforms:
                    series_plats_set = set(s.get("platforms") or [])
                    if my_platforms_set.isdisjoint(series_plats_set):
                        platform_match = False

                if name_match and genre_match and year_match and episodes_match and platform_match:
                    filtered.append(s)

            series = filtered

            if not series:
                st.warning("No se encontraron series con estos filtros.")

    users = fetch_users()
    series_to_open = st.session_state.get("open_series", None)
    if series_to_open:
        selected_series = fetch_series_by_id(series_to_open)


    if selected_series:
        st.markdown("---")
        st.subheader(selected_series.get("name"))
        col1, col2 = st.columns([2, 1])

        with col1:
            plat_list = selected_series.get('platforms') or []
            plat_str = ", ".join(plat_list)
            st.markdown(f"*Género:* {selected_series.get('genre', '—')}")
            st.markdown(f"*Año:* {selected_series.get('year', '—')}")
            st.markdown(f"*Episodios:* {selected_series.get('episodes', '—')}")
            st.markdown(f"*Plataformas:* {plat_str}")
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
                supabase.table("ratings") \
                    .delete() \
                    .eq("user_id", DEFAULT_USER_ID) \
                    .eq("id", selected_series.get("id")) \
                    .execute()
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
        if st.button("Volver al Home"):
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
    show_page_guide("Watch Parties")
    wps = fetch_watchparties()
    all_users = fetch_users()
    user_map = {u["user_id"]: u["name"] for u in all_users}

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
            wp_id = wp.get("watchparty_id") or wp.get("id")

            series_id = wp.get("series")
            series_obj = {}
            if series_id:
                series_resp = supabase.table("series").select("name").eq("id", series_id).execute()
                if series_resp.data:
                    series_obj = series_resp.data[0]

            host_username = wp.get("host")
            if host_username:
                host_resp = supabase.table("users").select("name").eq("user_id", wp.get("host")).execute()
                if host_resp.data:
                    host_username = host_resp.data[0].get("name")

            participants_resp = supabase.table("watchparties").select("participants").eq("watchparty_id", wp_id).execute()
            participants = [p.get("participant") for p in (participants_resp.data or [])]

            p_ids = wp.get("participants") or []
            usernames = [user_map.get(pid, "Usuario desconocido") for pid in p_ids]

            with st.container():
                st.markdown(f"""
                <div class='wp-card'>
                    <div class='wp-title'>{series_obj.get('name','(No title)')}</div>
                    <div class='wp-details'>Anfitrión: <b>{host_username or '—'}</b></div>
                    <div class='wp-details'>🕒 {wp.get('time') or '—'}</div>
                    <div class='wp-participants'>👥 Participantes: {', '.join(usernames) or '—'}</div>
                </div>
                """, unsafe_allow_html=True)

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
    show_page_guide("Party Lobby")
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
            series_obj = {}
            series_id = wp.get("series")
            if series_id:
                s_res = supabase.table("series").select("name").eq("id", series_id).execute()
                if s_res.data:
                    series_obj = s_res.data[0]

            host_username = wp.get("host")
            if host_username:
                host_res = supabase.table("users").select("name").eq("user_id", wp.get("host")).execute()
                if host_res.data:
                    host_username = host_res.data[0].get("name")

            participants_resp = supabase.table("participants").select("participant").eq("watchparty_id", wp_id).execute()
            participant_ids = [p.get("participant") for p in (participants_resp.data or [])]

            participant_names = []
            if participant_ids:
                users_res = supabase.table("users").select("user_id, name").in_("user_id", participant_ids).execute()
                participant_names = [u.get("name") for u in (users_res.data or [])]

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
    show_page_guide("Trending")
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
    show_page_guide("Plataformas")

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

    #Contenedor de plataformas
    st.markdown("<div class='platform-container'>", unsafe_allow_html=True)

    for name in plats:
            try:
                series_res = supabase.table("series").select("*").contains("platforms", [name]).execute()
                series_list = series_res.data or []

                if series_list:
                    lis_html = "".join([f"<li>{s.get('name')} ({s.get('year')})</li>" for s in series_list])
                    
                    st.markdown(
                        f"""
                        <div class='platform-card'>
                            <div class='platform-title'>{name}</div>
                            <ul class='platform-list'>
                                {lis_html}
                            </ul>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            except Exception as e:
                st.error(f"Error cargando plataforma {name}: {e}")

# -----------------------
# My Watchlist
# -----------------------
if page == "Mi Watchlist":
    st.header("Mi Watchlist / Mis ratings")
    show_page_guide("Mi Watchlist")
    my_ratings = supabase.table("ratings").select("*").eq("user_id", DEFAULT_USER_ID).execute().data or []
    watchlist = [r for r in my_ratings if r.get("status") == "watchlist"]
    watched = [r for r in my_ratings if r.get("status") == "watched"]

    st.subheader("Pendientes")
    for r in watchlist:
        s = fetch_series_by_id(r.get("id"))
        st.write(f"- {s.get('name')}")

        if st.button(f"Marcar como vista", key=f"mark_{r.get('id')}"):
            supabase.table("ratings") \
                .delete() \
                .eq("user_id", DEFAULT_USER_ID) \
                .eq("id", r.get("id")) \
                .eq("status", "watchlist") \
                .execute()

            add_rating(DEFAULT_USER_ID, r.get("id"), stars=7, review="", status="watched")

            st.rerun()


    st.subheader("Vistas")
    for r in watched:
        s = fetch_series_by_id(r.get("id"))
        st.write(f"- {s.get('name')} — {r.get('stars') or '-'} ★ — {r.get('review') or ''}")