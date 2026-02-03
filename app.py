import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random
import time
from datetime import datetime, date, timedelta, timezone
from streamlit_calendar import calendar
import altair as alt
import io
import base64
from PIL import Image
import hashlib
import extra_streamlit_components as stx

# ページ設定
st.set_page_config(page_title="褒めてくれる勉強時間・タスク管理アプリ", layout="wide")

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

# --- Cookieマネージャーの初期化 ---
cookie_manager = stx.CookieManager(key="cookie_manager")

# --- 画像処理関数 ---
def image_to_base64(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# --- イベント詳細表示ダイアログ ---
@st.dialog("📝 イベント詳細")
def show_event_info(title, start, color):
    st.markdown(f"### {title}")
    st.divider()
    st.write(f"📅 **日付:** {start}")
    st.markdown(f"🎨 **ラベル色:** <span style='color:{color}; font-size:1.5em;'>■</span>", unsafe_allow_html=True)

# --- デザイン適用関数 ---
def apply_design(user_theme="標準", wallpaper="真っ白", custom_data=None, 
                 bg_opacity=0.5, container_opacity=0.9, sidebar_bg_color="#ffffff",
                 main_text_color="#000000", sidebar_text_color="#000000", accent_color="#FFD700"):
    fonts = {
        "ピクセル風": "'DotGothic16', sans-serif",
        "手書き風": "'Yomogi', cursive",
        "ポップ": "'Hachi Maru Pop', cursive",
        "明朝体": "'Shippori Mincho', serif",
        "筆文字": "'Yuji Syuku', serif",
        "標準": "sans-serif"
    }
    font_family = fonts.get(user_theme, "sans-serif")
    
    # 背景CSS設定
    bg_style = ""
    
    # ★修正ポイント: 「真っ白」のときは透明度計算をせず、完全に不透明な白にする（バグ回避）
    if wallpaper == "真っ白":
        bg_style = "background-color: #ffffff !important;"
        card_bg_color = "#ffffff" # 完全な白
        border_style = "1px solid #e0e0e0" # 薄いグレーの枠線
        shadow_color = "none"
        main_text_override = "#000000"
    elif wallpaper == "真っ黒":
        bg_style = "background-color: #000000 !important;"
        card_bg_color = "#1a1a1a"
        border_style = "1px solid #333"
        shadow_color = "1px 1px 2px #000"
        main_text_override = "#ffffff"
    else:
        # 画像がある場合のみ透明度を適用
        card_bg_color = f"rgba(255, 255, 255, {container_opacity})"
        border_style = "1px solid rgba(255,255,255,0.2)"
        shadow_color = "1px 1px 2px rgba(255,255,255,0.8)"
        main_text_override = main_text_color

        if wallpaper == "カスタム" and custom_data:
            bg_style = f"""
                background-image: linear-gradient(rgba(255,255,255,{bg_opacity}), rgba(255,255,255,{bg_opacity})), url("data:image/png;base64,{custom_data}") !important;
                background-attachment: fixed !important;
                background-size: cover !important;
                background-position: center !important;
            """
        else:
            wallpapers = {
                "草原": "1472214103451-9374bd1c798e", "夕焼け": "1472120435266-53107fd0c44a",
                "夜空": "1462331940025-496dfbfc7564", "ダンジョン": "1518709268805-4e9042af9f23",
                "王宮": "1544939514-aa98d908bc47", "図書館": "1521587760476-6c12a4b040da",
                "サイバー": "1535295972055-1c762f4483e5"
            }
            img_id = wallpapers.get(wallpaper, "1472214103451-9374bd1c798e")
            bg_url = f"https://images.unsplash.com/photo-{img_id}?auto=format&fit=crop&w=1920&q=80"
            bg_style = f"""
                background-image: linear-gradient(rgba(255,255,255,{bg_opacity}), rgba(255,255,255,{bg_opacity})), url("{bg_url}") !important;
                background-attachment: fixed !important;
                background-size: cover !important;
            """

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DotGothic16&family=Yomogi&family=Hachi+Maru+Pop&family=Shippori+Mincho&family=Yuji+Syuku&display=swap');
    
    [data-testid="stAppViewContainer"], .stApp {{ {bg_style} }}
    [data-testid="stHeader"] {{ background-color: rgba(0,0,0,0); }}

    /* サイドバー */
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg_color} !important;
        border-right: 1px solid #e0e0e0;
    }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown {{
        color: {sidebar_text_color} !important;
    }}
    [data-testid="stSidebar"] svg {{
        fill: {sidebar_text_color} !important;
        color: {sidebar_text_color} !important;
    }}
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {{
        color: #000000 !important; 
        background-color: #ffffff !important;
    }}
    /* 目標設定の赤枠 */
    [data-testid="stSidebar"] div[data-baseweb="input"] {{
        border: 2px solid #FF4B4B !important;
        background-color: #FFF0F0 !important;
        border-radius: 8px !important;
    }}
    [data-testid="stSidebar"] input {{
        color: #000000 !important;
        background-color: transparent !important;
    }}

    /* メイン画面フォント */
    html, body, [class*="css"] {{ font-family: {font_family} !important; }}
    
    /* メインエリア文字色 */
    .main .stMarkdown, .main .stText, .main h1, .main h2, .main h3, .main p, .main span {{ 
        color: {main_text_override} !important; 
        text-shadow: {shadow_color};
    }}
    
    /* 入力フォームのラベルを見やすく */
    .stMarkdown label, div[data-testid="stForm"] label, .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label {{
        color: {main_text_override} !important;
        font-weight: bold !important;
        text-shadow: {shadow_color};
    }}
    
    /* 入力ボックス自体は白背景・黒文字で統一 */
    input, textarea, select {{
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
        border-radius: 8px !important;
    }}
    div[data-baseweb="select"] > div {{ background-color: #ffffff !important; color: #000000 !important; }}
    div[data-baseweb="base-input"] {{ background-color: #ffffff !important; }}

    /* カードコンテナ (透明度やぼかしを排除し、シンプルなスタイルに) */
    div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stExpander"], div[data-testid="stForm"] {{
        background-color: {card_bg_color} !important;
        border: {border_style};
        border-radius: 15px; 
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }}

    /* ランキングカード */
    .ranking-card {{
        background: {card_bg_color};
        border: {border_style};
        border-radius: 12px; padding: 15px; margin-bottom: 12px; display: flex; align-items: center;
    }}
    .rank-medal {{ font-size: 28px; width: 60px; text-align: center; color: {accent_color} !important; }}
    .rank-info {{ flex-grow: 1; }}
    .rank-name {{ font-size: 1.2em; font-weight: bold; color: {main_text_override}; }}
    .rank-title {{ font-size: 0.85em; color: {accent_color}; }}
    .rank-score {{ font-size: 1.4em; font-weight: bold; color: {accent_color}; }}

    /* ショップ */
    .shop-title {{ font-size: 1.1em; font-weight: bold; color: {main_text_override}; margin-bottom: 5px; border-bottom: 1px solid #ccc; padding-bottom:3px; }}
    .shop-price {{ font-size: 1.0em; color: {accent_color}; font-weight: bold; margin-bottom: 8px; }}
    .shop-owned {{ color: {main_text_override}; border: 1px solid {main_text_override}; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; display: inline-block; font-weight:bold; }}

    /* HUD */
    .status-bar {{
        background: {card_bg_color};
        border: {border_style};
        padding: 15px; border-radius: 15px; 
        display: flex; justify-content: space-around; align-items: center; margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }}
    .stat-item {{ text-align: center; }}
    .stat-label {{ font-size: 0.7em; color: {main_text_override}; opacity: 0.8; letter-spacing: 1px; }}
    .stat-val {{ font-size: 1.6em; font-weight: bold; color: {main_text_override}; }}
    
    /* カレンダーの色補正 (重要) */
    .fc-col-header-cell-cushion, .fc-daygrid-day-number {{
        color: {main_text_override} !important; 
        text-decoration: none !important;
    }}
    .fc-event-title {{ color: #fff !important; }}
    
    button[kind="primary"] {{
        background: {accent_color} !important;
        border: none !important; box-shadow: 0 4px 10px rgba(0,0,0,0.2); font-weight: bold !important;
        color: #000000 !important;
    }}
    
    canvas {{ filter: invert(0) hue-rotate(0deg); }}
    </style>
    """, unsafe_allow_html=True)

# --- カラーパレット定義 ---
COLOR_PALETTE = {
    "#ffffff": "ホワイト (白)",
    "#1a1a1a": "ブラック (黒)",
    "#001f3f": "ミッドナイト",
    "#3d0000": "クリムゾン",
    "#003300": "ディープグリーン",
    "#2c003e": "ロイヤルパープル",
}

# --- 認証・DB操作 ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def login_user(username, password):
    try:
        res = supabase.table("users").select("password").eq("username", username).execute()
        if res.data and check_hashes(password, res.data[0]["password"]): return True, "成功"
        return False, "IDまたはパスワードが違います"
    except Exception as e: return False, f"エラー: {e}"

def add_user(username, password, nickname):
    try:
        data = {
            "username": username, "password": make_hashes(password), "nickname": nickname,
            "xp": 0, "coins": 0, 
            "unlocked_themes": "標準", "current_theme": "標準",
            "current_title": "見習い", "unlocked_titles": "見習い", 
            "current_wallpaper": "真っ白", "unlocked_wallpapers": "真っ白", 
            "custom_title_unlocked": False, "custom_wallpaper_unlocked": False,
            "custom_bg_data": None,
            "daily_goal": 60, "last_goal_reward_date": None, "last_login_date": None,
            "current_sidebar_color": "#ffffff", "unlocked_sidebar_colors": "#ffffff", 
            "main_text_color": "#000000", 
            "sidebar_text_color": "#000000",
            "accent_color": "#FFD700"
        }
        supabase.table("users").insert(data).execute()
        return True, "登録成功"
    except Exception as e:
        return False, f"SQLエラー: {e}"

def get_user_data(username):
    try:
        res = supabase.table("users").select("*").eq("username", username).execute()
        return res.data[0] if res.data else None
    except: return None

# --- その他DB操作 ---
def get_weekly_ranking():
    start = (datetime.now(JST) - timedelta(days=7)).strftime('%Y-%m-%d')
    try:
        logs = supabase.table("study_logs").select("username, duration_minutes").gte("study_date", start).execute()
        if not logs.data: return pd.DataFrame()
        df = pd.DataFrame(logs.data).groupby('username').sum().reset_index()
        users = supabase.table("users").select("username, nickname, current_title").execute()
        df_users = pd.DataFrame(users.data)
        merged = pd.merge(df, df_users, on='username', how='left')
        return merged.sort_values('duration_minutes', ascending=False)
    except: return pd.DataFrame()

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
    logs = supabase.table("study_logs").select("duration_minutes").eq("username", u).eq("study_date", today_str).execute()
    total_today = sum([l['duration_minutes'] for l in logs.data]) if logs.data else m
    
    new_xp = ud['xp'] + m
    new_coins = ud['coins'] + m
    
    goal_reached = False
    goal = ud.get('daily_goal', 60)
    last_reward = ud.get('last_goal_reward_date')
    
    if last_reward != today_str and total_today >= goal:
        new_coins += 100
        supabase.table("users").update({
            "xp": new_xp, "coins": new_coins, "last_goal_reward_date": today_str
        }).eq("username", u).execute()
        goal_reached = True
    else:
        supabase.table("users").update({"xp": new_xp, "coins": new_coins}).eq("username", u).execute()
        
    return m, new_xp, new_coins, goal_reached

def delete_study_log(lid, u, m):
    supabase.table("study_logs").delete().eq("id", lid).execute()
    ud = get_user_data(u)
    if ud: supabase.table("users").update({"xp": max(0, ud['xp']-m), "coins": max(0, ud['coins']-m)}).eq("username", u).execute()
    return True

def get_study_logs(u):
    res = supabase.table("study_logs").select("*").eq("username", u).order("created_at", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def get_tasks(u):
    res = supabase.table("tasks").select("*").eq("username", u).order("due_date").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def add_task(u, n, d, p): supabase.table("tasks").insert({"username": u, "task_name": n, "status": "未完了", "due_date": str(d), "priority": p}).execute()
def delete_task(tid): supabase.table("tasks").delete().eq("id", tid).execute()
def complete_task(tid, u):
    supabase.table("tasks").update({"status": "完了"}).eq("id", tid).execute()
    ud = get_user_data(u)
    if ud: supabase.table("users").update({"xp": ud['xp']+10, "coins": ud['coins']+10}).eq("username", u).execute()

# --- タイマー更新フラグメント ---
@st.fragment(run_every=1)
def show_timer_fragment(user_name):
    now = time.time()
    start = st.session_state.get("start_time", now)
    elapsed = int(now - start)
    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    
    st.markdown(f"""
    <div style="text-align: center; font-size: 6em; font-weight: bold; margin-bottom: 20px;">
        {h:02}:{m:02}:{s:02}
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("⏹️ 終了して記録", use_container_width=True, type="primary"):
            duration = max(1, elapsed // 60)
            _, _, _, reached = add_study_log(user_name, st.session_state.get("current_subject", "自習"), duration, date.today())
            st.session_state["is_studying"] = False
            st.session_state["celebrate"] = True
            st.session_state["toast_msg"] = f"{duration}分 記録しました！"
            if reached:
                st.session_state["goal_reached_msg"] = "🎉 目標達成！ +100コイン！"
            st.rerun()

# --- メイン処理 ---
def main():
    if "logged_in" not in st.session_state: 
        st.session_state.update({"logged_in": False, "username": "", "is_studying": False, "start_time": None, "celebrate": False, "toast_msg": None, "selected_date": str(date.today())})

    # 自動ログイン判定
    if not st.session_state["logged_in"]:
        try:
            auth_cookie = cookie_manager.get('logtask_auth')
            if auth_cookie:
                c_user, c_hash = auth_cookie.split(":", 1)
                res = supabase.table("users").select("password").eq("username", c_user).execute()
                if res.data and res.data[0]["password"] == c_hash:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = c_user
                    st.rerun()
        except:
            pass

    if not st.session_state["logged_in"]:
        st.title("🛡️ ログイン")
        mode = st.selectbox("モード", ["ログイン", "新規登録"])
        u = st.text_input("ユーザーID")
        p = st.text_input("パスワード", type="password")
        if mode == "新規登録":
            n = st.text_input("ニックネーム")
            if st.button("登録"):
                success, msg = add_user(u, p, n)
                if success: st.success(msg)
                else: st.error(msg)
        else:
            if st.button("ログイン"):
                res, msg = login_user(u, p)
                if res:
                    p_hash = make_hashes(p)
                    cookie_manager.set('logtask_auth', f"{u}:{p_hash}", expires_at=datetime.now() + timedelta(days=7))
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u
                    st.rerun()
                else: st.error(msg)
        return

    # ログイン後
    user = get_user_data(st.session_state["username"])
    if not user: st.session_state["logged_in"] = False; st.rerun()

    # 自動移行（初期化）
    if "真っ白" not in user.get('unlocked_wallpapers', ''):
        supabase.table("users").update({
            "unlocked_wallpapers": user.get('unlocked_wallpapers', '') + ",真っ白"
        }).eq("username", user['username']).execute()
        st.rerun()

    today_str = str(date.today())
    if user.get('last_login_date') != today_str:
        new_coins = user['coins'] + 50
        supabase.table("users").update({
            "coins": new_coins,
            "last_login_date": today_str
        }).eq("username", user['username']).execute()
        st.toast("🎁 ログインボーナス！ +50コイン GET！", icon="🎁")
        time.sleep(1)
        user['coins'] = new_coins

    # 変数初期化
    bg_darkness = 0.5
    container_opacity = 0.9

    # サイドバー (設定)
    with st.sidebar:
        st.subheader("⚙️ 設定")
        
        with st.expander("🎨 文字色カスタマイズ"):
            cur_main = user.get('main_text_color', '#000000')
            cur_acc = user.get('accent_color', '#FFD700')
            
            new_main = st.color_picker("メイン文字色", cur_main)
            new_acc = st.color_picker("アクセント色（強調）", cur_acc)
            
            if new_main != cur_main or new_acc != cur_acc:
                supabase.table("users").update({
                    "main_text_color": new_main,
                    "accent_color": new_acc
                }).eq("username", user['username']).execute()
                st.rerun()

        st.markdown("##### 🎚️ 表示調整")
        # ★真っ白のときはスライダーを表示しない、または無効化することで誤操作を防ぐ
        if user.get('current_wallpaper') == "真っ白":
            st.info("※「真っ白」テーマでは表示調整は無効です")
        else:
            bg_darkness = st.slider("背景の暗さ (画像時)", 0.0, 1.0, 0.5, 0.1, help="0: 明るい, 1: 暗い")
            container_opacity = st.slider("ウィンドウ不透明度", 0.0, 1.0, 0.9, 0.1, help="0: 透明, 1: 濃い")
        
        st.divider()

        # 目標設定
        st.markdown("##### 🎯 1日の目標")
        new_goal = st.number_input("目標時間(分)", min_value=10, max_value=600, value=user.get('daily_goal', 60), step=10)
        if new_goal != user.get('daily_goal', 60):
            if st.button("目標を保存"):
                supabase.table("users").update({"daily_goal": new_goal}).eq("username", user['username']).execute()
                st.success("保存しました"); time.sleep(0.5); st.rerun()
        
        st.divider()

        # 壁紙設定
        walls = user['unlocked_wallpapers'].split(',')
        if "真っ白" not in walls: walls.insert(0, "真っ白")
        
        if user.get('custom_wallpaper_unlocked'):
            bg_mode = st.radio("壁紙モード", ["プリセット", "カスタム画像"], horizontal=True, label_visibility="collapsed")
            if bg_mode == "カスタム画像":
                st.caption("画像をアップロードして壁紙に設定")
                uploaded_file = st.file_uploader("画像を選択", type=['jpg', 'png', 'jpeg'])
                if uploaded_file:
                    if st.button("この画像を適用"):
                        img = Image.open(uploaded_file)
                        img.thumbnail((1920, 1080))
                        b64_str = image_to_base64(img)
                        supabase.table("users").update({"current_wallpaper": "カスタム", "custom_bg_data": b64_str}).eq("username", user['username']).execute()
                        st.success("更新しました！"); time.sleep(1); st.rerun()
                elif user.get('current_wallpaper') == 'カスタム': st.success("カスタム画像適用中")
            else:
                current_w = user.get('current_wallpaper', '真っ白')
                if current_w == 'カスタム': current_w = "真っ白"
                new_w = st.selectbox("壁紙", walls, index=walls.index(current_w) if current_w in walls else 0)
                if new_w != user.get('current_wallpaper'):
                    supabase.table("users").update({"current_wallpaper": new_w}).eq("username", user['username']).execute()
                    st.rerun()
        else:
            current_w = user.get('current_wallpaper', '真っ白')
            if current_w not in walls: current_w = "真っ白"
            new_w = st.selectbox("壁紙", walls, index=walls.index(current_w) if current_w in walls else 0)
            if new_w != user.get('current_wallpaper'):
                supabase.table("users").update({"current_wallpaper": new_w}).eq("username", user['username']).execute()
                st.rerun()
        
        # フォント設定
        themes = user.get('unlocked_themes', '標準').split(',')
        new_t = st.selectbox("フォント", themes, index=themes.index(user.get('current_theme', '標準')) if user.get('current_theme') in themes else 0)
        if new_t != user.get('current_theme'):
            supabase.table("users").update({"current_theme": new_t}).eq("username", user['username']).execute()
            st.rerun()
            
        with st.expander("👑 称号コレクション"):
            my_titles = user.get('unlocked_titles', '見習い').split(',')
            current = user.get('current_title', '見習い')
            
            if user.get('custom_title_unlocked'):
                tab_list, tab_custom = st.tabs(["📜 リスト", "✏️ 自由入力"])
                with tab_list:
                    idx = my_titles.index(current) if current in my_titles else 0
                    sel_t = st.selectbox("獲得済み", my_titles, index=idx)
                    if st.button("装備", key="eq_list"):
                        supabase.table("users").update({"current_title": sel_t}).eq("username", user['username']).execute()
                        st.toast("装備を変更しました！"); time.sleep(1); st.rerun()
                with tab_custom:
                    custom_t = st.text_input("名前を入力", value=current)
                    if st.button("設定", key="eq_custom"):
                        supabase.table("users").update({"current_title": custom_t}).eq("username", user['username']).execute()
                        st.toast("称号を設定しました！"); time.sleep(1); st.rerun()
            else:
                idx = my_titles.index(current) if current in my_titles else 0
                sel_t = st.selectbox("獲得済み", my_titles, index=idx)
                if st.button("装備", key="eq_only_list"):
                    supabase.table("users").update({"current_title": sel_t}).eq("username", user['username']).execute()
                    st.toast("装備を変更しました！"); time.sleep(1); st.rerun()

        if st.button("ログアウト"):
            cookie_manager.delete('logtask_auth')
            st.session_state["logged_in"] = False
            st.rerun()

    # デザイン適用
    apply_design(
        user.get('current_theme', '標準'), 
        user.get('current_wallpaper', '真っ白'), 
        user.get('custom_bg_data'),
        bg_opacity=bg_darkness,
        container_opacity=container_opacity,
        main_text_color=user.get('main_text_color', '#000000'),
        accent_color=user.get('accent_color', '#FFD700')
    )

    # ★ 集中モード (BGM無し)
    if st.session_state["is_studying"]:
        st.empty()
        st.markdown(f"<h1 style='text-align: center; font-size: 3em;'>🔥 {st.session_state.get('current_subject', '勉強')} 中...</h1>", unsafe_allow_html=True)
        show_timer_fragment(user['username'])
        return

    # 本日の勉強時間取得
    logs_df = get_study_logs(user['username'])
    tasks = get_tasks(user['username'])
    
    today_mins = 0
    if not logs_df.empty:
        logs_df['d'] = logs_df['study_date'].astype(str).str.split("T").str[0]
        today_mins = logs_df[logs_df['d'] == str(date.today())]['duration_minutes'].sum()

    # ★HUD
    level = (user['xp'] // 100) + 1
    next_xp = level * 100
    goal = user.get('daily_goal', 60)
    goal_progress = min(1.0, today_mins / goal) if goal > 0 else 0
    
    # HUD
    card_bg_color = f"rgba(255, 255, 255, {container_opacity})" if user.get('main_text_color', '#000000').lower() != "#ffffff" else f"rgba(30, 30, 30, {container_opacity})"
    acc = user.get('accent_color', '#FFD700')
    main_txt = user.get('main_text_color', '#000000')
    
    st.markdown(f"""
    <div class="status-bar">
        <div class="stat-item"><div class="stat-label">PLAYER</div><div class="stat-val" style="font-size:1.2em; color:{main_txt};">{user['nickname']}</div><div style="font-size:0.7em; color:{acc};">{user.get('current_title', '見習い')}</div></div>
        <div class="stat-item"><div class="stat-label">LEVEL</div><div class="stat-val" style="color:#00e5ff;">{level}</div></div>
        <div class="stat-item"><div class="stat-label">XP</div><div class="stat-val" style="color:{main_txt};">{user['xp']} <span style="font-size:0.5em; opacity:0.7;">/ {next_xp}</span></div></div>
        <div class="stat-item"><div class="stat-label">COIN</div><div class="stat-val" style="color:{acc};">{user['coins']} G</div></div>
        <div class="stat-item" style="border-left:1px solid rgba(128,128,128,0.5); padding-left:15px;">
            <div class="stat-label">TODAY'S GOAL</div>
            <div class="stat-val" style="color:#ff9900;">{today_mins} <span style="font-size:0.5em; opacity:0.7;">/ {goal} min</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.progress(goal_progress)
    if today_mins >= goal and goal > 0:
        if user.get('last_goal_reward_date') == str(date.today()):
             st.caption("✅ 今日の目標達成済み！ボーナス獲得済み")
        else:
             st.caption("🔥 あと少しで目標達成！")

    # メイン画面
    if st.session_state.get("celebrate"): st.balloons(); st.session_state["celebrate"] = False
    if st.session_state.get("toast_msg"): st.toast(st.session_state["toast_msg"]); st.session_state["toast_msg"] = None
    if st.session_state.get("goal_reached_msg"):
        st.toast(st.session_state["goal_reached_msg"], icon="🎉")
        st.balloons()
        st.session_state["goal_reached_msg"] = None

    t1, t2, t3, t4, t5, t6 = st.tabs(["📝 ToDo", "⏱️ タイマー", "📊 分析", "🏆 ランキング", "🛒 ショップ", "📚 科目"])

    with t1: # ToDo & Calendar
        c1, c2 = st.columns([0.6, 0.4])
        events = []
        if not tasks.empty:
            for _, r in tasks.iterrows():
                color = "#FF4B4B" if r['status'] == '未完了' else "#888"
                events.append({"title": f"📝 {r['task_name']}", "start": r['due_date'], "color": color})
        if not logs_df.empty:
            for _, r in logs_df.iterrows():
                d_str = str(r['study_date']).split("T")[0]
                events.append({"title": f"📖 {r['subject']} ({r['duration_minutes']}分)", "start": d_str, "color": "#00CC00"})

        with c1:
            with st.container(border=True):
                st.subheader("📅 カレンダー")
                calendar_options = {
                    "editable": True,
                    "navLinks": True,
                    "headerToolbar": {
                        "left": "today prev,next",
                        "center": "title",
                        "right": "dayGridMonth,timeGridWeek,timeGridDay"
                    },
                    "initialView": "dayGridMonth",
                }
                # callbacksにeventClickを追加
                cal = calendar(events=events, options=calendar_options, callbacks=['dateClick', 'eventClick'])
                
                if cal.get('dateClick'):
                    st.session_state["selected_date"] = cal['dateClick']['date']
                
                # イベント詳細ポップアップ表示
                if cal.get('eventClick'):
                    e = cal['eventClick']['event']
                    show_event_info(e['title'], e['start'], e.get('backgroundColor', '#888'))
        
        with c2:
            with st.container(border=True):
                sel_date_raw = st.session_state.get("selected_date", str(date.today()))
                display_date = sel_date_raw.split("T")[0]
                st.markdown(f"### 📌 {display_date}")
                
                day_mins_sel = 0
                if not logs_df.empty:
                    day_logs = logs_df[logs_df['d'] == display_date]
                    day_mins_sel = day_logs['duration_minutes'].sum()
                    st.info(f"📚 **勉強時間: {day_mins_sel} 分**")
                
                st.write("📝 **タスク**")
                if not tasks.empty:
                    day_tasks = tasks[tasks['due_date'] == display_date]
                    if not day_tasks.empty:
                        for _, task in day_tasks.iterrows():
                            if task['status'] == "未完了":
                                if st.button(f"完了: {task['task_name']}", key=f"do_{task['id']}"):
                                    complete_task(task['id'], user['username']); st.rerun()
                            else: st.write(f"✅ {task['task_name']}")
                    else: st.caption("タスクなし")
                
                st.divider()
                with st.form("quick_add"):
                    tn = st.text_input("タスク追加")
                    # 日付指定
                    default_date = datetime.strptime(display_date, '%Y-%m-%d').date()
                    task_date = st.date_input("期日", value=default_date)
                    
                    if st.form_submit_button("追加"):
                        add_task(user['username'], tn, task_date, "中"); st.rerun()

    with t2: # タイマー
        c1, c2 = st.columns([1, 1])
        with c1:
            with st.container(border=True):
                st.subheader("🔥 集中モード")
                subs = get_subjects(user['username'])
                s_name = st.selectbox("科目", subs + ["その他"])
                if s_name == "その他": s_name = st.text_input("科目名入力")
                if st.button("スタート", type="primary", use_container_width=True):
                    if s_name:
                        st.session_state["is_studying"] = True
                        st.session_state["start_time"] = time.time()
                        st.session_state["current_subject"] = s_name
                        st.rerun()
        with c2:
            with st.container(border=True):
                st.subheader("✏️ 手動記録")
                with st.form("manual_log"):
                    md = st.date_input("日付")
                    col_h, col_m = st.columns(2)
                    with col_h: h = st.number_input("時間 (h)", 0, 23, 0)
                    with col_m: m = st.number_input("分 (m)", 0, 59, 0)
                    ms = st.text_input("科目", value=s_name if s_name != "その他" else "")
                    if st.form_submit_button("記録"):
                        total_min = h * 60 + m
                        if total_min > 0:
                            _, _, _, reached = add_study_log(user['username'], ms, total_min, md)
                            st.session_state["toast_msg"] = "記録しました！"
                            st.session_state["celebrate"] = True
                            if reached:
                                st.session_state["goal_reached_msg"] = "🎉 目標達成！ +100コイン！"
                            st.rerun()
                        else: st.error("時間を入力してください")
        
        with st.container(border=True):
            st.write("📖 **最近の記録**")
            if not logs_df.empty:
                for _, r in logs_df.head(5).iterrows():
                    lc1, lc2 = st.columns([0.8, 0.2])
                    d_str = str(r['study_date']).split("T")[0]
                    lc1.write(f"・{r['subject']} ({r['duration_minutes']}分) - {d_str}")
                    if lc2.button("削除", key=f"dl_{r['id']}"):
                        delete_study_log(r['id'], user['username'], r['duration_minutes']); st.rerun()

    with t3: # 分析
        with st.container(border=True):
            st.subheader("📊 学習データ分析")
            if not logs_df.empty:
                k1, k2 = st.columns(2)
                total_all = logs_df['duration_minutes'].sum()
                k1.metric("総勉強時間", f"{total_all//60}時間{total_all%60}分")
                k2.metric("今日の勉強時間", f"{today_mins}分")
                
                st.markdown("##### 📅 過去7日間の推移")
                logs_df['dt'] = pd.to_datetime(logs_df['study_date'])
                last_7 = pd.Timestamp.now(JST).normalize().tz_localize(None) - pd.Timedelta(days=6)
                recent = logs_df[logs_df['dt'] >= last_7].copy()
                if not recent.empty:
                    chart = alt.Chart(recent).mark_bar().encode(
                        x=alt.X('dt:T', title='日付', axis=alt.Axis(format='%m/%d')),
                        y=alt.Y('duration_minutes:Q', title='時間(分)'),
                        color=alt.Color('subject:N', title='科目'),
                        tooltip=['study_date', 'subject', 'duration_minutes']
                    ).properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
                else: st.info("直近のデータがありません")
                
                st.markdown("##### 📚 科目比率")
                sub_dist = logs_df.groupby('subject')['duration_minutes'].sum().reset_index()
                pie = alt.Chart(sub_dist).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="duration_minutes", type="quantitative"),
                    color=alt.Color(field="subject", type="nominal"),
                    tooltip=['subject', 'duration_minutes']
                ).properties(height=300)
                st.altair_chart(pie, use_container_width=True)
            else: st.info("データがありません")

    with t4: # ランキング
        with st.container(border=True):
            st.subheader("🏆 週間ランキング")
            df_rank = get_weekly_ranking()
            if not df_rank.empty:
                for i, row in df_rank.iterrows():
                    rank = i + 1
                    medal = "🥇" if rank==1 else "🥈" if rank==2 else "🥉" if rank==3 else f"{rank}位"
                    st.markdown(f"""
                    <div class="ranking-card">
                        <div class="rank-medal" style="color: {'#FFD700' if rank==1 else '#C0C0C0' if rank==2 else '#CD7F32' if rank==3 else '#fff'};">{medal}</div>
                        <div class="rank-info">
                            <div class="rank-name">{row['nickname']}</div>
                            <div class="rank-title">👑 {row.get('current_title', '見習い')}</div>
                        </div>
                        <div class="rank-score">{int(row['duration_minutes'])} min</div>
                    </div>
                    """, unsafe_allow_html=True)
            else: st.info("データなし")

    with t5: # ショップ (BGM完全削除)
        st.write("アイテムを購入してカスタマイズしよう！")
        
        st.markdown("### 🅰️ フォント")
        font_items = [("ピクセル風", 500), ("手書き風", 800), ("ポップ", 1000), ("明朝体", 1200), ("筆文字", 1500)]
        cols = st.columns(3)
        my_fonts = user.get('unlocked_themes', '標準').split(',')
        for i, (n, p) in enumerate(font_items):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"<div class='shop-title'>{n}</div>", unsafe_allow_html=True)
                    if n in my_fonts:
                        st.markdown(f"<span class='shop-owned'>所有済み</span>", unsafe_allow_html=True)
                        st.button("設定へ", disabled=True, key=f"df_{n}")
                    else:
                        st.markdown(f"<div class='shop-price'>{p} G</div>", unsafe_allow_html=True)
                        if st.button("購入", key=f"buy_f_{n}", use_container_width=True):
                            if user['coins'] >= p:
                                nl = user['unlocked_themes'] + f",{n}"
                                supabase.table("users").update({"coins": user['coins']-p, "unlocked_themes": nl}).eq("username", user['username']).execute()
                                st.balloons(); st.rerun()
                            else: st.error("コイン不足")

        st.markdown("### 🖼️ 壁紙")
        items = [("真っ黒", 500), ("草原", 500), ("夕焼け", 500), ("夜空", 800), ("ダンジョン", 1200), ("王宮", 2000)]
        cols = st.columns(2)
        for i, (n, p) in enumerate(items):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"<div class='shop-title'>{n}</div>", unsafe_allow_html=True)
                    if n in user['unlocked_wallpapers']:
                        st.markdown(f"<span class='shop-owned'>所有済み</span>", unsafe_allow_html=True)
                        st.button("設定へ", disabled=True, key=f"d_{n}")
                    else:
                        st.markdown(f"<div class='shop-price'>{p} G</div>", unsafe_allow_html=True)
                        if st.button("購入", key=f"buy_w_{n}", use_container_width=True):
                            if user['coins'] >= p:
                                nl = user['unlocked_wallpapers'] + f",{n}"
                                supabase.table("users").update({"coins": user['coins']-p, "unlocked_wallpapers": nl}).eq("username", user['username']).execute()
                                st.balloons(); st.rerun()
                            else: st.error("コイン不足")

        st.markdown("### 💎 その他")
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("<div class='shop-title'>🎲 称号ガチャ</div>", unsafe_allow_html=True)
                st.markdown("<div class='shop-price'>100 G</div>", unsafe_allow_html=True)
                if st.button("ガチャを回す", type="primary", use_container_width=True):
                    if user['coins'] >= 100:
                        got = random.choice(["駆け出し", "努力家", "集中王", "夜更かし", "天才", "覚醒者", "大賢者", "神童"])
                        current = user.get('unlocked_titles', '')
                        if got not in current: current += f",{got}"
                        supabase.table("users").update({"coins": user['coins']-100, "unlocked_titles": current, "current_title": got}).eq("username", user['username']).execute()
                        st.toast(f"🎉 称号『{got}』を獲得しました！"); st.balloons(); time.sleep(1); st.rerun()
                    else: st.error("コイン不足")
        
        with c2:
            with st.container(border=True):
                st.markdown("<div class='shop-title'>👑 自由称号パス</div>", unsafe_allow_html=True)
                st.markdown("<div class='shop-price'>9999 G</div>", unsafe_allow_html=True)
                if user.get('custom_title_unlocked'):
                    st.button("✅ 購入済み", disabled=True, use_container_width=True, key="done_pass")
                else:
                    if st.button("パスを購入", key="buy_pass", use_container_width=True):
                        if user['coins'] >= 9999:
                            supabase.table("users").update({"coins": user['coins']-9999, "custom_title_unlocked": True}).eq("username", user['username']).execute()
                            st.balloons(); st.rerun()
                        else: st.error("不足")
                        
            with st.container(border=True):
                st.markdown("<div class='shop-title'>🖼️ カスタム壁紙パス</div>", unsafe_allow_html=True)
                st.markdown("<div class='shop-price'>9999 G</div>", unsafe_allow_html=True)
                if user.get('custom_wallpaper_unlocked'):
                    st.button("✅ 購入済み", disabled=True, use_container_width=True, key="buy_wp_done")
                else:
                    if st.button("パスを購入", key="buy_wp_pass", use_container_width=True):
                        if user['coins'] >= 9999:
                            supabase.table("users").update({"coins": user['coins']-9999, "custom_wallpaper_unlocked": True}).eq("username", user['username']).execute()
                            st.balloons(); st.rerun()
                        else: st.error("不足")

    with t6: # 科目
        new_s = st.text_input("科目追加")
        if st.button("追加"):
            if new_s: add_subject_db(user['username'], new_s); st.rerun()
        st.write("登録済み:")
        for s in get_subjects(user['username']):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(s)
            if c2.button("削除", key=f"d_{s}"): delete_subject_db(user['username'], s); st.rerun()

if __name__ == "__main__":
    main()
