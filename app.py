import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random
import time
from datetime import datetime, date, timedelta, timezone
from streamlit_calendar import calendar
import altair as alt
from PIL import Image
import io
import base64

# ページ設定
st.set_page_config(page_title="褒めてくれる勉強時間・タスク管理アプリ", layout="wide")

# --- 日本時間 (JST) の定義 ---
JST = timezone(timedelta(hours=9))

# --- BGMデータ ---
BGM_DATA = {
    "なし": None,
    "雨の音": {"url": "https://upload.wikimedia.org/wikipedia/commons/8/8f/Rain_falling_on_leaves.ogg", "type": "audio/ogg"},
    "焚き火": {"url": "https://upload.wikimedia.org/wikipedia/commons/6/66/Fire_crackling_sound_effect.ogg", "type": "audio/ogg"},
    "カフェ": {"url": "https://upload.wikimedia.org/wikipedia/commons/5/52/Cafeteria_noise.ogg", "type": "audio/ogg"},
    "川のせせらぎ": {"url": "https://upload.wikimedia.org/wikipedia/commons/5/54/River_Snoring_Forest_Nature_Sounds.ogg", "type": "audio/ogg"},
    "ホワイトノイズ": {"url": "https://upload.wikimedia.org/wikipedia/commons/9/98/White_Noise.ogg", "type": "audio/ogg"}
}

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

# --- 画像処理関数 ---
def image_to_base64(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# --- デザイン適用関数 ---
def apply_design(user_theme="標準", wallpaper="草原", custom_data=None, bg_opacity=0.4):
    fonts = {
        "ピクセル風": "'DotGothic16', sans-serif",
        "手書き風": "'Yomogi', cursive",
        "ポップ": "'Hachi Maru Pop', cursive",
        "明朝体": "'Shippori Mincho', serif",
        "筆文字": "'Yuji Syuku', serif",
        "標準": "sans-serif"
    }
    font_family = fonts.get(user_theme, "sans-serif")
    
    # 壁紙ロジック
    bg_css = "background-color: #1E1E1E;" # デフォルト
    
    if wallpaper == "カスタム" and custom_data:
        # ユーザーのカスタム画像を使用
        bg_css = f"""
            background-image: linear-gradient(rgba(0,0,0,{bg_opacity}), rgba(0,0,0,{bg_opacity})), url("data:image/png;base64,{custom_data}");
            background-attachment: fixed; background-size: cover; background-position: center;
        """
    else:
        # プリセット画像を使用
        wallpapers = {
            "草原": "1472214103451-9374bd1c798e", "夕焼け": "1472120435266-53107fd0c44a",
            "夜空": "1462331940025-496dfbfc7564", "ダンジョン": "1518709268805-4e9042af9f23",
            "王宮": "1544939514-aa98d908bc47", "図書館": "1521587760476-6c12a4b040da",
            "サイバー": "1535295972055-1c762f4483e5", "シンプル": ""
        }
        # 指定がない、または辞書にない場合は「草原」をデフォルトにする
        if wallpaper not in wallpapers: wallpaper = "草原"
        
        img_id = wallpapers.get(wallpaper, "")
        if img_id:
            bg_url = f"https://images.unsplash.com/photo-{img_id}?auto=format&fit=crop&w=1920&q=80"
            bg_css = f"""
                background-image: linear-gradient(rgba(0,0,0,{bg_opacity}), rgba(0,0,0,{bg_opacity})), url("{bg_url}");
                background-attachment: fixed; background-size: cover;
            """

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DotGothic16&family=Yomogi&family=Hachi+Maru+Pop&family=Shippori+Mincho&family=Yuji+Syuku&display=swap');
    
    .stApp {{ {bg_css} }}
    html, body, [class*="css"] {{ font-family: {font_family} !important; color: #ffffff; }}
    .stMarkdown, .stText, h1, h2, h3, p, span, div {{ color: #ffffff !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }}
    
    div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stExpander"], div[data-testid="stForm"] {{
        background-color: rgba(30, 30, 30, 0.85) !important;
        border-radius: 15px; padding: 20px; border: 1px solid rgba(255,255,255,0.15);
        box-shadow: 0 4px 15px rgba(0,0,0,0.5); backdrop-filter: blur(5px);
    }}

    .ranking-card {{
        background: linear-gradient(90deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));
        border-radius: 12px; padding: 15px; margin-bottom: 12px; display: flex; align-items: center;
        border: 1px solid rgba(255,255,255,0.2);
    }}
    .rank-medal {{ font-size: 28px; width: 60px; text-align: center; }}
    .rank-info {{ flex-grow: 1; }}
    .rank-name {{ font-size: 1.2em; font-weight: bold; color: #fff; }}
    .rank-title {{ font-size: 0.85em; color: #FFD700; }}
    .rank-score {{ font-size: 1.4em; font-weight: bold; color: #00FF00; text-shadow: 0 0 10px rgba(0,255,0,0.5); }}

    .shop-title {{ font-size: 1.1em; font-weight: bold; color: #fff; margin-bottom: 5px; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom:3px; }}
    .shop-price {{ font-size: 1.0em; color: #FFD700; font-weight: bold; margin-bottom: 8px; }}
    .shop-owned {{ color: #00FF00; border: 1px solid #00FF00; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; display: inline-block; font-weight:bold; }}

    .status-bar {{
        background: linear-gradient(90deg, #1a1a1a, #2d2d2d);
        padding: 15px; border-radius: 15px; border: 2px solid #444;
        display: flex; justify-content: space-around; align-items: center; margin-bottom: 20px;
        box-shadow: 0 0 15px rgba(0,0,0,0.8);
    }}
    .stat-item {{ text-align: center; }}
    .stat-label {{ font-size: 0.7em; color: #aaa; letter-spacing: 1px; }}
    .stat-val {{ font-size: 1.6em; font-weight: bold; color: #fff; text-shadow: 0 0 5px rgba(255,255,255,0.5); }}
    
    button[kind="primary"] {{
        background: linear-gradient(45deg, #FF4B4B, #FF914D) !important;
        border: none !important; box-shadow: 0 4px 10px rgba(255, 75, 75, 0.4); font-weight: bold !important;
    }}
    
    canvas {{ filter: invert(1) hue-rotate(180deg); }}
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
        data = {"username": username, "password": make_hashes(password), "nickname": nickname,
                "xp": 0, "coins": 0, "unlocked_themes": "標準", "current_theme": "標準",
                "current_title": "見習い", "unlocked_titles": "見習い", 
                "current_wallpaper": "草原", "unlocked_wallpapers": "草原",
                "current_bgm": "なし", "unlocked_bgm": "なし", 
                "custom_title_unlocked": False, "custom_wallpaper_unlocked": False}
        supabase.table("users").insert(data).execute()
        return True
    except: return False

def get_user_data(username):
    try:
        res = supabase.table("users").select("*").eq("username", username).execute()
        return res.data[0] if res.data else None
    except: return None

# --- ランキング ---
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

# --- 科目 ---
def get_subjects(username):
    try:
        res = supabase.table("subjects").select("subject_name").eq("username", username).execute()
        return [r['subject_name'] for r in res.data]
    except: return []

def add_subject_db(u, s): supabase.table("subjects").insert({"username": u, "subject_name": s}).execute()
def delete_subject_db(u, s): supabase.table("subjects").delete().eq("username", u).eq("subject_name", s).execute()

# --- ログ・タスク ---
def add_study_log(u, s, m, d):
    supabase.table("study_logs").insert({"username": u, "subject": s, "duration_minutes": m, "study_date": str(d)}).execute()
    ud = get_user_data(u)
    if ud: supabase.table("users").update({"xp": ud['xp']+m, "coins": ud['coins']+m}).eq("username", u).execute()
    return m, ud['xp']+m, ud['coins']+m

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
    <div style="text-align: center; font-size: 6em; font-weight: bold; color: #00FF00; text-shadow: 0 0 20px #00FF00; margin-bottom: 20px;">
        {h:02}:{m:02}:{s:02}
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("⏹️ 終了して記録", use_container_width=True, type="primary"):
            duration = max(1, elapsed // 60)
            add_study_log(user_name, st.session_state.get("current_subject", "自習"), duration, date.today())
            st.session_state["is_studying"] = False
            st.session_state["celebrate"] = True
            st.session_state["toast_msg"] = f"{duration}分 記録しました！"
            st.rerun()

# --- メイン処理 ---
def main():
    if "logged_in" not in st.session_state: 
        st.session_state.update({"logged_in": False, "username": "", "is_studying": False, "start_time": None, "celebrate": False, "toast_msg": None, "selected_date": str(date.today())})

    if not st.session_state["logged_in"]:
        st.title("🛡️ ログイン")
        mode = st.selectbox("モード", ["ログイン", "新規登録"])
        u = st.text_input("ユーザーID")
        p = st.text_input("パスワード", type="password")
        if mode == "新規登録":
            n = st.text_input("ニックネーム")
            if st.button("登録"):
                if add_user(u, p, n): st.success("登録成功！")
                else: st.error("エラー")
        else:
            if st.button("ログイン"):
                res, msg = login_user(u, p)
                if res:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u
                    st.rerun()
                else: st.error(msg)
        return

    # ログイン後
    user = get_user_data(st.session_state["username"])
    if not user: st.session_state["logged_in"] = False; st.rerun()

    # デザイン適用 (カスタム壁紙データも渡す)
    apply_design(
        user_theme=user.get('current_theme', '標準'), 
        wallpaper=user.get('current_wallpaper', '草原'),
        custom_data=user.get('custom_bg_data')
    )

    # BGM再生
    if st.session_state["is_studying"]:
        st.empty()
        bgm_key = user.get('current_bgm', 'なし')
        if bgm_key != 'なし' and BGM_DATA.get(bgm_key):
            bgm_info = BGM_DATA[bgm_key]
            st.audio(bgm_info["url"], format=bgm_info["type"], loop=True, autoplay=True)
            st.caption(f"🎵 Now Playing: {bgm_key}")
            
        st.markdown(f"<h1 style='text-align: center; font-size: 3em;'>🔥 {st.session_state.get('current_subject', '勉強')} 中...</h1>", unsafe_allow_html=True)
        show_timer_fragment(user['username'])
        return

    # HUD
    level = (user['xp'] // 100) + 1
    next_xp = level * 100
    st.markdown(f"""
    <div class="status-bar">
        <div class="stat-item"><div class="stat-label">PLAYER</div><div class="stat-val" style="font-size:1.2em;">{user['nickname']}</div><div style="font-size:0.7em; color:gold;">{user.get('current_title', '見習い')}</div></div>
        <div class="stat-item"><div class="stat-label">LEVEL</div><div class="stat-val" style="color:#00e5ff;">{level}</div></div>
        <div class="stat-item"><div class="stat-label">XP</div><div class="stat-val">{user['xp']} <span style="font-size:0.5em; color:#888;">/ {next_xp}</span></div></div>
        <div class="stat-item"><div class="stat-label">COIN</div><div class="stat-val" style="color:#FFD700;">{user['coins']} G</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(min(1.0, (user['xp'] % 100) / 100))

    # サイドバー
    with st.sidebar:
        st.subheader("⚙️ 設定")
        
        # 壁紙設定 (カスタム対応)
        walls = user['unlocked_wallpapers'].split(',')
        if user.get('custom_wallpaper_unlocked'):
            # カスタム機能がオンの場合
            bg_mode = st.radio("壁紙モード", ["プリセット", "カスタム画像"], horizontal=True, label_visibility="collapsed")
            
            if bg_mode == "カスタム画像":
                st.caption("画像をアップロードして壁紙に設定")
                uploaded_file = st.file_uploader("画像を選択", type=['jpg', 'png', 'jpeg'])
                if uploaded_file:
                    if st.button("この画像を適用"):
                        # 画像処理: 読み込んでリサイズしてBase64化
                        img = Image.open(uploaded_file)
                        img.thumbnail((1920, 1080)) # サイズ軽量化
                        b64_str = image_to_base64(img)
                        # DB保存
                        supabase.table("users").update({
                            "current_wallpaper": "カスタム",
                            "custom_bg_data": b64_str
                        }).eq("username", user['username']).execute()
                        st.success("壁紙を更新しました！")
                        time.sleep(1)
                        st.rerun()
                elif user.get('current_wallpaper') == 'カスタム':
                    st.success("現在カスタム画像適用中")
            else:
                # プリセット選択モード
                new_w = st.selectbox("壁紙", walls, index=walls.index(user.get('current_wallpaper', '草原')) if user.get('current_wallpaper') in walls else 0)
                if new_w != user.get('current_wallpaper'):
                    supabase.table("users").update({"current_wallpaper": new_w}).eq("username", user['username']).execute()
                    st.rerun()
        else:
            # 通常モード
            new_w = st.selectbox("壁紙", walls, index=walls.index(user.get('current_wallpaper', '草原')) if user.get('current_wallpaper') in walls else 0)
            if new_w != user.get('current_wallpaper'):
                supabase.table("users").update({"current_wallpaper": new_w}).eq("username", user['username']).execute()
                st.rerun()
        
        # フォント設定
        themes = user.get('unlocked_themes', '標準').split(',')
        new_t = st.selectbox("フォント", themes, index=themes.index(user.get('current_theme', '標準')) if user.get('current_theme') in themes else 0)
        if new_t != user.get('current_theme'):
            supabase.table("users").update({"current_theme": new_t}).eq("username", user['username']).execute()
            st.rerun()

        # BGM設定
        bgms = user.get('unlocked_bgm', 'なし').split(',')
        if 'なし' not in bgms: bgms.insert(0, 'なし')
        new_b = st.selectbox("集中BGM設定", bgms, index=bgms.index(user.get('current_bgm', 'なし')) if user.get('current_bgm') in bgms else 0)
        if new_b != user.get('current_bgm'):
            supabase.table("users").update({"current_bgm": new_b}).eq("username", user['username']).execute()
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

        if st.button("ログアウト"): st.session_state["logged_in"] = False; st.rerun()

    # メイン画面
    if st.session_state.get("celebrate"): st.balloons(); st.session_state["celebrate"] = False
    if st.session_state.get("toast_msg"): st.toast(st.session_state["toast_msg"]); st.session_state["toast_msg"] = None

    t1, t2, t3, t4, t5, t6 = st.tabs(["📝 ToDo", "⏱️ タイマー", "📊 分析", "🏆 ランキング", "🛒 ショップ", "📚 科目"])

    with t1: # ToDo & Calendar
        c1, c2 = st.columns([0.6, 0.4])
        tasks = get_tasks(user['username'])
        logs = get_study_logs(user['username'])
        events = []
        if not tasks.empty:
            for _, r in tasks.iterrows():
                color = "#FF4B4B" if r['status'] == '未完了' else "#888"
                events.append({"title": f"📝 {r['task_name']}", "start": r['due_date'], "color": color})
        if not logs.empty:
            for _, r in logs.iterrows():
                d_str = str(r['study_date'])[:10]
                events.append({"title": f"📖 {r['subject']} ({r['duration_minutes']}分)", "start": d_str, "color": "#00CC00"})

        with c1:
            st.subheader("📅 カレンダー")
            cal = calendar(events=events, options={"initialView": "dayGridMonth", "height": 500}, callbacks=['dateClick'])
            if cal.get('dateClick'): st.session_state["selected_date"] = cal['dateClick']['date']
        
        with c2:
            sel_date_raw = st.session_state.get("selected_date", str(date.today()))
            display_date = sel_date_raw.split("T")[0]
            st.markdown(f"### 📌 {display_date}")
            
            day_mins = 0
            if not logs.empty:
                logs['short_date'] = logs['study_date'].astype(str).str[:10]
                day_logs = logs[logs['short_date'] == display_date]
                day_mins = day_logs['duration_minutes'].sum()
                st.info(f"📚 **勉強時間: {day_mins} 分**")
            
            st.write("📝 **タスク**")
            if not tasks.empty:
                day_tasks = tasks[tasks['due_date'] == display_date]
                if not day_tasks.empty:
                    for _, task in day_tasks.iterrows():
                        if task['status'] == "未完了":
                            if st.button(f"完了: {task['task_name']}", key=f"do_{task['id']}"):
                                complete_task(task['id'], user['username'])
                                st.rerun()
                        else: st.write(f"✅ {task['task_name']}")
                else: st.caption("タスクなし")
            
            st.divider()
            with st.form("quick_add"):
                tn = st.text_input("タスク追加")
                if st.form_submit_button("追加"):
                    add_task(user['username'], tn, display_date, "中")
                    st.rerun()

    with t2: # タイマー & 手動記録
        c1, c2 = st.columns([1, 1])
        with c1:
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
                        add_study_log(user['username'], ms, total_min, md)
                        st.session_state["toast_msg"] = "記録しました！"
                        st.session_state["celebrate"] = True
                        st.rerun()
                    else: st.error("時間を入力してください")
        
        st.divider()
        st.write("📖 **最近の記録**")
        if not logs.empty:
            for _, r in logs.head(5).iterrows():
                lc1, lc2 = st.columns([0.8, 0.2])
                d_str = str(r['study_date'])[:10]
                lc1.write(f"・{r['subject']} ({r['duration_minutes']}分) - {d_str}")
                if lc2.button("削除", key=f"dl_{r['id']}"):
                    delete_study_log(r['id'], user['username'], r['duration_minutes'])
                    st.rerun()

    with t3: # 分析
        st.subheader("📊 学習データ分析")
        if not logs.empty:
            logs['study_date'] = pd.to_datetime(logs['study_date'])
            today = pd.Timestamp.now(JST).normalize().tz_localize(None)
            
            total_min = logs['duration_minutes'].sum()
            today_min = logs[logs['study_date'] == today]['duration_minutes'].sum()
            k1, k2 = st.columns(2)
            k1.metric("総勉強時間", f"{total_min//60}時間{total_min%60}分")
            k2.metric("今日の勉強時間", f"{today_min}分")
            
            st.markdown("##### 📅 過去7日間の推移")
            last_7 = today - pd.Timedelta(days=6)
            recent = logs[logs['study_date'] >= last_7].copy()
            if not recent.empty:
                chart = alt.Chart(recent).mark_bar().encode(
                    x=alt.X('study_date:T', title='日付', axis=alt.Axis(format='%m/%d')),
                    y=alt.Y('duration_minutes:Q', title='時間(分)'),
                    color=alt.Color('subject:N', title='科目'),
                    tooltip=['study_date', 'subject', 'duration_minutes']
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)
            else: st.info("直近のデータがありません")
            
            st.markdown("##### 📚 科目比率")
            sub_dist = logs.groupby('subject')['duration_minutes'].sum().reset_index()
            pie = alt.Chart(sub_dist).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="duration_minutes", type="quantitative"),
                color=alt.Color(field="subject", type="nominal"),
                tooltip=['subject', 'duration_minutes']
            ).properties(height=300)
            st.altair_chart(pie, use_container_width=True)
        else: st.info("データがありません")

    with t4: # ランキング
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

    with t5: # ショップ
        st.write("アイテムを購入してカスタマイズしよう！")
        
        # フォントショップ
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
        items = [("夕焼け", 500), ("夜空", 800), ("ダンジョン", 1200), ("王宮", 2000)]
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

        st.markdown("### 🎵 BGM")
        items = [("雨の音", 300), ("焚き火", 500), ("カフェ", 800)]
        cols = st.columns(3)
        my_bgms = user.get('unlocked_bgm', 'なし')
        for i, (n, p) in enumerate(items):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"<div class='shop-title'>{n}</div>", unsafe_allow_html=True)
                    if n in my_bgms:
                        st.markdown(f"<span class='shop-owned'>所有済み</span>", unsafe_allow_html=True)
                        st.button("設定へ", disabled=True, key=f"db_{n}")
                    else:
                        st.markdown(f"<div class='shop-price'>{p} G</div>", unsafe_allow_html=True)
                        if st.button("購入", key=f"buy_b_{n}", use_container_width=True):
                            if user['coins'] >= p:
                                nl = my_bgms + f",{n}"
                                supabase.table("users").update({"coins": user['coins']-p, "unlocked_bgm": nl}).eq("username", user['username']).execute()
                                st.balloons(); st.rerun()
                            else: st.error("コイン不足")

        st.markdown("### 💎 その他")
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("<div class='shop-title'>🎲 称号ガチャ</div>", unsafe_allow_html=True)
                st.markdown("<div class='shop-price'>100 G</div>", unsafe_allow_html=True)
                st.caption("ランダムな称号をゲット！")
                if st.button("ガチャを回す", type="primary", use_container_width=True):
                    if user['coins'] >= 100:
                        got = random.choice(["駆け出し", "努力家", "集中王", "夜更かし", "天才", "覚醒者", "大賢者", "神童"])
                        current = user.get('unlocked_titles', '')
                        if got not in current: current += f",{got}"
                        supabase.table("users").update({"coins": user['coins']-100, "unlocked_titles": current, "current_title": got}).eq("username", user['username']).execute()
                        st.toast(f"🎉 称号『{got}』を獲得しました！")
                        st.balloons(); time.sleep(1); st.rerun()
                    else: st.error("コイン不足")
        
        with c2:
            with st.container(border=True):
                st.markdown("<div class='shop-title'>👑 自由称号パス</div>", unsafe_allow_html=True)
                st.markdown("<div class='shop-price'>9999 G</div>", unsafe_allow_html=True)
                st.caption("好きな称号を自由に設定可能！")
                if user.get('custom_title_unlocked'):
                    st.button("✅ 購入済み", disabled=True, use_container_width=True)
                else:
                    if st.button("パスを購入", key="buy_pass", use_container_width=True):
                        if user['coins'] >= 9999:
                            supabase.table("users").update({"coins": user['coins']-9999, "custom_title_unlocked": True}).eq("username", user['username']).execute()
                            st.balloons(); st.rerun()
                        else: st.error("不足")
                        
            # 新アイテム: カスタム壁紙パス
            with st.container(border=True):
                st.markdown("<div class='shop-title'>🖼️ カスタム壁紙パス</div>", unsafe_allow_html=True)
                st.markdown("<div class='shop-price'>9999 G</div>", unsafe_allow_html=True)
                st.caption("好きな画像を壁紙にできる！")
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
