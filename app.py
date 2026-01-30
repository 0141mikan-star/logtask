import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random
import time
from datetime import datetime, date, timedelta, timezone
import urllib.parse
import hashlib
import altair as alt
from streamlit_calendar import calendar

# ページ設定
st.set_page_config(page_title="個人タスク管理RPG", layout="wide")

# --- 日本時間 (JST) の定義 ---
JST = timezone(timedelta(hours=9))

# --- セッションステート初期化 ---
if "toast_msg" not in st.session_state:
    st.session_state["toast_msg"] = None
if "is_studying" not in st.session_state:
    st.session_state["is_studying"] = False
if "start_time" not in st.session_state:
    st.session_state["start_time"] = None
if "last_cal_event" not in st.session_state:
    st.session_state["last_cal_event"] = None
if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = None

# トースト通知表示
if st.session_state["toast_msg"]:
    st.toast(st.session_state["toast_msg"], icon="🆙")
    st.session_state["toast_msg"] = None 

st.title("✅ 褒めてくれるタスク管理 (RPG風)")

# 称号ガチャのリスト
GACHA_TITLES = [
    "駆け出し冒険者", "夜更かしの達人", "努力の天才", "タスクスレイヤー",
    "週末の戦士", "無限の集中力", "数学の悪魔", "コードの魔術師",
    "文房具マスター", "伝説の勇者", "睡眠不足の神", "カフェイン中毒"
]

# --- Supabase接続設定 ---
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except:
        return None

supabase = init_supabase()

if not supabase:
    st.error("Supabaseへの接続設定が見つかりません。")
    st.stop()

# --- デザイン適用関数 (フォント) ---
def apply_font(font_type):
    css_import = ""
    font_family = ""
    
    if font_type == "ピクセル風":
        css_import = "@import url('https://fonts.googleapis.com/css2?family=DotGothic16&display=swap');"
        font_family = "'DotGothic16', sans-serif"
    elif font_type == "手書き風":
        css_import = "@import url('https://fonts.googleapis.com/css2?family=Yomogi&display=swap');"
        font_family = "'Yomogi', cursive"
    elif font_type == "ポップ":
        css_import = "@import url('https://fonts.googleapis.com/css2?family=Hachi+Maru+Pop&display=swap');"
        font_family = "'Hachi Maru Pop', cursive"
    elif font_type == "明朝体":
        css_import = "@import url('https://fonts.googleapis.com/css2?family=Shippori+Mincho&display=swap');"
        font_family = "'Shippori Mincho', serif"
    elif font_type == "筆文字":
        css_import = "@import url('https://fonts.googleapis.com/css2?family=Yuji+Syuku&display=swap');"
        font_family = "'Yuji Syuku', serif"
    
    if font_family:
        st.markdown(f"""
        <style>
        {css_import}
        body, p, h1, h2, h3, h4, h5, h6, input, textarea, label, button, .stTooltip, .stExpander {{
            font-family: {font_family} !important;
        }}
        .stMarkdown, .stTextInput > div > div, .stSelectbox > div > div {{
            font-family: {font_family} !important;
        }}
        .material-icons, .material-symbols-rounded, [data-testid="stExpander"] svg {{
            font-family: inherit !important;
        }}
        </style>
        """, unsafe_allow_html=True)

# --- デザイン適用関数 (壁紙・透明度調整対応) ---
def apply_wallpaper(wallpaper_name, bg_opacity=0.3, box_opacity=0.9):
    bg_url = ""
    
    # 画像URL定義
    if wallpaper_name == "草原": 
        bg_url = "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?auto=format&fit=crop&w=1920&q=80"
    elif wallpaper_name == "夕焼け":
        bg_url = "https://images.unsplash.com/photo-1472120435266-53107fd0c44a?auto=format&fit=crop&w=1920&q=80"
    elif wallpaper_name == "夜空":
        bg_url = "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?auto=format&fit=crop&w=1920&q=80"
    elif wallpaper_name == "ダンジョン":
        bg_url = "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1920&q=80"
    elif wallpaper_name == "王宮":
        bg_url = "https://images.unsplash.com/photo-1544939514-aa98d908bc47?auto=format&fit=crop&w=1920&q=80"
    elif wallpaper_name == "図書館":
        bg_url = "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=1920&q=80"
    elif wallpaper_name == "サイバー":
        bg_url = "https://images.unsplash.com/photo-1535295972055-1c762f4483e5?auto=format&fit=crop&w=1920&q=80"

    if wallpaper_name == "シンプル" or not bg_url:
        return

    st.markdown(f"""
    <style>
    /* 全体の背景画像と、黒フィルターの濃さ(bg_opacity) */
    .stApp {{
        background-image: linear-gradient(rgba(0, 0, 0, {bg_opacity}), rgba(0, 0, 0, {bg_opacity})), url("{bg_url}");
        background-attachment: fixed;
        background-size: cover;
        background-position: center;
        background-color: #1E1E1E;
    }}
    
    /* 文字色を白く */
    .stMarkdown, .stText, h1, h2, h3, p, span {{
        color: #ffffff !important;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.9);
    }}

    /* タブバー */
    button[data-baseweb="tab"] {{
        background-color: rgba(0, 0, 0, 0.6) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 5px 5px 0 0;
        margin-right: 4px;
    }}
    button[aria-selected="true"] {{
        background-color: #FF4B4B !important;
        border: 1px solid #FF4B4B;
    }}
    
    /* コンテナ・ボックスの濃さ(box_opacity) */
    /* ショップのカード、Expander、フォーム、タイマーのタスクリスト */
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stExpander"],
    div[data-testid="stForm"],
    .task-container-box {{
        background-color: rgba(20, 20, 20, {box_opacity}) !important;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid rgba(255,255,255,0.3);
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
        /* ボックス内の文字色も強制的に白にする */
        color: #ffffff !important;
    }}

    /* コンテナ内の全てのテキスト要素の色も強制的に白にする */
    div[data-testid="stVerticalBlockBorderWrapper"] *,
    div[data-testid="stExpander"] *,
    div[data-testid="stForm"] *,
    .task-container-box * {{
        color: #ffffff !important;
    }}
    
    /* 入力ラベル */
    label {{
        color: #FFD700 !important; /* 金色 */
        font-weight: bold;
        text-shadow: none;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- ユーザー情報取得 ---
def get_user_data(username):
    try:
        response = supabase.table("users").select("*").eq("username", username).execute()
        if response.data:
            return response.data[0]
        return None
    except:
        return None

# --- セキュリティ関数 ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# --- ユーザー管理関数 ---
def add_user(username, password):
    try:
        data = {
            "username": username, 
            "password": make_hashes(password), 
            "xp": 0,
            "coins": 0,
            "unlocked_themes": "標準",
            "current_title": "見習い",
            "unlocked_titles": "見習い",
            "unlocked_wallpapers": "シンプル",
            "current_wallpaper": "シンプル"
        }
        supabase.table("users").insert(data).execute()
        return True
    except Exception:
        return False

def login_user(username, password):
    try:
        response = supabase.table("users").select("password").eq("username", username).execute()
        if response.data:
            if check_hashes(password, response.data[0]["password"]):
                return True
        return False
    except Exception:
        return False

# --- DB操作: タスク関連 ---
def add_task(username, task_name, due_date, priority):
    data = {
        "username": username,
        "task_name": task_name,
        "status": '未完了',
        "due_date": str(due_date),
        "priority": priority
    }
    supabase.table("tasks").insert(data).execute()

def get_tasks(username):
    response = supabase.table("tasks").select("*").eq("username", username).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['status_rank'] = df['status'].apply(lambda x: 1 if x == '未完了' else 2)
        priority_map = {'高': 1, '中': 2, '低': 3}
        df['priority_rank'] = df['priority'].map(priority_map).fillna(3)
        df = df.sort_values(by=['status_rank', 'priority_rank', 'due_date'])
        return df
    return pd.DataFrame()

def complete_tasks_bulk(task_ids, username):
    supabase.table("tasks").update({"status": "完了"}).in_("id", task_ids).execute()
    amount = len(task_ids) * 10
    user_data = get_user_data(username)
    if user_data:
        new_xp = user_data.get('xp', 0) + amount
        new_coins = user_data.get('coins', 0) + amount
        supabase.table("users").update({"xp": new_xp, "coins": new_coins}).eq("username", username).execute()
        return amount, new_xp, new_coins
    return 0, 0, 0

def delete_task(task_id):
    supabase.table("tasks").delete().eq("id", task_id).execute()

# --- DB操作: 勉強ログ関連 ---
def add_study_log(username, subject, minutes, date_obj=None):
    if date_obj is None:
        date_str = datetime.now(JST).strftime('%Y-%m-%d')
    else:
        date_str = date_obj.strftime('%Y-%m-%d')
        
    data = {
        "username": username,
        "subject": subject,
        "duration_minutes": minutes,
        "study_date": date_str
    }
    supabase.table("study_logs").insert(data).execute()
    
    amount = minutes
    user_data = get_user_data(username)
    if user_data:
        new_xp = user_data.get('xp', 0) + amount
        new_coins = user_data.get('coins', 0) + amount
        supabase.table("users").update({"xp": new_xp, "coins": new_coins}).eq("username", username).execute()
        return amount, new_xp, new_coins
    return 0, 0, 0

def get_study_logs(username):
    response = supabase.table("study_logs").select("*").eq("username", username).execute()
    df = pd.DataFrame(response.data)
    return df

# --- DB操作: ショップ・ガチャ関連 ---
def buy_theme(username, theme_name, cost):
    user_data = get_user_data(username)
    current_coins = user_data.get('coins', 0)
    current_themes = user_data.get('unlocked_themes', "標準")
    
    if current_coins >= cost:
        new_coins = current_coins - cost
        new_themes = f"{current_themes},{theme_name}"
        supabase.table("users").update({"coins": new_coins, "unlocked_themes": new_themes}).eq("username", username).execute()
        return True, new_coins
    return False, current_coins

def buy_wallpaper(username, wallpaper_name, cost):
    user_data = get_user_data(username)
    current_coins = user_data.get('coins', 0)
    current_wallpapers = user_data.get('unlocked_wallpapers')
    if not current_wallpapers:
        current_wallpapers = "シンプル"

    if current_coins >= cost:
        new_coins = current_coins - cost
        new_wallpapers = f"{current_wallpapers},{wallpaper_name}"
        supabase.table("users").update({"coins": new_coins, "unlocked_wallpapers": new_wallpapers}).eq("username", username).execute()
        return True, new_coins
    return False, current_coins

def play_gacha(username, cost):
    user_data = get_user_data(username)
    current_coins = user_data.get('coins', 0)
    current_titles = user_data.get('unlocked_titles', "見習い")
    
    if current_coins >= cost:
        new_coins = current_coins - cost
        won_title = random.choice(GACHA_TITLES)
        
        if won_title not in current_titles.split(','):
            new_titles = f"{current_titles},{won_title}"
        else:
            new_titles = current_titles
            
        supabase.table("users").update({
            "coins": new_coins, 
            "unlocked_titles": new_titles,
            "current_title": won_title
        }).eq("username", username).execute()
        
        return True, won_title, new_coins
    return False, None, current_coins

def set_title(username, title):
    supabase.table("users").update({"current_title": title}).eq("username", username).execute()


# --- 日付補正処理 ---
def parse_correct_date(raw_date):
    try:
        if "T" in raw_date:
            dt_utc = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            dt_jst = dt_utc.astimezone(JST)
            return dt_jst.strftime('%Y-%m-%d')
        else:
            return raw_date
    except:
        return raw_date

# --- 詳細ダイアログ ---
@st.dialog("📅 記録の詳細")
def show_detail_dialog(target_date, df_tasks, df_logs):
    st.write(f"**{target_date}** の頑張り記録です")
    
    day_tasks = pd.DataFrame()
    if not df_tasks.empty:
        day_tasks = df_tasks[df_tasks['due_date'] == target_date]
    
    day_logs = pd.DataFrame()
    total_minutes = 0
    if not df_logs.empty:
        day_logs = df_logs[df_logs['study_date'] == target_date]
        if not day_logs.empty:
            total_minutes = day_logs['duration_minutes'].sum()
            
    hours = total_minutes // 60
    mins = total_minutes % 60
    if hours > 0:
        time_display = f"{hours}時間{mins}分"
    else:
        time_display = f"{mins}分"
    
    c1, c2 = st.columns(2)
    with c1:
        st.info("📝 **タスク**")
        if not day_tasks.empty:
            for _, row in day_tasks.iterrows():
                icon = "✅" if row['status'] == '完了' else "⬜"
                st.write(f"{icon} {row['task_name']}")
        else:
            st.caption("なし")
    with c2:
        st.success(f"📖 **勉強: {time_display}**")
        if not day_logs.empty:
            for _, row in day_logs.iterrows():
                st.write(f"・{row['subject']}: {row['duration_minutes']}分")
        else:
            st.caption("なし")

# --- カレンダーコンポーネント (ToDoタブ用) ---
def render_calendar_and_details(df_tasks, df_logs, unique_key):
    # カレンダー用の白い背景スタイルを適用
    st.markdown("""
    <style>
    .fc {
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 10px;
        padding: 10px;
        color: #333333 !important;
    }
    .fc-theme-standard .fc-scrollgrid {
        border-color: #ddd !important;
    }
    .fc-col-header-cell-cushion, .fc-daygrid-day-number {
        color: #333333 !important;
        text-decoration: none !important;
        text-shadow: none !important;
    }
    .fc-button-primary {
        background-color: #FF4B4B !important;
        border-color: #FF4B4B !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.subheader("📅 カレンダー")
    
    events = []
    if not df_tasks.empty:
        for _, row in df_tasks.iterrows():
            color = "#808080" if row['status'] == '完了' else "#FF4B4B" if row['priority']=="高" else "#1C83E1"
            events.append({
                "title": f"📝 {row['task_name']}",
                "start": row['due_date'],
                "backgroundColor": color,
                "allDay": True
            })
    if not df_logs.empty:
        for _, row in df_logs.iterrows():
            events.append({
                "title": f"📖 {row['subject']} ({row['duration_minutes']}m)",
                "start": row['study_date'],
                "backgroundColor": "#9C27B0",
                "borderColor": "#9C27B0",
                "allDay": True
            })

    cal_options = {
        "initialView": "dayGridMonth",
        "height": 450,
        "selectable": True,
        "timeZone": 'Asia/Tokyo', 
    }
    
    cal_data = calendar(events=events, options=cal_options, callbacks=['dateClick', 'select', 'eventClick'], key=unique_key)
    
    if cal_data and cal_data != st.session_state["last_cal_event"]:
        st.session_state["last_cal_event"] = cal_data
        raw_date_str = None
        if "dateClick" in cal_data:
             raw_date_str = cal_data["dateClick"]["date"]
        elif "select" in cal_data:
             raw_date_str = cal_data["select"]["start"]
        elif "eventClick" in cal_data:
             raw_date_str = cal_data["eventClick"]["event"]["start"]
        
        if raw_date_str:
            target_date = parse_correct_date(raw_date_str)
            show_detail_dialog(target_date, df_tasks, df_logs)

# --- その日のタスクリスト (タイマーダブ用) ---
def render_daily_task_list(df_tasks, unique_key):
    st.subheader("📅 今日のクエスト")
    
    c1, c2 = st.columns([0.5, 0.5])
    with c1:
        target_date = st.date_input("日付
