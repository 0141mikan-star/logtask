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
st.set_page_config(page_title="褒めてくれる勉強時間・タスク管理アプリ", layout="wide")

# --- 日本時間 (JST) の定義 ---
JST = timezone(timedelta(hours=9))

# --- セッションステート初期化 ---
if "toast_msg" not in st.session_state:
    st.session_state["toast_msg"] = None
if "is_studying" not in st.session_state:
    st.session_state["is_studying"] = False
if "start_time" not in st.session_state:
    st.session_state["start_time"] = None
if "current_subject" not in st.session_state:
    st.session_state["current_subject"] = ""
if "last_cal_event" not in st.session_state:
    st.session_state["last_cal_event"] = None
if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = None

# トースト通知表示
if st.session_state["toast_msg"]:
    st.toast(st.session_state["toast_msg"], icon="🆙")
    st.session_state["toast_msg"] = None 

st.title("✅ 褒めてくれる勉強時間・タスク管理アプリ")

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

# --- デザイン適用関数 ---
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

def apply_wallpaper(wallpaper_name, bg_opacity=0.3):
    bg_url = ""
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

    css = ""
    if bg_url and wallpaper_name != "シンプル":
        css += f"""
        .stApp {{
            background-image: linear-gradient(rgba(0, 0, 0, {bg_opacity}), rgba(0, 0, 0, {bg_opacity})), url("{bg_url}");
            background-attachment: fixed;
            background-size: cover;
            background-position: center;
            background-color: #1E1E1E;
        }}
        """
    else:
        css += """
        .stApp { background-color: #1E1E1E; }
        """

    css += """
    .stMarkdown, .stText, h1, h2, h3, p, span, div {
        color: #ffffff !important;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
    }
    div[data-testid="stVerticalBlockBorderWrapper"], 
    div[data-testid="stExpander"], 
    div[data-testid="stForm"], 
    .task-container-box,
    .ranking-card {
        background-color: rgba(20, 20, 20, 0.9) !important; 
        border-radius: 12px;
        padding: 15px;
        border: 1px solid rgba(255,255,255,0.3);
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
    }
    div[data-testid="stVerticalBlockBorderWrapper"] *,
    div[data-testid="stExpander"] *,
    div[data-testid="stForm"] *, 
    .task-container-box *,
    .ranking-card * {
        color: #ffffff !important;
    }
    button[data-baseweb="tab"] {
        background-color: rgba(20, 20, 20, 0.9) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 5px 5px 0 0;
        margin-right: 4px;
    }
    button[aria-selected="true"] {
        background-color: #FF4B4B !important;
        border: 1px solid #FF4B4B;
    }
    label {
        color: #FFD700 !important;
        font-weight: bold;
        text-shadow: none;
    }
    button {
        font-weight: bold !important;
    }
    """
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# --- ユーザー情報取得 ---
def get_user_data(username):
    try:
        response = supabase.table("users").select("*").eq("username", username).execute()
        if response.data:
            return response.data[0]
        return None
    except:
        return None

# --- ランキングデータ取得 ---
def get_weekly_ranking():
    start_date = (datetime.now(JST) - timedelta(days=7)).strftime('%Y-%m-%d')
    try:
        logs_resp = supabase.table("study_logs").select("*").gte("study_date", start_date).execute()
        if not logs_resp.data:
            return pd.DataFrame()
        df_logs = pd.DataFrame(logs_resp.data)
        ranking = df_logs.groupby('username')['duration_minutes'].sum().reset_index()
        ranking = ranking.sort_values('duration_minutes', ascending=False).reset_index(drop=True)
        users_resp = supabase.table("users").select("username, nickname, current_title").execute()
        if users_resp.data:
            df_users = pd.DataFrame(users_resp.data)
            ranking = pd.merge(ranking, df_users, on='username', how='left')
        return ranking
    except Exception as e:
        return pd.DataFrame()

# --- セキュリティ・ユーザー管理 ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

def add_user(username, password, nickname):
    try:
        data = {
            "username": username, 
            "password": make_hashes(password),
            "nickname": nickname,
            "xp": 0, "coins": 0,
            "unlocked_themes": "標準",
            "current_title": "見習い",
            "unlocked_titles": "見習い",
            "unlocked_wallpapers": "シンプル",
            "current_wallpaper": "シンプル",
            "custom_title_unlocked": False
        }
        supabase.table("users").insert(data).execute()
        return True
    except:
        return False

def login_user(username, password):
    try:
        response = supabase.table("users").select("password").eq("username", username).execute()
        if response.data:
            if check_hashes(password, response.data[0]["password"]):
                return True
        return False
    except:
        return False

def update_profile(username, new_nickname, new_title):
    try:
        supabase.table("users").update({
            "nickname": new_nickname,
            "current_title": new_title
        }).eq("username", username).execute()
        return True
    except:
        return False

# --- DB操作 ---
def add_task(username, task_name, due_date, priority):
    data = {
        "username": username, "task_name": task_name,
        "status": '未完了', "due_date": str(due_date), "priority": priority
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

def add_study_log(username, subject, minutes, date_obj=None):
    if date_obj is None:
        date_str = datetime.now(JST).strftime('%Y-%m-%d')
    else:
        date_str = date_obj.strftime('%Y-%m-%d')
    data = {
        "username": username, "subject": subject,
        "duration_minutes": minutes, "study_date": date_str
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
    if not df.empty:
        if 'id' in df.columns:
            df = df.sort_values('id', ascending=False)
    return df

def delete_study_log(log_id, username, duration):
    try:
        supabase.table("study_logs").delete().eq("id", log_id).execute()
        user_data = get_user_data(username)
        if user_data:
            current_xp = user_data.get('xp', 0)
            current_coins = user_data.get('coins', 0)
            new_xp = max(0, current_xp - duration)
            new_coins = max(0, current_coins - duration)
            supabase.table("users").update({"xp": new_xp, "coins": new_coins}).eq("username", username).execute()
            return True
    except:
        return False
    return False

# --- ショップ・ガチャ ---
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
    if not current_wallpapers: current_wallpapers = "シンプル"
    if current_coins >= cost:
        new_coins = current_coins - cost
        new_wallpapers = f"{current_wallpapers},{wallpaper_name}"
        supabase.table("users").update({"coins": new_coins, "unlocked_wallpapers": new_wallpapers}).eq("username", username).execute()
        return True, new_coins
    return False, current_coins

def buy_custom_title_rights(username, cost):
    user_data = get_user_data(username)
    current_coins = user_data.get('coins', 0)
    if current_coins >= cost:
        new_coins = current_coins - cost
        supabase.table("users").update({"coins": new_coins, "custom_title_unlocked": True}).eq("username", username).execute()
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
        supabase.table("users").update({"coins": new_coins, "unlocked_titles": new_titles, "current_title": won_title}).eq("username", username).execute()
        return True, won_title, new_coins
    return False, None, current_coins

def set_title(username, title):
    supabase.table("users").update({"current_title": title}).eq("username", username).execute()

# --- 日付補正 ---
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
def show_detail_dialog(target_date, df_tasks, df_logs, username):
    st.write(f"**{target_date}** の記録")
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
    time_display = f"{hours}時間{mins}分" if hours > 0 else f"{mins}分"
    
    c1, c2 = st.columns(2)
    with c1:
        st.info("📝 **タスク**")
        if not day_tasks.empty:
            for _, row in day_tasks.iterrows():
                cc1, cc2 = st.columns([0.8, 0.2])
                icon = "✅" if row['status'] == '完了' else "⬜"
                cc1.write(f"{icon} {row['task_name']}")
                if cc2.button("🗑️", key=f"del_task_cal_{row['id']}"):
                    delete_task(row['id'])
                    st.session_state["toast_msg"] = "タスクを削除しました"
                    st.rerun()
        else:
            st.caption("なし")
    with c2:
        st.success(f"📖 **勉強: {time_display}**")
        if not day_logs.empty:
            for _, row in day_logs.iterrows():
                cc1, cc2 = st.columns([0.8, 0.2])
                cc1.write(f"・{row['subject']}: {row['duration_minutes']}分")
                if cc2.button("🗑️", key=f"del_log_cal_{row['id']}"):
                    delete_study_log(row['id'], username, row['duration_minutes'])
                    st.session_state["toast_msg"] = f"ログを削除 (-{row['duration_minutes']} XP/Coin)"
                    st.rerun()
        else:
            st.caption("なし")

# --- カレンダー表示 (シンプル版) ---
def render_calendar_and_details(df_tasks, df_logs, unique_key, username):
    st.markdown("""
    <style>
    .fc {
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 10px; padding: 10px; color: #333333 !important;
    }
    .fc-theme-standard .fc-scrollgrid { border-color: #ddd !important; }
    .fc-col-header-cell-cushion, .fc-daygrid-day-number {
        color: #333333 !important; text-decoration: none !important; text-shadow: none !important;
    }
    .fc-button-primary { background-color: #FF4B4B !important; border-color: #FF4B4B !important; }
    </style>
    """, unsafe_allow_html=True)
    st.subheader("📅 カレンダー")
    events = []
    if not df_tasks.empty:
        for _, row in df_tasks.iterrows():
            color = "#808080" if row['status'] == '完了' else "#FF4B4B" if row['priority']=="高" else "#1C83E1"
            events.append({
                "title": f"📝 {row['task_name']}", "start": row['due_date'], "backgroundColor": color, "allDay": True
            })
    if not df_logs.empty:
        for _, row in df_logs.iterrows():
            events.append({
                "title": f"📖 {row['subject']} ({row['duration_minutes']}m)", "start": row['study_date'],
                "backgroundColor": "#9C27B0", "borderColor": "#9C27B0", "allDay": True
            })
    cal_options = {
        "initialView": "dayGridMonth", "height": 450, "selectable": True, "timeZone": 'Asia/Tokyo'
    }
    cal_data = calendar(events=events, options=cal_options, callbacks=['dateClick', 'select', 'eventClick'], key=unique_key)
    if cal_data and cal_data != st.session_state.get("last_cal_event"):
        st.session_state["last_cal_event"] = cal_data
        raw_date_str = None
        if "dateClick" in cal_data: raw_date_str = cal_data["dateClick"]["date"]
        elif "select" in cal_data: raw_date_str = cal_data["select"]["start"]
        elif "eventClick" in cal_data: raw_date_str = cal_data["eventClick"]["event"]["start"]
        if raw_date_str:
            target_date = parse_correct_date(raw_date_str)
            show_detail_dialog(target_date, df_tasks, df_logs, username)

# --- タスクリスト ---
def render_daily_task_list(df_tasks, unique_key):
    st.subheader("📅 今日のクエスト")
    c1, c2 = st.columns([0.5, 0.5])
    with c1:
        target_date = st.date_input("日付を確認", value=date.today(), key=f"date_{unique_key}")
    day_tasks = pd.DataFrame()
    if not df_tasks.empty:
        day_tasks = df_tasks[df_tasks['due_date'] == str(target_date)]
    st.markdown(f'<div class="task-container-box"><div style="border-bottom:1px solid #555; padding-bottom:5px; margin-bottom:10px; font-weight:bold; color:#FFD700;">📅 {target_date} のクエスト</div>', unsafe_allow_html=True)
    if not day_tasks.empty:
        active = day_tasks[day_tasks['status'] == '未完了']
        completed = day_tasks[day_tasks['status'] == '完了']
        if not active.empty:
            for _, row in active.iterrows():
                prio = row['priority']
                icon = "🔥" if prio == "高" else "⚠️" if prio == "中" else "🟢"
                st.info(f"{icon} **{row['task_name']}**")
        else:
            if not completed.empty: st.success("🎉 全クエスト完了！")
            else: st.caption("タスクはありません")
        if not completed.empty:
            with st.expander("✅ 完了済み"):
                for _, row in completed.iterrows(): st.write(f"~~{row['task_name']}~~")
    else:
        st.info("予定はありません。休息も冒険の一部です🍵")
    st.markdown('</div>', unsafe_allow_html=True)

# --- メイン処理 ---
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""

    # === ログイン画面 ===
    if not st.session_state["logged_in"]:
        st.sidebar.title("🔐 ログイン")
        choice = st.sidebar.selectbox("メニュー", ["ログイン", "新規登録"])
        if choice == "ログイン":
            st.subheader("ログイン")
            u = st.text_input("ユーザー名")
            p = st.text_input("パスワード", type='password')
            if st.button("ログイン"):
                if login_user(u, p):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u
                    st.success("成功！")
                    st.rerun()
                else: st.error("失敗しました。")
        elif choice == "新規登録":
            st.subheader("新規登録")
            nu = st.text_input("ユーザー名 (ID)")
            np = st.text_input("パスワード", type='password')
            nn = st.text_input("ニックネーム (ランキング表示用)", placeholder="例: 勉強勇者")
            if st.button("登録"):
                if not nu or not np or not nn: st.error("全ての項目を入力してください")
                else:
                    if add_user(nu, np, nn): st.success("登録完了！ログインしてください。")
                    else: st.warning("そのIDは既に使われています。")
        return

    # === アプリ本編 ===
    current_user = st.session_state["username"]
    user_data = get_user_data(current_user)
    
    xp = user_data.get('xp', 0) if user_data else 0
    coins = user_data.get('coins', 0) if user_data else 0
    my_themes = user_data.get('unlocked_themes', "標準").split(',') if user_data else ["標準"]
    my_title = user_data.get('current_title', "見習い") if user_data else "見習い"
    my_nickname = user_data.get('nickname') if user_data else current_user
    my_wallpapers = user_data.get('unlocked_wallpapers')
    if not my_wallpapers: my_wallpapers = "シンプル"
    my_wallpapers_list = my_wallpapers.split(',')
    current_wallpaper = user_data.get('current_wallpaper')
    if not current_wallpaper: current_wallpaper = "シンプル"
    has_custom_title = user_data.get('custom_title_unlocked', False)

    # --- サイドバー ---
    with st.sidebar:
        st.subheader(f"👤 {my_nickname}")
        st.caption(f"ID: {current_user}")
        st.caption(f"👑 {my_title}")
        if st.button("ログアウト"):
            st.session_state["logged_in"] = False
            st.rerun()
        st.divider()
        st.subheader("🎨 デザイン設定")
        selected_theme = st.selectbox("フォント", my_themes, index=0)
        apply_font(selected_theme)
        try: w_index = my_wallpapers_list.index(current_wallpaper)
        except: w_index = 0
        selected_wallpaper = st.selectbox("壁紙", my_wallpapers_list, index=w_index)
        st.divider()
        st.write("🔧 **調整**")
        bg_opacity = st.slider("壁紙の暗さ", 0.0, 1.0, 0.3, 0.05)
        if selected_wallpaper != current_wallpaper:
            supabase.table("users").update({"current_wallpaper": selected_wallpaper}).eq("username", current_user).execute()
            st.rerun()
        apply_wallpaper(selected_wallpaper, bg_opacity)
        st.divider()
        st.subheader("📝 プロフィール編集")
        with st.expander("ニックネーム変更"):
            new_nn = st.text_input("新しい名前", value=my_nickname)
            if st.button("変更保存"):
                if update_profile(current_user, new_nn, my_title):
                    st.success("変更しました"); time.sleep(1); st.rerun()
        with st.expander("称号変更"):
            my_titles_list = user_data.get('unlocked_titles', "見習い").split(',')
            if has_custom_title:
                title_mode = st.radio("入力モード", ["リストから選択", "自由入力"])
                if title_mode == "自由入力":
                    new_custom_title = st.text_input("好きな称号を入力", value=my_title)
                    if st.button("称号更新"):
                        set_title(current_user, new_custom_title); st.success("更新しました"); time.sleep(1); st.rerun()
                else:
                    selected_t = st.selectbox("リスト", my_titles_list)
                    if st.button("称号選択"): set_title(current_user, selected_t); st.rerun()
            else:
                selected_t = st.selectbox("リスト", my_titles_list)
                if st.button("称号選択"): set_title(current_user, selected_t); st.rerun()

    # === ★重要: 勉強中モード (待機画面) ===
    # 勉強中なら他の画面を表示せず、時計だけを表示してループさせる
    if st.session_state["is_studying"]:
        # 画面を専有する
        st.markdown(f"### 🔥 {st.session_state['current_subject']} を勉強中...")
        
        # 経過時間計算
        now = time.time()
        elapsed_sec = int(now - st.session_state["start_time"])
        h = elapsed_sec // 3600
        m = (elapsed_sec % 3600) // 60
        s = elapsed_sec % 60
        time_str = f"{h:02}:{m:02}:{s:02}"
        
        # デジタル時計風表示
        st.markdown(f"""
        <div style="
            text-align: center; 
            font-size: 80px; 
            font-weight: bold; 
            color: #FF4B4B; 
            background-color: rgba(0,0,0,0.5);
            padding: 20px;
            border-radius: 15px;
            margin: 50px 0;
            text-shadow: 0 0 10px #FF0000;
        ">
            {time_str}
        </div>
        """, unsafe_allow_html=True)
        
        # 終了ボタン
        col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
        with col_c2:
            if st.button("⏹️ 終了して記録", type="primary", use_container_width=True):
                duration_min = max(1, elapsed_sec // 60)
                # 記録保存
                add_study_log(current_user, st.session_state["current_subject"], duration_min)
                # リセット
                st.session_state["is_studying"] = False
                st.session_state["start_time"] = None
                st.session_state["current_subject"] = ""
                st.session_state["celebrate"] = True
                st.session_state["toast_msg"] = f"{duration_min}分 勉強しました！お疲れ様！"
                st.rerun()
        
        # 自動リフレッシュ (1秒後に再実行)
        time.sleep(1)
        st.rerun()
        
        # ここで処理を終える (下のタブを表示させない)
        return

    # --- 通常画面（勉強していない時） ---
    
    # ステータス表示
    level = (xp // 50) + 1
    next_level_xp = level * 50
    xp_needed = next_level_xp - xp
    progress_val = 1.0 - (xp_needed / 50)
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
        c1.metric("Lv", f"{level}")
        c2.metric("XP", f"{xp}")
        c3.metric("Coin", f"{coins} 💰")
        c4.write(f"Next Lv: **{xp_needed} XP**")
        c4.progress(max(0.0, min(1.0, progress_val)))

    if st.session_state["celebrate"]:
        st.balloons()
        st.session_state["celebrate"] = False

    st.divider()

    df_tasks = get_tasks(current_user)
    df_logs = get_study_logs(current_user)

    # タブ
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 ToDo", "⏱️ タイマー", "📊 分析", "🏆 ランキング", "🛒 ショップ"])
    
    # === タブ1: ToDo ===
    with tab1:
        col_t1, col_t2 = st.columns([0.6, 0.4])
        with col_t1:
            with st.expander("➕ タスク追加", expanded=False):
                with st.form("add", clear_on_submit=True):
                    name = st.text_input("タスク名")
                    c1, c2 = st.columns(2)
                    d_date = c1.date_input("期限", value=date.today())
                    prio = c2.selectbox("優先度", ["高", "中", "低"], index=1)
                    if st.form_submit_button("追加", type="primary"):
                        if name:
                            add_task(current_user, name, d_date, prio)
                            st.session_state["toast_msg"] = "タスクを追加しました！"
                            time.sleep(0.5); st.rerun()
            if not df_tasks.empty:
                active_tasks = df_tasks[df_tasks['status'] == '未完了']
                if not active_tasks.empty:
                    st.write("🔽 **未完了タスク**")
                    selected_ids = []
                    for _, row in active_tasks.iterrows():
                        cc1, cc2, cc3 = st.columns([0.1, 0.7, 0.2])
                        if cc1.checkbox("", key=f"sel_{row['id']}"): selected_ids.append(row['id'])
                        cc2.markdown(f"**{row['task_name']}**")
                        cc2.caption(f"📅 {row['due_date']} | {row['priority']}")
                        if cc3.button("🗑️", key=f"d_{row['id']}"):
                            delete_task(row['id']); st.rerun()
                        st.markdown("---")
                    if selected_ids:
                        if st.button(f"✅ {len(selected_ids)}件完了 (+{len(selected_ids)*10} XP/Coin)", type="primary"):
                            amount, new_xp, new_coins = complete_tasks_bulk(selected_ids, current_user)
                            st.session_state["celebrate"] = True
                            st.session_state["toast_msg"] = f"+{amount}XP & +{amount}コイン 獲得！"
                            st.rerun()
                else: st.info("タスクはありません！")
        with col_t2:
            render_calendar_and_details(df_tasks, df_logs, "cal_todo", current_user)

    # === タブ2: 勉強タイマー (開始前画面) ===
    with tab2:
        col_s1, col_s2 = st.columns([0.5, 0.5])
        with col_s1:
            st.subheader("🔥 ストップウォッチ")
            # 開始前の入力フォーム
            with st.container(border=True):
                st.write("集中したい教科を入力してスタート！")
                subj_input = st.text_input("教科・内容", placeholder="例: 英語", key="start_subject_input")
                
                if st.button("▶️ 集中モードを開始", type="primary", use_container_width=True):
                    if not subj_input:
                        st.error("教科を入力してください")
                    else:
                        st.session_state["is_studying"] = True
                        st.session_state["start_time"] = time.time()
                        st.session_state["current_subject"] = subj_input
                        st.rerun()

            st.divider()
            st.subheader("✏️ 手動記録")
            with st.expander("入力フォームを開く", expanded=True):
                with st.form("manual", clear_on_submit=True):
                    c_date, c_time_h, c_time_m = st.columns([0.4, 0.3, 0.3])
                    m_date = c_date.date_input("日付", value=date.today())
                    mh = c_time_h.number_input("時間", 0, 24, 0)
                    mm = c_time_m.number_input("分", 0, 59, 0)
                    m_subj = st.text_input("教科 (Enterで記録)", placeholder="例: 数学")
                    if st.form_submit_button("記録", type="primary"):
                        total_m = (mh * 60) + mm
                        if m_subj and total_m > 0:
                            amt, nx, nc = add_study_log(current_user, m_subj, total_m, m_date)
                            st.session_state["celebrate"] = True
                            st.session_state["toast_msg"] = f"記録完了！ +{amt}XP & Coin"
                            st.rerun()
                        elif not m_subj: st.error("教科を入力してください")
                        elif total_m <= 0: st.error("時間を入力してください")
            
            if not df_logs.empty:
                st.markdown("---")
                st.subheader("📖 最近の記録 (削除可能)")
                recent_logs = df_logs.head(5)
                for _, row in recent_logs.iterrows():
                    rc1, rc2, rc3 = st.columns([0.5, 0.3, 0.2])
                    rc1.write(f"**{row['subject']}**")
                    rc2.caption(f"{row['study_date']} / {row['duration_minutes']}分")
                    if rc3.button("🗑️", key=f"del_{row['id']}"):
                        if delete_study_log(row['id'], current_user, row['duration_minutes']):
                            st.warning(f"削除しました (-{row['duration_minutes']} XP/Coin)")
                            time.sleep(1); st.rerun()
        with col_s2:
            render_daily_task_list(df_tasks, "timer_list")

    # === タブ3: 分析 ===
    with tab3:
        st.subheader("📊 学習データ分析")
        if not df_logs.empty:
            st.markdown("##### 📚 教科ごとの勉強時間")
            subject_dist = df_logs.groupby('subject')['duration_minutes'].sum().reset_index()
            pie_chart = alt.Chart(subject_dist).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="duration_minutes", type="quantitative"),
                color=alt.Color(field="subject", type="nominal"),
                tooltip=["subject", "duration_minutes"]
            ).properties(height=300)
            st.altair_chart(pie_chart, use_container_width=True)
            st.divider()
            st.markdown("##### 📈 過去7日間の推移 (教科別)")
            today = date.today()
            last_7_days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
            df_recent = df_logs[df_logs['study_date'].isin(last_7_days)].copy()
            if not df_recent.empty:
                bar_chart = alt.Chart(df_recent).mark_bar().encode(
                    x=alt.X('study_date', title='日付', scale=alt.Scale(domain=last_7_days)),
                    y=alt.Y('duration_minutes', title='時間(分)'),
                    color=alt.Color('subject', title='教科', legend=alt.Legend(orient='top')),
                    tooltip=['study_date', 'subject', 'duration_minutes']
                ).properties(height=300)
                st.altair_chart(bar_chart, use_container_width=True)
            else: st.info("過去7日間の記録はありません")
        else: st.info("データがありません")

    # === タブ4: ランキング ===
    with tab4:
        st.subheader("🏆 週間勉強時間ランキング")
        st.caption("過去7日間の合計時間を競いましょう！")
        df_ranking = get_weekly_ranking()
        if not df_ranking.empty:
            for index, row in df_ranking.iterrows():
                rank = index + 1
                medal = "🥇" if rank==1 else "🥈" if rank==2 else "🥉" if rank==3 else f"{rank}位"
                is_me = (row['username'] == current_user)
                border_color = "#FF4B4B" if is_me else "rgba(255,255,255,0.3)"
                bg_style = "background-color: rgba(255, 75, 75, 0.2) !important;" if is_me else ""
                display_name = row.get('nickname') if row.get('nickname') else row['username']
                total_m = row['duration_minutes']
                h, m = total_m // 60, total_m % 60
                time_str = f"{h}時間 {m}分" if h > 0 else f"{m}分"
                st.markdown(f"""
                <div class="ranking-card" style="border: 1px solid {border_color}; {bg_style} margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
                    <div style="display:flex; align-items:center;">
                        <span style="font-size: 1.5em; width: 50px; text-align:center;">{medal}</span>
                        <div>
                            <div style="font-size: 1.1em; font-weight: bold;">{display_name}</div>
                            <div style="font-size: 0.8em; color: #ccc;">{row.get('current_title', '見習い')}</div>
                        </div>
                    </div>
                    <div style="font-size: 1.2em; font-weight: bold; color: #FFD700;">{time_str}</div>
                </div>""", unsafe_allow_html=True)
        else: st.info("まだデータがありません。あなたが一番乗りです！")

    # === タブ5: ショップ ===
    with tab5:
        col_shop_font, col_shop_wall, col_gacha = st.columns(3)
        with col_shop_font:
            st.subheader("🅰️ フォント屋")
            font_items = [
                {"name": "ピクセル風", "cost": 500, "desc": "レトロゲーム風"}, {"name": "手書き風", "cost": 800, "desc": "黒板風"},
                {"name": "ポップ", "cost": 1000, "desc": "元気な丸文字"}, {"name": "明朝体", "cost": 1200, "desc": "小説のような雰囲気"},
                {"name": "筆文字", "cost": 1500, "desc": "達筆な和風"},
            ]
            for item in font_items:
                with st.container(border=True):
                    st.write(f"**{item['name']}**"); st.caption(f"{item['desc']} ({item['cost']}💰)")
                    if item['name'] in my_themes: st.button("✅ 済", disabled=True, key=f"btn_f_{item['name']}")
                    else:
                        if st.button(f"購入", key=f"buy_f_{item['name']}"):
                            success, bal = buy_theme(current_user, item['name'], item['cost'])
                            if success: st.balloons(); st.rerun()
                            else: st.error("コイン不足")
        with col_shop_wall:
            st.subheader("🖼️ 壁紙屋")
            wall_items = [
                {"name": "草原", "cost": 500, "desc": "爽やかな緑"}, {"name": "夕焼け", "cost": 800, "desc": "落ち着くオレンジ"},
                {"name": "夜空", "cost": 1000, "desc": "静かな夜"}, {"name": "ダンジョン", "cost": 1500, "desc": "冒険の始まり"},
                {"name": "王宮", "cost": 2000, "desc": "高貴な空間"}, {"name": "図書館", "cost": 1200, "desc": "知の宝庫"},
                {"name": "サイバー", "cost": 1800, "desc": "近未来都市"},
            ]
            for item in wall_items:
                with st.container(border=True):
                    st.write(f"**{item['name']}**"); st.caption(f"{item['desc']} ({item['cost']}💰)")
                    if item['name'] in my_wallpapers_list: st.button("✅ 済", disabled=True, key=f"btn_w_{item['name']}")
                    else:
                        if st.button(f"購入", key=f"buy_w_{item['name']}"):
                            success, bal = buy_wallpaper(current_user, item['name'], item['cost'])
                            if success: st.balloons(); st.rerun()
                            else: st.error("コイン不足")
        with col_gacha:
            st.subheader("🎲 称号ガチャ"); st.write("1回 **100 💰**")
            if st.button("回す！", type="primary"):
                success, won_title, bal = play_gacha(current_user, 100)
                if success: st.balloons(); st.success(f"🎉 **{won_title}**"); time.sleep(2); st.rerun()
                else: st.error("コイン不足")
            st.divider(); st.subheader("📛 自由称号パス"); st.write("**9999 💰**")
            if has_custom_title: st.button("✅ 解放済み", disabled=True)
            else:
                if st.button("購入する", type="primary"):
                    success, bal = buy_custom_title_rights(current_user, 9999)
                    if success: st.balloons(); st.rerun()
                    else: st.error("コイン不足")

if __name__ == "__main__":
    main()

