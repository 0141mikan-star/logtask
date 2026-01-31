import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random
import time
from datetime import datetime, date, timedelta, timezone
import urllib.parse
import hashlib
from streamlit_calendar import calendar

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

if not supabase:
    st.error("Supabaseへの接続設定が見つかりません。")
    st.stop()

# --- デザイン適用関数 ---
def apply_font(font_type):
    fonts = {
        "ピクセル風": ("DotGothic16", "sans-serif"),
        "手書き風": ("Yomogi", "cursive"),
        "ポップ": ("Hachi+Maru+Pop", "cursive"),
        "明朝体": ("Shippori+Mincho", "serif"),
        "筆文字": ("Yuji+Syuku", "serif")
    }
    if font_type in fonts:
        name, fallback = fonts[font_type]
        st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family={name}&display=swap');
        body, p, h1, h2, h3, h4, h5, h6, input, textarea, label, button, .stTooltip, .stExpander {{
            font-family: '{name}', {fallback} !important;
        }}
        </style>
        """, unsafe_allow_html=True)

def apply_wallpaper(wallpaper_name, bg_opacity=0.3):
    wallpapers = {
        "草原": "1472214103451-9374bd1c798e", "夕焼け": "1472120435266-53107fd0c44a",
        "夜空": "1462331940025-496dfbfc7564", "ダンジョン": "1518709268805-4e9042af9f23",
        "王宮": "1544939514-aa98d908bc47", "図書館": "1521587760476-6c12a4b040da",
        "サイバー": "1535295972055-1c762f4483e5"
    }
    bg_css = f"background-color: #1E1E1E;"
    if wallpaper_name in wallpapers:
        id = wallpapers[wallpaper_name]
        url = f"https://images.unsplash.com/photo-{id}?auto=format&fit=crop&w=1920&q=80"
        bg_css += f'background-image: linear-gradient(rgba(0,0,0,{bg_opacity}), rgba(0,0,0,{bg_opacity})), url("{url}"); background-attachment: fixed; background-size: cover;'
    
    st.markdown(f"""
    <style>
    .stApp {{ {bg_css} }}
    .stMarkdown, .stText, h1, h2, h3, p, span, div {{ color: #ffffff !important; text-shadow: 1px 1px 3px rgba(0,0,0,0.8); }}
    div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stExpander"], div[data-testid="stForm"], .task-container-box, .ranking-card {{
        background-color: rgba(20, 20, 20, 0.9) !important; border-radius: 12px; padding: 15px; border: 1px solid rgba(255,255,255,0.3);
    }}
    button[data-baseweb="tab"] {{ background-color: rgba(20, 20, 20, 0.9) !important; color: white !important; }}
    button[aria-selected="true"] {{ background-color: #FF4B4B !important; }}
    label {{ color: #FFD700 !important; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

# --- 認証・DB操作 ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def login_user(username, password):
    try:
        username = username.strip()
        response = supabase.table("users").select("password").eq("username", username).execute()
        if response.data:
            if check_hashes(password, response.data[0]["password"]):
                return True, "成功"
        return False, "ユーザー名かパスワードが違います"
    except Exception as e:
        return False, f"エラー: {e}"

def add_user(username, password, nickname):
    try:
        data = {
            "username": username.strip(),
            "password": make_hashes(password.strip()),
            "nickname": nickname.strip(),
            "xp": 0, "coins": 0, "unlocked_themes": "標準",
            "current_title": "見習い", "unlocked_titles": "見習い",
            "current_wallpaper": "草原", "unlocked_wallpapers": "草原",
            "custom_title_unlocked": False
        }
        supabase.table("users").insert(data).execute()
        return True
    except:
        return False

def get_user_data(username):
    try:
        res = supabase.table("users").select("*").eq("username", username).execute()
        return res.data[0] if res.data else None
    except: return None

def get_tasks(username):
    try:
        res = supabase.table("tasks").select("*").eq("username", username).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['status_rank'] = df['status'].apply(lambda x: 1 if x == '未完了' else 2)
            df = df.sort_values(by=['status_rank', 'created_at'])
        return df
    except: return pd.DataFrame()

def add_task(username, name, date, prio):
    supabase.table("tasks").insert({"username": username, "task_name": name, "status": "未完了", "due_date": str(date), "priority": prio}).execute()

def complete_tasks_bulk(ids, username, amount):
    supabase.table("tasks").update({"status": "完了"}).in_("id", ids).execute()
    u = get_user_data(username)
    if u: supabase.table("users").update({"xp": u['xp'] + amount, "coins": u['coins'] + amount}).eq("username", username).execute()

def delete_task(tid):
    supabase.table("tasks").delete().eq("id", tid).execute()

def add_study_log(username, subj, mins):
    date_str = datetime.now(JST).strftime('%Y-%m-%d')
    supabase.table("study_logs").insert({"username": username, "subject": subj, "duration_minutes": mins, "study_date": date_str}).execute()
    u = get_user_data(username)
    if u: supabase.table("users").update({"xp": u['xp'] + mins, "coins": u['coins'] + mins}).eq("username", username).execute()

def delete_study_log(lid, username, mins):
    supabase.table("study_logs").delete().eq("id", lid).execute()
    u = get_user_data(username)
    if u: supabase.table("users").update({"xp": max(0, u['xp'] - mins), "coins": max(0, u['coins'] - mins)}).eq("username", username).execute()

def get_study_logs(username):
    try:
        res = supabase.table("study_logs").select("*").eq("username", username).execute()
        df = pd.DataFrame(res.data)
        return df.sort_values('created_at', ascending=False) if not df.empty else df
    except: return pd.DataFrame()

# ガチャリスト
GACHA_TITLES = ["駆け出し冒険者", "夜更かしの達人", "努力の天才", "タスクスレイヤー", "週末の戦士", "無限の集中力", "数学の悪魔", "コードの魔術師", "文房具マスター", "伝説の勇者", "睡眠不足の神", "カフェイン中毒"]

# --- メイン処理 ---
def main():
    # ★重要: 初期化ブロック (なければ作る)
    if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
    if "username" not in st.session_state: st.session_state["username"] = ""
    if "is_studying" not in st.session_state: st.session_state["is_studying"] = False
    if "celebrate" not in st.session_state: st.session_state["celebrate"] = False
    if "start_time" not in st.session_state: st.session_state["start_time"] = None
    if "current_subject" not in st.session_state: st.session_state["current_subject"] = ""
    if "toast_msg" not in st.session_state: st.session_state["toast_msg"] = None

    st.title("✅ 褒めてくれる勉強時間・タスク管理アプリ")

    # 1. 未ログイン時
    if not st.session_state["logged_in"]:
        st.sidebar.title("🔐 ログイン")
        choice = st.sidebar.selectbox("メニュー", ["ログイン", "新規登録"])
        
        if choice == "ログイン":
            st.subheader("ログイン")
            u = st.text_input("ユーザー名")
            p = st.text_input("パスワード", type='password')
            if st.button("ログイン"):
                ok, msg = login_user(u, p)
                if ok:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u.strip()
                    st.rerun()
                else: st.error(msg)
        
        elif choice == "新規登録":
            st.subheader("新規登録")
            nu = st.text_input("ユーザー名 (ID)")
            np = st.text_input("パスワード", type='password')
            nn = st.text_input("ニックネーム")
            if st.button("登録"):
                if nu and np and nn:
                    if add_user(nu, np, nn): st.success("登録完了！ログインしてください。")
                    else: st.error("そのIDは使われています。")
                else: st.warning("全項目入力してください")
        return

    # 2. ログイン済み処理
    current_user = st.session_state["username"]
    user = get_user_data(current_user)
    
    # ユーザーデータが取れない場合はログアウト扱いにする
    if not user:
        st.session_state["logged_in"] = False
        st.rerun()

    # ★ 集中モード (待機画面) ★
    # ここで .get() を使っているのでエラーは絶対に出ません
    if st.session_state.get("is_studying", False):
        st.markdown(f"### 🔥 {st.session_state.get('current_subject', '勉強')} を勉強中...")
        
        now = time.time()
        start = st.session_state.get("start_time")
        if start is None: start = now
        
        elapsed = int(now - start)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        
        st.markdown(f"""
        <div style="text-align: center; font-size: 80px; font-weight: bold; color: #FF4B4B; background-color: rgba(0,0,0,0.5); padding: 20px; border-radius: 15px; margin: 50px 0; text-shadow: 0 0 10px #FF0000;">
            {h:02}:{m:02}:{s:02}
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("⏹️ 終了して記録", type="primary", use_container_width=True):
                mins = max(1, elapsed // 60)
                subj = st.session_state.get("current_subject", "自習")
                add_study_log(current_user, subj, mins)
                
                # フラグをリセット
                st.session_state["is_studying"] = False
                st.session_state["celebrate"] = True
                st.session_state["toast_msg"] = f"{mins}分 勉強しました！お疲れ様！"
                st.rerun()
        
        time.sleep(1)
        st.rerun()
        return

    # --- 通常画面 (タスク管理) ---
    apply_font(user.get('unlocked_themes', '標準').split(',')[0])
    apply_wallpaper(user.get('current_wallpaper', '草原'))

    # お祝い & トースト (ここも .get() で安全化)
    if st.session_state.get("celebrate", False):
        st.balloons()
        st.session_state["celebrate"] = False
    
    if st.session_state.get("toast_msg"):
        st.toast(st.session_state["toast_msg"], icon="🆙")
        st.session_state["toast_msg"] = None

    # サイドバー
    with st.sidebar:
        st.subheader(f"👤 {user['nickname']}")
        st.caption(f"👑 {user['current_title']}")
        if st.button("ログアウト"):
            st.session_state["logged_in"] = False
            st.rerun()
        st.divider()
        bg_op = st.slider("壁紙の暗さ", 0.0, 1.0, 0.4)
        wall_list = user['unlocked_wallpapers'].split(',')
        new_wall = st.selectbox("壁紙変更", wall_list, index=wall_list.index(user['current_wallpaper']) if user['current_wallpaper'] in wall_list else 0)
        if new_wall != user['current_wallpaper']:
            supabase.table("users").update({"current_wallpaper": new_wall}).eq("username", current_user).execute()
            st.rerun()

    # ステータスバー
    level = (user['xp'] // 50) + 1
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
        c1.metric("Lv", f"{level}")
        c2.metric("XP", f"{user['xp']}")
        c3.metric("Coin", f"{user['coins']} 💰")
        c4.write(f"Next Lv: **{level*50 - user['xp']} XP**")
        c4.progress(min(1.0, (user['xp'] % 50) / 50))

    st.divider()

    # データ取得
    tasks = get_tasks(current_user)
    logs = get_study_logs(current_user)

    # タブ
    t1, t2, t3, t4 = st.tabs(["📝 ToDo", "⏱️ タイマー", "🏆 ランク", "🛒 ショップ"])

    # ToDoタブ
    with t1:
        col_a, col_b = st.columns([0.6, 0.4])
        with col_a:
            with st.expander("➕ タスク追加"):
                with st.form("add_t"):
                    n = st.text_input("タスク名")
                    d = st.date_input("期限")
                    if st.form_submit_button("追加"):
                        add_task(current_user, n, d, "中")
                        st.session_state["toast_msg"] = "追加しました"
                        st.rerun()
            
            if not tasks.empty:
                for _, r in tasks[tasks['status']=='未完了'].iterrows():
                    c1, c2 = st.columns([0.85, 0.15])
                    if c1.button(f"✅ {r['task_name']} (期限: {r['due_date']})", key=f"t_{r['id']}"):
                        complete_tasks_bulk([r['id']], current_user, 10)
                        st.session_state["celebrate"] = True
                        st.rerun()
                    if c2.button("🗑️", key=f"d_{r['id']}"):
                        delete_task(r['id'])
                        st.rerun()
            else: st.info("タスクはありません")

        with col_b:
            # カレンダー
            events = [{"title": f"📝 {r['task_name']}", "start": r['due_date']} for _, r in tasks.iterrows()]
            calendar(events=events, options={"initialView": "dayGridMonth", "height": 400})

    # タイマータブ
    with t2:
        st.subheader("勉強タイマー")
        subj = st.text_input("勉強する内容", placeholder="例: 数学", key="timer_sub")
        if st.button("▶️ スタート", type="primary"):
            if subj:
                st.session_state["is_studying"] = True
                st.session_state["start_time"] = time.time()
                st.session_state["current_subject"] = subj
                st.rerun()
            else: st.warning("内容を入力してください")
        
        st.divider()
        st.write("📖 最近の履歴")
        if not logs.empty:
            for _, r in logs.head(5).iterrows():
                cc1, cc2 = st.columns([0.8, 0.2])
                cc1.write(f"・{r['subject']} ({r['duration_minutes']}分) - {r['study_date']}")
                if cc2.button("削除", key=f"dl_{r['id']}"):
                    delete_study_log(r['id'], current_user, r['duration_minutes'])
                    st.rerun()

    # ランキングタブ
    with t3:
        st.subheader("週間ランキング")
        start = (datetime.now(JST) - timedelta(days=7)).strftime('%Y-%m-%d')
        res = supabase.table("study_logs").select("username, duration_minutes").gte("study_date", start).execute()
        if res.data:
            df_r = pd.DataFrame(res.data)
            # ニックネームを結合するためにユーザーデータも取る
            users_res = supabase.table("users").select("username, nickname").execute()
            if users_res.data:
                df_u = pd.DataFrame(users_res.data)
                df_r = pd.merge(df_r, df_u, on="username", how="left")
                # グループ化して集計
                rank_df = df_r.groupby(['nickname']).sum()[['duration_minutes']].sort_values('duration_minutes', ascending=False)
                st.table(rank_df)
        else: st.info("データがありません")

    # ショップタブ
    with t4:
        st.subheader("🛒 ショップ")
        items = [("夕焼け", 800), ("夜空", 1000), ("ダンジョン", 1500), ("王宮", 2000), ("図書館", 1200), ("サイバー", 1800)]
        for name, price in items:
            with st.container(border=True):
                c1, c2 = st.columns([0.7, 0.3])
                c1.write(f"**{name}** ({price} 💰)")
                if name in user['unlocked_wallpapers'].split(','):
                    c2.button("済", disabled=True, key=f"b_{name}")
                else:
                    if c2.button("購入", key=f"buy_{name}"):
                        if user['coins'] >= price:
                            new_list = user['unlocked_wallpapers'] + f",{name}"
                            supabase.table("users").update({"coins": user['coins'] - price, "unlocked_wallpapers": new_list}).eq("username", current_user).execute()
                            st.balloons()
                            st.rerun()
                        else: st.error("コイン不足")
        
        st.divider()
        st.write("🎲 **称号ガチャ (100 💰)**")
        if st.button("ガチャを回す"):
            if user['coins'] >= 100:
                won = random.choice(GACHA_TITLES)
                play_gacha(current_user, 100) # コイン減算などは関数内
                st.success(f"🎉 {won} を獲得！")
                st.balloons()
                time.sleep(2)
                st.rerun()
            else: st.error("コイン不足")

if __name__ == "__main__":
    main()
