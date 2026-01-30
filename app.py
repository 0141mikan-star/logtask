import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random
import time
from datetime import datetime, date, timedelta, timezone # timezoneを追加
import urllib.parse
import hashlib
from streamlit_calendar import calendar

# ページ設定
st.set_page_config(page_title="個人タスク管理", layout="wide")

# --- 日本時間 (JST) の定義 ---
JST = timezone(timedelta(hours=9))

# --- セッションステート初期化 ---
if "toast_msg" not in st.session_state:
    st.session_state["toast_msg"] = None

# ストップウォッチ用のステート
if "is_studying" not in st.session_state:
    st.session_state["is_studying"] = False
if "start_time" not in st.session_state:
    st.session_state["start_time"] = None

# 画面読み込み時にトースト通知
if st.session_state["toast_msg"]:
    st.toast(st.session_state["toast_msg"], icon="🆙")
    st.session_state["toast_msg"] = None 

st.title("✅ 褒めてくれるタスク管理 (RPG風)")

# 褒め言葉リスト
PRAISE_MESSAGES = [
    "素晴らしい！その調子です！🎉",
    "お疲れ様でした！偉い！✨",
    "タスク完了！すごいですね！🚀",
    "完璧です！また一つ片付きました！💪",
    "天才ですか？仕事が早い！😲",
    "着実に進んでいますね！偉業です！🏔️",
    "ナイスファイト！ゆっくり休んでください🍵"
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

# --- デザイン変更用の魔法の関数 ---
def apply_theme(font_type):
    css = ""
    font_family = ""
    if font_type == "ピクセル風":
        css_import = "@import url('https://fonts.googleapis.com/css2?family=DotGothic16&display=swap');"
        font_family = "'DotGothic16', sans-serif"
    elif font_type == "手書き風":
        css_import = "@import url('https://fonts.googleapis.com/css2?family=Yomogi&display=swap');"
        font_family = "'Yomogi', cursive"
    
    if font_family:
        css = f"""
        <style>
        {css_import}
        body, p, h1, h2, h3, h4, h5, h6, input, textarea, label, button, .stTooltip {{
            font-family: {font_family} !important;
        }}
        .stMarkdown, .stTextInput > div > div, .stSelectbox > div > div {{
            font-family: {font_family} !important;
        }}
        /* アイコン除外 */
        .material-icons, .material-symbols-rounded, [data-testid="stExpander"] svg {{
            font-family: inherit !important;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)

# --- ユーザー情報取得 ---
def get_user_xp(username):
    try:
        response = supabase.table("users").select("xp").eq("username", username).execute()
        if response.data:
            return response.data[0]["xp"]
        return 0
    except:
        return 0

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
        data = {"username": username, "password": make_hashes(password), "xp": 0}
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
    xp_gained = len(task_ids) * 10
    current_xp = get_user_xp(username)
    new_xp = current_xp + xp_gained
    supabase.table("users").update({"xp": new_xp}).eq("username", username).execute()
    return xp_gained, new_xp

def delete_task(task_id):
    supabase.table("tasks").delete().eq("id", task_id).execute()

# --- DB操作: 勉強ログ関連 ---
def add_study_log(username, subject, minutes):
    # 日本時間で日付を取得
    today_str = datetime.now(JST).strftime('%Y-%m-%d')
    data = {
        "username": username,
        "subject": subject,
        "duration_minutes": minutes,
        "study_date": today_str
    }
    supabase.table("study_logs").insert(data).execute()
    
    # 勉強時間 1分につき 1XP ゲット
    gained_xp = minutes
    current_xp = get_user_xp(username)
    new_xp = current_xp + gained_xp
    supabase.table("users").update({"xp": new_xp}).eq("username", username).execute()
    return gained_xp, new_xp

def get_study_logs(username):
    response = supabase.table("study_logs").select("*").eq("username", username).execute()
    df = pd.DataFrame(response.data)
    return df

# --- Googleカレンダー連携用 ---
def generate_google_calendar_link(task_name, due_date_str):
    base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
    text = urllib.parse.quote(task_name)
    try:
        start_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)
        dates = f"{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
    except:
        dates = ""
    details = urllib.parse.quote("Streamlitタスク管理アプリ")
    return f"{base_url}&text={text}&dates={dates}&details={details}"

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
                else:
                    st.error("失敗しました。")
        elif choice == "新規登録":
            st.subheader("新規登録")
            nu = st.text_input("ユーザー名")
            np = st.text_input("パスワード", type='password')
            if st.button("登録"):
                if add_user(nu, np):
                    st.success("登録完了！ログインしてください。")
                else:
                    st.warning("その名前は使われています。")
        return

    # === アプリ本編 ===
    current_user = st.session_state["username"]
    
    # --- サイドバー ---
    with st.sidebar:
        st.write(f"👤 {current_user}")
        if st.button("ログアウト"):
            st.session_state["logged_in"] = False
            st.rerun()
        st.divider()

        current_xp = get_user_xp(current_user)
        
        st.subheader("🎨 着せ替え設定")
        theme_options = ["標準"]
        if current_xp >= 50: theme_options.append("ピクセル風")
        else: st.caption("🔒 Lv.2 (50XP) で「ピクセル風」")
        if current_xp >= 100: theme_options.append("手書き風")
        else: st.caption("🔒 Lv.3 (100XP) で「手書き風」")
            
        if "theme" not in st.session_state: st.session_state["theme"] = "標準"
        selected_theme = st.selectbox("フォント選択", theme_options, index=theme_options.index(st.session_state.get("theme", "標準")) if st.session_state.get("theme", "標準") in theme_options else 0)
        st.session_state["theme"] = selected_theme
        apply_theme(selected_theme)

    # --- メイン画面：ステータス ---
    current_xp = get_user_xp(current_user)
    level = (current_xp // 50) + 1
    next_level_xp = level * 50
    xp_needed = next_level_xp - current_xp
    progress_val = 1.0 - (xp_needed / 50)
    
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 3])
        c1.metric("Lv", f"{level}")
        c2.metric("XP", f"{current_xp}")
        c3.write(f"次のレベルまで: **{xp_needed} XP**")
        c3.progress(max(0.0, min(1.0, progress_val)))

    if "celebrate" not in st.session_state: st.session_state["celebrate"] = False
    if st.session_state["celebrate"]:
        st.balloons()
        st.session_state["celebrate"] = False

    st.divider()

    # --- 画面レイアウト ---
    col_left, col_right = st.columns([0.45, 0.55], gap="large")
    
    df_tasks = get_tasks(current_user)
    df_logs = get_study_logs(current_user)

    with col_left:
        tab_tasks, tab_timer = st.tabs(["📝 ToDoリスト", "⏱️ 集中タイマー"])
        
        # === タブ1: ToDoリスト ===
        with tab_tasks:
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
                            time.sleep(0.5)
                            st.rerun()

            if not df_tasks.empty:
                active_tasks = df_tasks[df_tasks['status'] == '未完了']
                
                if not active_tasks.empty:
                    st.write("🔽 **未完了タスク**")
                    selected_ids = []
                    for _, row in active_tasks.iterrows():
                        cc1, cc2, cc3 = st.columns([0.1, 0.7, 0.2])
                        if cc1.checkbox("", key=f"sel_{row['id']}"):
                            selected_ids.append(row['id'])
                        cc2.markdown(f"**{row['task_name']}**")
                        cc2.caption(f"📅 {row['due_date']} | {row['priority']}")
                        if cc3.button("🗑️", key=f"d_{row['id']}"):
                            delete_task(row['id'])
                            st.rerun()
                        st.markdown("---")
                    
                    if selected_ids:
                        if st.button(f"✅ {len(selected_ids)}件完了 (+{len(selected_ids)*10}XP)", type="primary"):
                            gained, total = complete_tasks_bulk(selected_ids, current_user)
                            st.session_state["celebrate"] = True
                            st.session_state["toast_msg"] = f"お疲れ様！ +{gained}XP (現在: {total})"
                            st.rerun()
                else:
                    st.info("タスクはありません！")
            else:
                st.info("タスクを追加しよう！")

        # === タブ2: 勉強タイマー (GIF削除・時刻修正版) ===
        with tab_timer:
            st.subheader("🔥 勉強時間を記録")
            st.caption("時間を測ると 1分につき 1XP もらえるよ！")
            
            # 計測中の表示
            if st.session_state["is_studying"]:
                # 日本時間で開始時刻を表示
                start_dt = datetime.fromtimestamp(st.session_state["start_time"], JST)
                st.info(f"🕐 **{start_dt.strftime('%H:%M')}** から計測中...")
                
                elapsed_sec = time.time() - st.session_state["start_time"]
                st.metric("経過時間 (目安)", f"{int(elapsed_sec // 60)} 分")
                
                st.write("---")
                study_subject = st.text_input("教科・内容を入力 (例: 数学)", key="subject_input")
                
                if st.button("⏹️ 終了して記録する", type="primary"):
                    if not study_subject:
                        st.error("教科名を入力してください！")
                    else:
                        end_time = time.time()
                        duration_min = int((end_time - st.session_state["start_time"]) // 60)
                        
                        if duration_min < 1:
                            duration_min = 1
                            
                        gained, total = add_study_log(current_user, study_subject, duration_min)
                        
                        st.session_state["is_studying"] = False
                        st.session_state["start_time"] = None
                        st.session_state["celebrate"] = True
                        st.session_state["toast_msg"] = f"{duration_min}分勉強した！ +{gained}XP (現在: {total})"
                        st.rerun()
            
            else:
                if st.button("▶️ 勉強スタート！", type="primary"):
                    st.session_state["is_studying"] = True
                    st.session_state["start_time"] = time.time()
                    st.rerun()

    # --- カレンダー表示 ---
    with col_right:
        st.subheader("📅 カレンダー")
        
        events = []
        if not df_tasks.empty:
            for _, row in df_tasks.iterrows():
                color = "#808080" if row['status'] == '完了' else "#FF4B4B" if row['priority']=="高" else "#1C83E1"
                events.append({
                    "title": f"📝 {row['task_name']}",
                    "start": row['due_date'],
                    "backgroundColor": color,
                    "borderColor": color,
                    "allDay": True
                })
        
        if not df_logs.empty:
            for _, row in df_logs.iterrows():
                events.append({
                    "title": f"📖 {row['subject']} ({row['duration_minutes']}分)",
                    "start": row['study_date'],
                    "backgroundColor": "#9C27B0",
                    "borderColor": "#9C27B0",
                    "allDay": True
                })

        if events:
            calendar(events=events, options={"initialView": "dayGridMonth", "height": 600})
        else:
            st.info("データがありません")

if __name__ == "__main__":
    main()
