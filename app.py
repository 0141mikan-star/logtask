import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random
import time
from datetime import datetime, date, timedelta
import urllib.parse
import hashlib
from streamlit_calendar import calendar

# ページ設定
st.set_page_config(page_title="個人タスク管理", layout="wide")

# --- セッションステート初期化 ---
if "toast_msg" not in st.session_state:
    st.session_state["toast_msg"] = None

# 画面読み込み時に、前回の操作でセットされたメッセージがあれば表示
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

# --- 【修正】デザイン変更用の魔法の関数 ---
# バグ修正: アイコン（material-iconsなど）を除外してテキストだけにフォントを適用する
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
        # divやspanを無差別に指定せず、テキスト要素のみをターゲットにする
        css = f"""
        <style>
        {css_import}
        
        /* 一般的なテキスト要素に適用 */
        body, p, h1, h2, h3, h4, h5, h6, input, textarea, label, button, .stTooltip {{
            font-family: {font_family} !important;
        }}
        
        /* Streamlitの特定の要素 */
        .stMarkdown, .stTextInput > div > div, .stSelectbox > div > div {{
            font-family: {font_family} !important;
        }}

        /* アイコンが壊れないように除外設定（念のため） */
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

# --- タスク管理関数 ---
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

# --- 【修正】一括更新用の関数 ---
def complete_tasks_bulk(task_ids, username):
    # 1. すべてのIDを完了にする
    supabase.table("tasks").update({"status": "完了"}).in_("id", task_ids).execute()
    
    # 2. 経験値を計算（1つにつき10XP）
    xp_gained = len(task_ids) * 10
    
    current_xp = get_user_xp(username)
    new_xp = current_xp + xp_gained
    supabase.table("users").update({"xp": new_xp}).eq("username", username).execute()
    
    return xp_gained, new_xp

def delete_task(task_id):
    supabase.table("tasks").delete().eq("id", task_id).execute()

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
        st.sidebar.title("🔐 ログイン / 登録")
        choice = st.sidebar.selectbox("メニュー", ["ログイン", "新規登録"])
        # ... (ログイン処理は変更なし) ...
        if choice == "ログイン":
            st.subheader("ログイン")
            username = st.text_input("ユーザー名")
            password = st.text_input("パスワード", type='password')
            if st.button("ログイン"):
                if login_user(username, password):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.success("ログイン成功！")
                    st.rerun()
                else:
                    st.error("失敗しました。")
        elif choice == "新規登録":
            st.subheader("新規登録")
            new_user = st.text_input("ユーザー名")
            new_pass = st.text_input("パスワード", type='password')
            if st.button("登録"):
                if add_user(new_user, new_pass):
                    st.success("登録しました！ログインしてください。")
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
        
        if current_xp >= 50:
            theme_options.append("ピクセル風")
        else:
            st.caption("🔒 Lv.2 (XP 50) で「ピクセル風」解放")
        if current_xp >= 100:
            theme_options.append("手書き風")
        else:
            st.caption("🔒 Lv.3 (XP 100) で「手書き風」解放")
            
        if "theme" not in st.session_state:
            st.session_state["theme"] = "標準"
            
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
        col_stats1, col_stats2, col_stats3 = st.columns([1, 1, 3])
        with col_stats1:
            st.metric("Lv (レベル)", f"{level}")
        with col_stats2:
            st.metric("XP (経験値)", f"{current_xp}")
        with col_stats3:
            st.write(f"次のレベルまであと **{xp_needed} XP**")
            st.progress(max(0.0, min(1.0, progress_val)))

    if "celebrate" not in st.session_state: st.session_state["celebrate"] = False
    if st.session_state["celebrate"]:
        st.balloons()
        st.session_state["celebrate"] = False

    st.divider()

    col_list, col_calendar = st.columns([0.45, 0.55], gap="large")
    df = get_tasks(current_user)

    # --- タスクリスト (複数選択対応) ---
    with col_list:
        st.subheader("📋 タスクリスト")
        with st.expander("➕ タスク追加", expanded=True):
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

        if not df.empty:
            st.divider()
            
            # 未完了のタスクのみを対象にするリストを作る
            active_tasks = df[df['status'] == '未完了']
            completed_tasks = df[df['status'] == '完了']
            
            # 1. 未完了タスク（チェックボックス付き）
            if not active_tasks.empty:
                st.write("🔽 **未完了タスク (選択してまとめて完了)**")
                selected_ids = []
                
                for _, row in active_tasks.iterrows():
                    c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
                    
                    # 選択用チェックボックス (keyをユニークにする)
                    if c1.checkbox("", key=f"sel_{row['id']}"):
                        selected_ids.append(row['id'])
                    
                    c2.markdown(f"**{row['task_name']}**")
                    c2.caption(f"📅 {row['due_date']} | {row['priority']}")
                    
                    if c3.button("🗑️", key=f"d_{row['id']}"):
                        delete_task(row['id'])
                        st.rerun()
                    st.markdown("---")
                
                # まとめて完了ボタン
                if selected_ids:
                    if st.button(f"✅ 選択した {len(selected_ids)} 件を完了にする (+{len(selected_ids)*10} XP)", type="primary"):
                        gained, total = complete_tasks_bulk(selected_ids, current_user)
                        st.session_state["celebrate"] = True
                        st.session_state["toast_msg"] = f"まとめて完了！ 経験値 +{gained} 獲得！ (現在: {total})"
                        st.rerun()
            else:
                st.info("未完了のタスクはありません！")

            # 2. 完了済みタスク（履歴として表示）
            if not completed_tasks.empty:
                with st.expander("✅ 完了済みタスクを表示"):
                    for _, row in completed_tasks.iterrows():
                        c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
                        c1.write("✅") # ただのアイコン
                        c2.markdown(f"~~{row['task_name']}~~")
                        if c3.button("🗑️", key=f"d_done_{row['id']}"):
                            delete_task(row['id'])
                            st.rerun()
                        st.markdown("---")

    with col_calendar:
        st.subheader("📅 カレンダー")
        if not df.empty:
            events = []
            for _, row in df.iterrows():
                color = "#808080" if row['status'] == '完了' else "#FF4B4B" if row['priority']=="高" else "#1C83E1"
                events.append({"title": row['task_name'], "start": row['due_date'], "backgroundColor": color, "allDay": True})
            calendar(events=events, options={"initialView": "dayGridMonth", "height": 500})
        else:
            st.info("タスクを追加してください")

if __name__ == "__main__":
    main()
