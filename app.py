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
st.title("✅ 褒めてくれるタスク管理 (Supabase版)")

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
# キャッシュを使って接続を高速化
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
    st.error("Supabaseへの接続設定が見つかりません。secrets.tomlを確認してください。")
    st.stop()

# --- セキュリティ（ハッシュ化）関数 ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# --- ユーザー管理関数 ---
def add_user(username, password):
    try:
        data = {"username": username, "password": make_hashes(password)}
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
    # 自分のタスクだけを取得
    response = supabase.table("tasks").select("*").eq("username", username).execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        # 並び替え用ロジック
        df['status_rank'] = df['status'].apply(lambda x: 1 if x == '未完了' else 2)
        priority_map = {'高': 1, '中': 2, '低': 3}
        df['priority_rank'] = df['priority'].map(priority_map).fillna(3)
        df = df.sort_values(by=['status_rank', 'priority_rank', 'due_date'])
        return df
    return pd.DataFrame()

def update_status(task_id, is_done):
    status = '完了' if is_done else '未完了'
    supabase.table("tasks").update({"status": status}).eq("id", task_id).execute()

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
    with st.sidebar:
        st.write(f"👤 {st.session_state['username']}")
        if st.button("ログアウト"):
            st.session_state["logged_in"] = False
            st.rerun()
        st.divider()

    if "celebrate" not in st.session_state: st.session_state["celebrate"] = False
    if st.session_state["celebrate"]:
        st.balloons()
        st.toast(random.choice(PRAISE_MESSAGES), icon="🎉")
        st.session_state["celebrate"] = False

    col_list, col_calendar = st.columns([0.45, 0.55], gap="large")
    current_user = st.session_state["username"]
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
                
                if c1.checkbox("", value=is_done, key=f"c_{row['id']}") != is_done:
                    update_status(row['id'], not is_done)
                    if not is_done: st.session_state["celebrate"] = True
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
