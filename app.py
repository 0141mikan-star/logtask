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

# --- デザイン変更用の魔法の関数 (追加部分) ---
def apply_theme(font_type):
    css = ""
    if font_type == "ピクセル風":
        css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DotGothic16&display=swap');
        html, body, [class*="css"] { font-family: 'DotGothic16', sans-serif; }
        </style>
        """
    elif font_type == "手書き風":
        css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Yomogi&display=swap');
        html, body, [class*="css"] { font-family: 'Yomogi', cursive; }
        </style>
        """
    
    if css:
        st.markdown(css, unsafe_allow_html=True)

# --- ユーザー情報取得 (追加部分) ---
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
        # xp の初期値は 0
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

# --- ステータス更新 & XP加算 (改造部分) ---
def update_status(task_id, is_done, username):
    status = '完了' if is_done else '未完了'
    supabase.table("tasks").update({"status": status}).eq("id", task_id).execute()
    
    # 完了にした時だけXPを増やす！
    if is_done:
        current_xp = get_user_xp(username)
        new_xp = current_xp + 10
        supabase.table("users").update({"xp": new_xp}).eq("username", username).execute()
        return new_xp # 新しいXPを返す
    return None

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
    
    # --- サイドバー (着せ替え機能を追加) ---
    with st.sidebar:
        st.write(f"👤 {current_user}")
        
        # 現在のXPを取得して表示
        current_xp = get_user_xp(current_user)
        st.metric("現在の経験値 (XP)", f"{current_xp}")
        st.progress(min((current_xp % 100) / 100, 1.0)) # 次のレベルへのバー（簡易版）

        st.divider()
        
        # 着せ替えセレクター
        st.subheader("🎨 着せ替え")
        theme_options = ["標準"]
        
        if current_xp >= 50:
            theme_options.append("ピクセル風")
        else:
            st.caption("🔒 Lv.5 (XP 50) で「ピクセル風」解放")
            
        if current_xp >= 100:
            theme_options.append("手書き風")
        else:
            st.caption("🔒 Lv.10 (XP 100) で「手書き風」解放")
            
        # セッションに保存して選択状態を維持
        if "theme" not in st.session_state:
            st.session_state["theme"] = "標準"
            
        selected_theme = st.selectbox("フォント選択", theme_options, index=theme_options.index(st.session_state.get("theme", "標準")) if st.session_state.get("theme", "標準") in theme_options else 0)
        st.session_state["theme"] = selected_theme
        apply_theme(selected_theme)
        
        st.divider()

        if st.button("ログアウト"):
            st.session_state["logged_in"] = False
            st.rerun()

    # 褒める演出
    if "celebrate" not in st.session_state: st.session_state["celebrate"] = False
    if st.session_state["celebrate"]:
        st.balloons()
        st.toast(random.choice(PRAISE_MESSAGES), icon="🎉")
        st.session_state["celebrate"] = False

    col_list, col_calendar = st.columns([0.45, 0.55], gap="large")
    df = get_tasks(current_user)

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
                        st.toast("追加しました")
                        time.sleep(0.5)
                        st.rerun()

        if not df.empty:
            st.divider()
            for _, row in df.iterrows():
                c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
                is_done = row['status'] == '完了'
                
                # チェックボックスの処理
                if c1.checkbox("", value=is_done, key=f"c_{row['id']}") != is_done:
                    # ステータス更新関数に username も渡すように変更！
                    new_xp = update_status(row['id'], not is_done, current_user)
                    
                    if not is_done: # 未完了→完了 になった時
                        st.session_state["celebrate"] = True
                        if new_xp:
                            st.toast(f"経験値ゲット！ XP: {new_xp}", icon="🆙")
                    st.rerun()
                
                c2.markdown(f"~~{row['task_name']}~~" if is_done else f"**{row['task_name']}**")
                if not is_done: c2.caption(f"📅 {row['due_date']} | {row['priority']}")
                
                if c3.button("🗑️", key=f"d_{row['id']}"):
                    delete_task(row['id'])
                    st.rerun()

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
