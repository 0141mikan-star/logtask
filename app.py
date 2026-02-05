import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time
import calendar
from datetime import datetime, date, timedelta, timezone
import altair as alt
import io
import base64
from PIL import Image
import hashlib
import random
import extra_streamlit_components as stx

# --- ページ設定 ---
st.set_page_config(page_title="褒めてくれる勉強時間・タスク管理アプリ", layout="wide", initial_sidebar_state="expanded")

# --- 日本時間 (JST) の定義 ---
JST = timezone(timedelta(hours=9))

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

# --- Cookieマネージャー ---
cookie_manager = stx.CookieManager(key="cookie_manager")

# --- デザイン適用関数 (カレンダー色固定版) ---
def apply_design(user_theme="標準", wallpaper="真っ白", main_text_color="#000000", accent_color="#FFD700"):
    fonts = {
        "ピクセル風": "'DotGothic16', sans-serif",
        "手書き風": "'Yomogi', cursive",
        "ポップ": "'Hachi Maru Pop', cursive",
        "明朝体": "'Shippori Mincho', serif",
        "筆文字": "'Yuji Syuku', serif",
        "標準": "sans-serif"
    }
    font_family = fonts.get(user_theme, "sans-serif")
    
    # 壁紙CSS
    bg_css = "background-color: #ffffff;"
    sidebar_bg = "#f8f9fa"
    container_bg = "#ffffff"
    text_color = main_text_color
    
    if wallpaper == "真っ黒":
        bg_css = "background-color: #121212;"
        sidebar_bg = "#1e1e1e"
        container_bg = "#2d2d2d"
        text_color = "#ffffff"
    elif wallpaper == "夕焼け":
        bg_css = "background-image: linear-gradient(120deg, #f6d365 0%, #fda085 100%);"
        container_bg = "rgba(255, 255, 255, 0.9)"
    elif wallpaper == "夜空":
        bg_css = "background-image: linear-gradient(to top, #30cfd0 0%, #330867 100%);"
        sidebar_bg = "rgba(0, 0, 0, 0.6)"
        container_bg = "rgba(255, 255, 255, 0.95)"
    elif wallpaper == "草原":
        bg_css = "background-image: linear-gradient(120deg, #d4fc79 0%, #96e6a1 100%);"
        container_bg = "rgba(255, 255, 255, 0.9)"

    # ★カレンダー・ボタン用の固定色定義
    fixed_cal_bg = "#ffffff"       # ボタン背景：白固定
    fixed_cal_text = "#333333"     # ボタン文字：黒固定
    fixed_cal_border = "#e0e0e0"   # ボタン枠線：グレー固定
    fixed_cal_select = "#FFD700"   # 選択時：ゴールド固定（アクセントカラーに依存しない）
    fixed_cal_hover = "#fffdf0"    # ホバー時：薄いクリーム色固定

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DotGothic16&family=Yomogi&family=Hachi+Maru+Pop&family=Shippori+Mincho&family=Yuji+Syuku&display=swap');
    
    /* 1. ベースフォント設定 */
    html, body, [data-testid="stAppViewContainer"] {{
        font-family: {font_family}, sans-serif;
        {bg_css}
    }}
    
    /* 2. テキスト要素への適用 */
    h1, h2, h3, h4, h5, h6, p, label, li, a, .stMarkdown, .stText {{
        font-family: {font_family}, sans-serif !important;
        color: {text_color} !important;
    }}
    
    /* 3. 入力フォームとボタンのフォント */
    input, textarea, select, button, .stButton button, .stSelectbox div {{
        font-family: {font_family}, sans-serif !important;
    }}

    /* サイドバー */
    [data-testid="stSidebar"] {{ 
        background-color: {sidebar_bg} !important; 
        border-right: 1px solid rgba(128,128,128,0.2); 
    }}
    [data-testid="stSidebar"] * {{ 
        color: {main_text_color} !important; 
    }}

    /* 入力フォームの背景色固定 (白) */
    input, textarea, select {{
        background-color: #ffffff !important; 
        color: #000000 !important; 
        border: 1px solid #ccc !important;
    }}
    div[data-baseweb="select"] > div {{ 
        background-color: #ffffff !important; 
        color: #000000 !important; 
    }}

    /* ★カレンダーの日付ボタン (色を完全固定) */
    .stButton button {{
        width: 100%; 
        height: 70px; 
        white-space: pre-wrap; 
        line-height: 1.1; 
        padding: 2px;
        border: 1px solid {fixed_cal_border} !important; 
        background-color: {fixed_cal_bg} !important; 
        color: {fixed_cal_text} !important;
        transition: all 0.2s; 
        border-radius: 8px;
    }}
    .stButton button:hover {{
        border-color: {fixed_cal_select} !important; 
        background-color: {fixed_cal_hover} !important; 
        transform: translateY(-2px); 
        z-index: 10; 
        position: relative;
    }}
    
    /* ★選択中の日付ボタン (色を完全固定・primary上書き) */
    div[data-testid="stVerticalBlock"] .stButton button[kind="primary"] {{
        background-color: {fixed_cal_select} !important; 
        border-color: #e6c200 !important; 
        color: #000000 !important; /* 文字色は黒固定 */
        font-weight: bold; 
        border-width: 2px;
    }}

    /* コンテナ */
    div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stExpander"], div[data-testid="stForm"] {{
        background-color: {container_bg} !important;
        border: 1px solid rgba(128,128,128,0.2); border-radius: 12px; padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    
    /* ステータスバー */
    .status-bar {{
        background: {container_bg}; border: 1px solid rgba(128,128,128,0.2); 
        padding: 15px; border-radius: 12px; display: flex; justify-content: space-around; align-items: center; margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .stat-val {{ font-size: 1.6em; font-weight: bold; }}
    
    /* 単位表示 (メイン文字色) */
    .stat-unit {{
        font-size: 0.6em;
        font-weight: normal;
        margin-left: 3px;
        color: {main_text_color} !important;
    }}
    
    /* アクションボタンも固定色（ゴールド）にする */
    button[kind="primary"] {{
        background: {fixed_cal_select} !important; 
        border: none !important; 
        color: #000 !important; 
        font-weight: bold !important;
    }}

    /* ランキングデザイン */
    .ranking-card {{
        padding: 15px; margin-bottom: 12px; border-radius: 15px; 
        display: flex; align-items: center; 
        background: {container_bg};
        border: 1px solid rgba(128,128,128,0.1);
        transition: transform 0.2s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    .ranking-card:hover {{ transform: scale(1.02); }}

    .rank-1 {{ background: linear-gradient(135deg, #FFF8E1 0%, #FFD700 100%) !important; border: 2px solid #FFD700 !important; }}
    .rank-1 .rank-name, .rank-1 .rank-score {{ color: #5c4d00 !important; text-shadow: 0 1px 0 rgba(255,255,255,0.6); }}
    .rank-2 {{ background: linear-gradient(135deg, #F5F5F5 0%, #C0C0C0 100%) !important; border: 2px solid #C0C0C0 !important; }}
    .rank-3 {{ background: linear-gradient(135deg, #FFF0E0 0%, #CD7F32 100%) !important; border: 2px solid #CD7F32 !important; }}
    
    .rank-medal {{ font-size: 2.5rem; width: 60px; text-align: center; margin-right: 10px; }}
    .rank-info {{ flex-grow: 1; }}
    .rank-name {{ font-size: 1.3em; font-weight: 800; color: {text_color}; }}
    .rank-title {{ font-size: 0.8em; opacity: 0.8; color: {text_color}; }}
    .rank-score {{ font-size: 1.5em; font-weight: 900; text-align: right; margin-right: 10px; color: {accent_color}; }}
    </style>
    """, unsafe_allow_html=True)

# --- 認証・DB操作 ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def login_user(username, password):
    try:
        res = supabase.table("users").select("password").eq("username", username).execute()
        if res.data and check_hashes(password, res.data[0]["password"]): return True, "成功"
        return False, "IDまたはパスワードが違います"
    except: return False, "エラー"

def add_user(username, password, nickname):
    try:
        data = {
            "username": username, "password": make_hashes(password), "nickname": nickname, 
            "xp": 0, "coins": 0, 
            "unlocked_themes": "標準", "current_theme": "標準", 
            "current_title": "見習い", "unlocked_titles": "見習い", 
            "current_wallpaper": "真っ白", "unlocked_wallpapers": "真っ白",
            "unlocked_bgms": "Lofi", "current_bgm": "なし", 
            "daily_goal": 60, "main_text_color": "#000000", "accent_color": "#FFD700"
        }
        supabase.table("users").insert(data).execute()
        return True, "登録成功"
    except: return False, "エラー"

def get_user_data(username):
    try:
        res = supabase.table("users").select("*").eq("username", username).execute()
        return res.data[0] if res.data else None
    except: return None

def get_subjects(username):
    try:
        res = supabase.table("subjects").select("subject_name").eq("username", username).execute()
        return [r['subject_name'] for r in res.data]
    except: return []

def add_subject_db(u, s): supabase.table("subjects").insert({"username": u, "subject_name": s}).execute()
def delete_subject_db(u, s): supabase.table("subjects").delete().eq("username", u).eq("subject_name", s).execute()

def add_study_log(u, s, m, d):
    supabase.table("study_logs").insert({"username": u, "subject": s, "duration_minutes": m, "study_date": str(d)}).execute()
    ud = get_user_data(u)
    if not ud: return m, 0, 0, False
    
    today_str = str(date.today())
    last_reward = ud.get('last_goal_reward_date')
    goal = ud.get('daily_goal', 60)
    
    logs = supabase.table("study_logs").select("duration_minutes").eq("username", u).eq("study_date", today_str).execute()
    total = sum([l['duration_minutes'] for l in logs.data]) if logs.data else m
    
    goal_reached = False
    
    if last_reward != today_str and total >= goal:
        new_xp = ud['xp'] + m
        new_coins = ud['coins'] + m + 100
        supabase.table("users").update({
            "xp": new_xp, "coins": new_coins, "last_goal_reward_date": today_str
        }).eq("username", u).execute()
        goal_reached = True
    else:
        new_xp = ud['xp'] + m
        new_coins = ud['coins'] + m
        supabase.table("users").update({"xp": new_xp, "coins": new_coins}).eq("username", u).execute()
        
    return m, new_xp, new_coins, goal_reached

def delete_study_log(lid, u, m):
    supabase.table("study_logs").delete().eq("id", lid).execute()
    ud = get_user_data(u)
    if ud: supabase.table("users").update({"xp": max(0, ud['xp']-m), "coins": max(0, ud['coins']-m)}).eq("username", u).execute()

def get_study_logs(u):
    try:
        res = supabase.table("study_logs").select("*").eq("username", u).order("created_at", desc=True).execute()
        if res.data: return pd.DataFrame(res.data)
        else: return pd.DataFrame(columns=['id', 'username', 'subject', 'duration_minutes', 'study_date'])
    except: return pd.DataFrame(columns=['id', 'username', 'subject', 'duration_minutes', 'study_date'])

def get_tasks(u):
    try:
        res = supabase.table("tasks").select("*").eq("username", u).order("due_date").execute()
        if res.data: return pd.DataFrame(res.data)
        else: return pd.DataFrame(columns=['id', 'username', 'task_name', 'status', 'due_date', 'priority'])
    except: return pd.DataFrame(columns=['id', 'username', 'task_name', 'status', 'due_date', 'priority'])

def add_task(u, n, d, p): supabase.table("tasks").insert({"username": u, "task_name": n, "status": "未完了", "due_date": str(d), "priority": p}).execute()
def delete_task(tid): supabase.table("tasks").delete().eq("id", tid).execute()
def complete_task(tid, u):
    supabase.table("tasks").update({"status": "完了"}).eq("id", tid).execute()
    ud = get_user_data(u)
    if ud: supabase.table("users").update({"xp": ud['xp']+10, "coins": ud['coins']+10}).eq("username", u).execute()

def get_weekly_ranking():
    start = (datetime.now(JST) - timedelta(days=7)).strftime('%Y-%m-%d')
    try:
        logs = supabase.table("study_logs").select("username, duration_minutes").gte("study_date", start).execute()
        if not logs.data: return pd.DataFrame()
        df = pd.DataFrame(logs.data).groupby('username').sum().reset_index()
        users = supabase.table("users").select("username, nickname, current_title").execute()
        return pd.merge(df, pd.DataFrame(users.data), on='username', how='left').sort_values('duration_minutes', ascending=False)
    except: return pd.DataFrame()

# --- タイマー ---
@st.fragment(run_every=1)
def show_timer_fragment(user_name):
    is_paused = st.session_state.get("timer_paused", False)
    accumulated = st.session_state.get("timer_accumulated", 0)
    start_time = st.session_state.get("start_time", time.time())
    
    if is_paused:
        elapsed = int(accumulated)
    else:
        elapsed = int(accumulated + (time.time() - start_time))
    
    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    
    st.markdown(f"""
    <div style="text-align: center; font-size: 6em; font-weight: bold; margin-bottom: 20px;">
        {h:02}:{m:02}:{s:02}
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        if not is_paused:
            if st.button("⏸ 一時停止", use_container_width=True):
                st.session_state["timer_accumulated"] = elapsed
                st.session_state["timer_paused"] = True
                st.rerun()
        else:
            if st.button("▶ 再開", use_container_width=True):
                st.session_state["start_time"] = time.time()
                st.session_state["timer_paused"] = False
                st.rerun()
                
    with c2:
        if st.button("⏹️ 終了", use_container_width=True, type="primary"):
            duration = max(1, elapsed // 60)
            _, _, _, reached = add_study_log(user_name, st.session_state.get("current_subject", "自習"), duration, date.today())
            st.session_state["is_studying"] = False
            st.session_state["timer_paused"] = False
            st.session_state["timer_accumulated"] = 0
            st.session_state["celebrate"] = True
            st.session_state["toast_msg"] = f"{duration}分 記録しました！"
            if reached: st.session_state["goal_reached_msg"] = "🎉 目標達成！"
            st.rerun()

# --- メイン処理 ---
def main():
    if "logged_in" not in st.session_state: 
        st.session_state.update({
            "logged_in": False, "username": "", "is_studying": False, 
            "start_time": None, "celebrate": False, "toast_msg": None, 
            "selected_date": str(date.today()),
            "cal_year": date.today().year, "cal_month": date.today().month,
            "selected_bgm": "なし",
            "timer_paused": False, "timer_accumulated": 0
        })

    if not st.session_state["logged_in"]:
        st.title("🛡️ ログイン")
        mode = st.selectbox("モード", ["ログイン", "新規登録"])
        u = st.text_input("ユーザーID"); p = st.text_input("パスワード", type="password")
        if mode == "新規登録":
            n = st.text_input("ニックネーム")
            if st.button("登録"):
                res, msg = add_user(u, p, n)
                if res: st.success(msg)
                else: st.error(msg)
        else:
            if st.button("ログイン"):
                res, msg = login_user(u, p)
                if res:
                    cookie_manager.set('logtask_auth', f"{u}:{make_hashes(p)}", expires_at=datetime.now() + timedelta(days=7))
                    st.session_state["logged_in"] = True; st.session_state["username"] = u; st.rerun()
                else: st.error(msg)
        return

    user = get_user_data(st.session_state["username"])
    if not user: st.session_state["logged_in"] = False; st.rerun()

    if 'unlocked_bgms' not in user:
        try: supabase.table("users").update({"unlocked_bgms": "Lofi"}).eq("username", user['username']).execute()
        except: pass
        user['unlocked_bgms'] = "Lofi"

    if not user.get('current_wallpaper'):
        try: supabase.table("users").update({"current_wallpaper": "真っ白"}).eq("username", user['username']).execute()
        except: pass

    today_str = str(date.today())
    if user.get('last_login_date') != today_str:
        new_coins = user['coins'] + 100
        supabase.table("users").update({
            "coins": new_coins,
            "last_login_date": today_str
        }).eq("username", user['username']).execute()
        st.toast("🎁 ログインボーナス！ +100コイン GET！", icon="🎁")
        time.sleep(1)
        user['coins'] = new_coins

    apply_design(
        user.get('current_theme', '標準'), 
        user.get('current_wallpaper', '真っ白'),
        user.get('main_text_color', '#000000'),
        user.get('accent_color', '#FFD700')
    )

    # サイドバー
    with st.sidebar:
        st.subheader("⚙️ 設定")
        
        st.markdown("##### 🎵 集中時のBGM (YouTube)")
        my_bgms = ["なし"] + user.get('unlocked_bgms', 'Lofi').split(',')
        if "Lofi" not in my_bgms: my_bgms.append("Lofi")
        
        selected_bgm = st.selectbox("再生する音", my_bgms, index=0, key="bgm_select")
        st.session_state["selected_bgm"] = selected_bgm

        with st.expander("👑 称号装備"):
            my_titles = user.get('unlocked_titles', '見習い').split(',')
            cur_t = user.get('current_title', '見習い')
            new_title = st.selectbox("称号", my_titles, index=my_titles.index(cur_t) if cur_t in my_titles else 0)
            if new_title != cur_t:
                supabase.table("users").update({"current_title": new_title}).eq("username", user['username']).execute()
                st.rerun()

        with st.expander("🖼️ 壁紙"):
            my_walls = user.get('unlocked_wallpapers', '真っ白').split(',')
            cur_w = user.get('current_wallpaper', '真っ白')
            new_w = st.selectbox("壁紙", my_walls, index=my_walls.index(cur_w) if cur_w in my_walls else 0)
            if new_w != cur_w:
                supabase.table("users").update({"current_wallpaper": new_w}).eq("username", user['username']).execute()
                st.rerun()

        with st.expander("🎨 文字色"):
            cur_m = user.get('main_text_color', '#000000'); cur_a = user.get('accent_color', '#FFD700')
            nm = st.color_picker("メイン", cur_m); na = st.color_picker("アクセント", cur_a)
            if nm != cur_m or na != cur_a:
                supabase.table("users").update({"main_text_color": nm, "accent_color": na}).eq("username", user['username']).execute()
                st.rerun()
        
        st.divider()
        ng = st.number_input("1日の目標(分)", value=user.get('daily_goal', 60), step=10)
        if ng != user.get('daily_goal', 60):
            if st.button("目標保存"):
                supabase.table("users").update({"daily_goal": ng}).eq("username", user['username']).execute()
                st.rerun()
        
        st.divider()
        
        VALID = ["標準", "ピクセル風", "手書き風", "ポップ", "明朝体", "筆文字"]
        my_fonts = [t for t in user.get('unlocked_themes', '').split(',') if t in VALID]
        if not my_fonts: my_fonts = ["標準"]
        cur_font = user.get('current_theme', '標準')
        if cur_font not in my_fonts: cur_font = "標準"
        nt = st.selectbox("フォント", my_fonts, index=my_fonts.index(cur_font))
        if nt != cur_font:
            supabase.table("users").update({"current_theme": nt}).eq("username", user['username']).execute()
            st.rerun()

        if st.button("ログアウト"):
            cookie_manager.delete('logtask_auth')
            st.session_state["logged_in"] = False; st.rerun()

    # ★ 集中モード (BGM再生)
    if st.session_state["is_studying"]:
        st.empty()
        
        if not st.session_state.get("timer_paused", False):
            s_bgm = st.session_state.get("selected_bgm", "なし")
            bgm_map = {
                "Lofi": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
                "雨音": "https://www.youtube.com/watch?v=BSmYxnvUDHw",
                "カフェ": "https://www.youtube.com/watch?v=rVUv_j9AiVM",
                "森": "https://www.youtube.com/watch?v=eNUpTV9BGac",
                "ホワイトノイズ": "https://www.youtube.com/watch?v=E1bbH03JhKA"
            }
            if s_bgm in bgm_map:
                st.video(bgm_map[s_bgm], autoplay=True)
                st.caption(f"🎵 再生中: {s_bgm}")
        else:
            st.warning("⏸ 一時停止中（BGM停止）")

        st.markdown(f"<h1 style='text-align:center;'>🔥 {st.session_state.get('current_subject','')} 中...</h1>", unsafe_allow_html=True)
        show_timer_fragment(user['username'])
        return

    logs_df = get_study_logs(user['username'])
    tasks = get_tasks(user['username'])
    today_mins = 0
    if not logs_df.empty and 'duration_minutes' in logs_df.columns:
        today_mins = logs_df[logs_df['study_date'].astype(str).str.contains(str(date.today()))]['duration_minutes'].sum()

    st.markdown(f"""
    <div class="status-bar">
        <div class="stat-item"><div class="stat-label">PLAYER</div><div class="stat-val" style="font-size:1.2em;">{user['nickname']}</div><div style="font-size:0.7em;">{user.get('current_title', '見習い')}</div></div>
        <div class="stat-item"><div class="stat-label">XP</div><div class="stat-val" style="color:{user.get('accent_color')};">{user['xp']}</div></div>
        <div class="stat-item"><div class="stat-label">COIN</div><div class="stat-val" style="color:{user.get('accent_color')};">{user['coins']} <span class="stat-unit">G</span></div></div>
        <div class="stat-item"><div class="stat-label">TODAY</div><div class="stat-val" style="color:{user.get('accent_color')};">{today_mins} <span class="stat-unit">/ {user.get('daily_goal')} min</span></div></div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(min(1.0, today_mins / max(1, user.get('daily_goal', 60))))

    if st.session_state.get("celebrate"): st.balloons(); st.session_state["celebrate"] = False
    if st.session_state.get("toast_msg"): st.toast(st.session_state["toast_msg"]); st.session_state["toast_msg"] = None

    t1, t2, t3, t4, t5, t6 = st.tabs(["📅 カレンダー", "⏱️ タイマー", "📊 分析", "🏆 ランキング", "🛒 ショップ", "📚 科目"])

    with t1: 
        c1, c2 = st.columns([0.65, 0.35])
        with c1:
            with st.container(border=True):
                # 月移動
                mc1, mc2, mc3 = st.columns([0.2, 0.6, 0.2])
                with mc1:
                    if st.button("◀ 前月"):
                        st.session_state.cal_month -= 1
                        if st.session_state.cal_month == 0: st.session_state.cal_month = 12; st.session_state.cal_year -= 1
                        st.rerun()
                with mc2:
                    st.markdown(f"<h3 style='text-align:center; margin:0; color:{user.get('main_text_color')};'>{st.session_state.cal_year}年 {st.session_state.cal_month}月</h3>", unsafe_allow_html=True)
                with mc3:
                    if st.button("次月 ▶"):
                        st.session_state.cal_month += 1
                        if st.session_state.cal_month == 13: st.session_state.cal_month = 1; st.session_state.cal_year += 1
                        st.rerun()
                
                cols = st.columns(7)
                weekdays = ["日", "月", "火", "水", "木", "金", "土"]
                for i, w in enumerate(weekdays):
                    cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#666;'>{w}</div>", unsafe_allow_html=True)
                
                cal = calendar.Calendar(firstweekday=6)
                month_days = cal.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
                
                for week in month_days:
                    cols = st.columns(7)
                    for i, d in enumerate(week):
                        with cols[i]:
                            if d != 0:
                                d_str = f"{st.session_state.cal_year}-{st.session_state.cal_month:02}-{d:02}"
                                label = f"{d}"
                                if not logs_df.empty:
                                    s_mins = logs_df[logs_df['study_date'].astype(str).str.contains(d_str)]['duration_minutes'].sum()
                                    if s_mins > 0: label += f"\n📖{s_mins}分"
                                if not tasks.empty:
                                    t_cnt = len(tasks[(tasks['due_date'].astype(str) == d_str) & (tasks['status'] == '未完了')])
                                    if t_cnt > 0: label += f"\n🔔{t_cnt}件"
                                
                                b_type = "primary" if d_str == st.session_state.get("selected_date") else "secondary"
                                if st.button(label, key=f"btn_{d_str}", type=b_type, use_container_width=True):
                                    st.session_state["selected_date"] = d_str
                                    st.rerun()
                            else: st.write("")

        with c2:
            with st.container(border=True):
                raw_sel = st.session_state.get("selected_date", str(date.today()))
                display_date = raw_sel
                st.markdown(f"### 📌 {display_date}")
                
                st.write("📚 **勉強記録**")
                if not logs_df.empty:
                    day_logs = logs_df[logs_df['study_date'].astype(str).str.contains(display_date)]
                    if not day_logs.empty:
                        total_d = day_logs['duration_minutes'].sum()
                        st.info(f"合計: {total_d}分")
                        for _, r in day_logs.iterrows():
                            lc1, lc2 = st.columns([0.7, 0.3])
                            lc1.text(f"{r['subject']}: {r['duration_minutes']}分")
                            if lc2.button("削除", key=f"deld_{r['id']}"):
                                delete_study_log(r['id'], user['username'], r['duration_minutes'])
                                st.rerun()
                    else: st.caption("記録なし")
                else: st.caption("記録なし")
                
                st.divider()
                st.write("📝 **タスク**")
                if not tasks.empty:
                    dt = tasks[tasks['due_date'].astype(str) == display_date]
                    if not dt.empty:
                        for _, task in dt.iterrows():
                            tc1, tc2, tc3 = st.columns([0.6, 0.2, 0.2])
                            if task['status'] == "未完了":
                                tc1.write(task['task_name'])
                                if tc2.button("完", key=f"done_{task['id']}"):
                                    complete_task(task['id'], user['username']); st.rerun()
                                if tc3.button("消", key=f"delt_{task['id']}"):
                                    delete_task(task['id']); st.rerun()
                            else: tc1.write(f"✅ {task['task_name']}")
                    else: st.caption("タスクなし")
                
                st.divider()
                with st.form("add_t"):
                    tn = st.text_input("タスク追加")
                    try: dd = datetime.strptime(display_date, '%Y-%m-%d').date()
                    except: dd = date.today()
                    td = st.date_input("期日", value=dd)
                    if st.form_submit_button("追加"):
                        add_task(user['username'], tn, td, "中"); st.rerun()

    with t2: 
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🔥 集中")
            sub = st.selectbox("科目", get_subjects(user['username']) + ["その他"])
            if sub=="その他": sub = st.text_input("科目名")
            if st.button("スタート", type="primary", use_container_width=True):
                if sub:
                    st.session_state["is_studying"]=True; st.session_state["start_time"]=time.time(); st.session_state["current_subject"]=sub
                    st.session_state["timer_paused"]=False; st.session_state["timer_accumulated"]=0
                    st.rerun()
        with c2:
            st.subheader("✏️ 記録")
            with st.form("manual"):
                d = st.date_input("日付"); h = st.number_input("時間",0,23); m = st.number_input("分",0,59)
                s = st.text_input("科目", value=sub if sub!="その他" else "")
                if st.form_submit_button("記録"):
                    add_study_log(user['username'], s, h*60+m, d); st.rerun()
        
        st.write("履歴 (最新5件)")
        if not logs_df.empty:
            for _,r in logs_df.head(5).iterrows():
                st.text(f"{r['study_date']} : {r['subject']} ({r['duration_minutes']}分)")

    with t3: 
        k1, k2 = st.columns(2)
        k1.metric("総勉強時間", f"{logs_df['duration_minutes'].sum()//60}時間" if not logs_df.empty else "0時間")
        k2.metric("今日", f"{today_mins}分")
        if not logs_df.empty:
            logs_df['dt'] = pd.to_datetime(logs_df['study_date'])
            rc = logs_df[logs_df['dt'] >= (datetime.now(JST)-timedelta(days=7)).replace(tzinfo=None)]
            if not rc.empty:
                st.altair_chart(alt.Chart(rc).mark_bar().encode(x='dt:T', y='duration_minutes', color='subject'), use_container_width=True)
                
    with t4: 
        st.subheader("🏆 週間ランキング")
        rk = get_weekly_ranking()
        if not rk.empty:
            top_score = rk.iloc[0]['duration_minutes']
            for i, r in rk.iterrows():
                rank = i + 1
                if rank == 1: css_class, medal = "rank-1", "🥇"
                elif rank == 2: css_class, medal = "rank-2", "🥈"
                elif rank == 3: css_class, medal = "rank-3", "🥉"
                else: css_class, medal = "", f"<span style='font-size:1.5rem; font-weight:bold; color:#888;'>{rank}</span>"
                
                bar_width = (r['duration_minutes'] / top_score) * 100 if top_score > 0 else 0
                st.markdown(f"""
                <div class="ranking-card {css_class}">
                    <div class="rank-medal">{medal}</div>
                    <div class="rank-info">
                        <div class="rank-name">{r['nickname']}</div>
                        <div class="rank-title">👑 {r['current_title']}</div>
                    </div>
                    <div style="text-align:right;">
                        <div class="rank-score">{int(r['duration_minutes'])} <span class="rank-unit">min</span></div>
                        <div style="width:100px; height:6px; background:rgba(0,0,0,0.1); border-radius:3px; margin-left:auto;">
                            <div style="width:{bar_width}%; height:100%; background:{user.get('accent_color')}; border-radius:3px;"></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("データが集計されていません")

    with t5: 
        st.subheader("🛒 ショップ")
        
        c_bgm, c_other = st.columns(2)
        
        with c_bgm:
            st.markdown("#### 🎵 BGM購入")
            for b, p in [("雨音", 500), ("カフェ", 800), ("森", 800), ("ホワイトノイズ", 300)]:
                with st.container(border=True):
                    bc1, bc2 = st.columns([0.6, 0.4])
                    bc1.write(f"**{b}**")
                    bc1.caption(f"{p} G")
                    if b not in user.get('unlocked_bgms', 'Lofi'):
                        if bc2.button("購入", key=f"buy_bgm_{b}"):
                            if user['coins'] >= p:
                                try:
                                    current_bgms = user.get('unlocked_bgms', 'Lofi')
                                    new_bgms = current_bgms + "," + b
                                    supabase.table("users").update({"coins": user['coins'] - p, "unlocked_bgms": new_bgms}).eq("username", user['username']).execute()
                                    st.balloons(); st.rerun()
                                except: st.error("購入に失敗しました")
                            else: st.error("不足")
                    else: bc2.write("✅ 済")

        with c_other:
            st.markdown("#### 🅰️ フォント")
            for f, p in [("ピクセル風",500),("手書き風",800),("ポップ",1000),("明朝体",1200),("筆文字",1500)]:
                with st.container(border=True):
                    fc1, fc2 = st.columns([0.6,0.4])
                    fc1.write(f"**{f}**")
                    fc1.caption(f"{p} G")
                    if f not in user['unlocked_themes']:
                        if fc2.button("購入", key=f"buy_{f}"):
                            if user['coins']>=p:
                                supabase.table("users").update({"coins":user['coins']-p, "unlocked_themes":user['unlocked_themes']+","+f}).eq("username", user['username']).execute()
                                st.balloons(); st.rerun()
                            else: st.error("不足")
                    else: fc2.write("✅ 済")
            
            st.divider()
            
            st.markdown("#### 🖼️ 壁紙")
            for w, p in [("真っ黒",500),("夕焼け",800),("夜空",1000),("草原",1200)]:
                with st.container(border=True):
                    wc1, wc2 = st.columns([0.6,0.4])
                    wc1.write(f"**{w}**")
                    wc1.caption(f"{p} G")
                    if w not in user['unlocked_wallpapers']:
                        if wc2.button("購入", key=f"buy_w_{w}"):
                            if user['coins']>=p:
                                supabase.table("users").update({"coins":user['coins']-p, "unlocked_wallpapers":user['unlocked_wallpapers']+","+w}).eq("username", user['username']).execute()
                                st.balloons(); st.rerun()
                            else: st.error("不足")
                    else: wc2.write("✅ 済")
            
            st.divider()
            st.markdown("#### 🎲 称号ガチャ")
            with st.container(border=True):
                st.write("**ランダム称号ガチャ (1回 100 G)**")
                if st.button("ガチャを回す", type="primary"):
                    if user['coins'] >= 100:
                        titles = ["駆け出し", "努力家", "集中王", "夜更かし", "天才", "覚醒者", "大賢者", "神童", "マスター", "レジェンド"]
                        got = random.choice(titles)
                        current_list = user['unlocked_titles'].split(',')
                        if got not in current_list:
                            new_list = user['unlocked_titles'] + "," + got
                            supabase.table("users").update({"coins":user['coins']-100, "unlocked_titles":new_list}).eq("username", user['username']).execute()
                            st.toast(f"🎉 新しい称号「{got}」を獲得！")
                        else:
                            supabase.table("users").update({"coins":user['coins']-100}).eq("username", user['username']).execute()
                            st.toast(f"かぶり！「{got}」だった...")
                        st.balloons(); time.sleep(1); st.rerun()
                    else: st.error("コイン不足")

    with t6: 
        ns = st.text_input("新規科目")
        if st.button("追加", key="add_sub"):
            if ns: add_subject_db(user['username'], ns); st.rerun()
        for s in get_subjects(user['username']):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(s)
            if c2.button("削除", key=f"del_s_{s}"): delete_subject_db(user['username'], s); st.rerun()

if __name__ == "__main__":
    main()
