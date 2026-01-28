import streamlit as st
import sqlite3
import pandas as pd
import random
import time
from datetime import datetime, date, timedelta
import urllib.parse
import hashlib
from streamlit_calendar import calendar

# ページ設定
st.set_page_config(page_title="個人タスク管理", layout="wide")
st.title("✅ 褒めてくれるタスク管理 (個人用)")

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

# --- セキュリティ（ハッシュ化）関数 ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# --- データベース関連 ---
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # タスクテーブル（username列を追加）
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            task_name TEXT NOT NULL,
            status TEXT NOT NULL,
            due_date TEXT,
            priority TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ユーザーテーブル（新規追加）
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')

    # 既存DBへの列追加（マイグレーション）
    try:
        c.execute("SELECT username FROM tasks LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE tasks ADD COLUMN username TEXT")
        conn.commit()
        
    try:
        c.execute("SELECT due_date FROM tasks LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
        c.execute("ALTER TABLE tasks ADD COLUMN priority TEXT")
        conn.commit()

    conn.commit()
    return conn

# --- ユーザー管理関数 ---
def add_user(conn, username, password):
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, make_hashes(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # ユーザー名が重複

def login_user(conn, username, password):
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    data = c.fetchall()
    if data:
        if check_hashes(password, data[0][0]):
            return True
    return False

# --- タスク管理関数（ユーザーフィルタ付き） ---
def add_task(conn, username, task_name, due_date, priority):
    c = conn.cursor()
    c.execute('INSERT INTO tasks (username, task_name, status, due_date, priority) VALUES (?, ?, ?, ?, ?)', 
              (username, task_name, '未完了', due_date, priority))
    conn.commit()

def get_tasks(conn, username):
    # username でフィルタリングする
    return pd.read_sql('''
        SELECT * FROM tasks 
        WHERE username = ?
        ORDER BY 
            CASE status WHEN '未完了' THEN 1 ELSE 2 END,
            CASE priority WHEN '高' THEN 1 WHEN '中' THEN 2 ELSE 3 END,
            due_date ASC
    ''', conn, params=(username,))

def update_status(conn, task_id, is_done):
    status = '完了' if is_done else '未完了'
    c = conn.cursor()
    c.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, task_id))
    conn.commit()

def delete_task(conn, task_id):
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()

# --- Googleカレンダー連携用 ---
def generate_google_calendar_link(task_name, due_date_str):
    base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
    text = urllib.parse.quote(task_name)
    start_date = datetime.strptime(due_date_str, '%Y-%m-%d')
    end_date = start_date + timedelta(days=1)
    dates = f"{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
    details = urllib.parse.quote("Streamlitタスク管理アプリ")
    return f"{base_url}&text={text}&dates={dates}&details={details}"

# --- メイン処理 ---
def main():
    conn = init_db()

    # セッション状態の初期化
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""

    # === ログインしていない場合 ===
    if not st.session_state["logged_in"]:
        st.sidebar.title("🔐 ログイン / 登録")
        menu = ["ログイン", "新規登録"]
        choice = st.sidebar.selectbox("メニュー", menu)

        if choice == "ログイン":
            st.subheader("ログイン画面")
            username = st.text_input("ユーザー名")
            password = st.text_input("パスワード", type='password')
            if st.button("ログイン"):
                if login_user(conn, username, password):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.success(f"{username} さん、おかえりなさい！")
                    st.rerun()
                else:
                    st.error("ユーザー名かパスワードが間違っています")

        elif choice == "新規登録":
            st.subheader("アカウント新規作成")
            new_user = st.text_input("希望のユーザー名")
            new_password = st.text_input("パスワード", type='password')
            if st.button("登録する"):
                if add_user(conn, new_user, new_password):
                    st.success("アカウントを作成しました！ログイン画面からログインしてください。")
                    st.info("左のメニューを「ログイン」に切り替えてください。")
                else:
                    st.warning("そのユーザー名は既に使用されています")
        
        # ログインしていない時はここで処理終了
        st.info("👈 左のサイドバーからログインまたは新規登録を行ってください。")
        return

    # === ログイン済みの場合 (ここからアプリ本体) ===
    
    # ログアウトボタン
    with st.sidebar:
        st.write(f"👤 **{st.session_state['username']}** でログイン中")
        if st.button("ログアウト"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.rerun()
        st.divider()

    # 褒める処理
    if "celebrate" not in st.session_state:
        st.session_state["celebrate"] = False
    if st.session_state["celebrate"]:
        st.balloons()
        st.toast(random.choice(PRAISE_MESSAGES), icon="🎉")
        st.session_state["celebrate"] = False

    # 画面分割
    col_list, col_calendar = st.columns([0.45, 0.55], gap="large")
    
    current_user = st.session_state["username"]
    df = get_tasks(conn, current_user)

    # 左カラム: リスト & 追加
    with col_list:
        st.subheader(f"📋 {current_user} のタスクリスト")
        
        with st.expander("➕ 新しいタスクを追加", expanded=True):
            with st.form("task_form", clear_on_submit=True):
                new_task = st.text_input("タスク名")
                c1, c2 = st.columns(2)
                with c1:
                    t_date = st.date_input("期限日", value=date.today())
                with c2:
                    t_prio = st.selectbox("優先度", ["高", "中", "低"], index=1)
                
                if st.form_submit_button("追加", type="primary"):
                    if new_task:
                        add_task(conn, current_user, new_task, t_date, t_prio)
                        st.toast("追加しました", icon="📅")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.warning("タスク名を入力してください")
        
        st.divider()

        # リスト表示
        if df.empty:
            st.info("タスクがありません。")
        else:
            done_count = len(df[df['status'] == '完了'])
            st.progress(done_count / len(df))
            
            for index, row in df.iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([0.1, 0.5, 0.25, 0.15])
                    is_done = row['status'] == '完了'
                    
                    with c1:
                        if st.checkbox("", value=is_done, key=f"chk_{row['id']}") != is_done:
                            update_status(conn, row['id'], not is_done)
                            if not is_done: st.session_state["celebrate"] = True
                            st.rerun()
                    with c2:
                        label = f"~~{row['task_name']}~~" if is_done else f"**{row['task_name']}**"
                        st.markdown(label)
                        if not is_done:
                            st.caption(f"📅 {row['due_date']} | {row['priority']}")
                    with c3:
                        if not is_done:
                            url = generate_google_calendar_link(row['task_name'], row['due_date'])
                            st.markdown(f'<a href="{url}" target="_blank">📅登録</a>', unsafe_allow_html=True)
                    with c4:
                        if st.button("🗑️", key=f"del_{row['id']}"):
                            delete_task(conn, row['id'])
                            st.rerun()
                    st.markdown("---")

    # 右カラム: カレンダー
    with col_calendar:
        st.subheader("📅 カレンダー")
        if df.empty:
            st.info("タスクを追加するとカレンダーに表示されます。")
        else:
            events = []
            for _, row in df.iterrows():
                color = "#808080" if row['status'] == '完了' else "#FF4B4B" if row['priority'] == "高" else "#1C83E1" if row['priority'] == "中" else "#27C46D"
                events.append({
                    "title": row['task_name'],
                    "start": row['due_date'],
                    "backgroundColor": color,
                    "borderColor": color,
                    "allDay": True
                })
            
            calendar(events=events, options={
                "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,listWeek"},
                "initialView": "dayGridMonth",
                "height": 600
            })

    conn.close()

if __name__ == "__main__":
    main()


