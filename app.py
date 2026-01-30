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
st.set_page_config(page_title="個人タスク管理RPG", layout="wide")

# --- 日本時間 (JST) の定義 ---
JST = timezone(timedelta(hours=9))

# --- セッションステート初期化 ---
if "toast_msg" not in st.session_state:
    st.session_state["toast_msg"] = None
if "is_studying" not in st.session_state:
    st.session_state["is_studying"] = False
if "start_time" not in st.session_state:
    st.session_state["start_time"] = None
# カレンダーの連打防止用（前回クリックしたデータを保存しておく）
if "last_cal_event" not in st.session_state:
    st.session_state["last_cal_event"] = None

# トースト通知表示
if st.session_state["toast_msg"]:
    st.toast(st.session_state["toast_msg"], icon="🆙")
    st.session_state["toast_msg"] = None 

st.title("✅ 褒めてくれるタスク管理 (RPG風)")

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
        .material-icons, .material-symbols-rounded, [data-testid="stExpander"] svg {{
            font-family: inherit !important;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)

# --- ユーザー情報取得 (拡張版) ---
def get_user_data(username):
    try:
        response = supabase.table("users").select("*").eq("username", username).execute()
        if response.data:
            return response.data[0]
        return None
    except:
        return None

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
        data = {
            "username": username, 
            "password": make_hashes(password), 
            "xp": 0,
            "coins": 0,
            "unlocked_themes": "標準",
            "current_title": "見習い",
            "unlocked_titles": "見習い"
        }
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

# --- DB操作: 勉強ログ関連 ---
def add_study_log(username, subject, minutes, date_obj=None):
    if date_obj is None:
        date_str = datetime.now(JST).strftime('%Y-%m-%d')
    else:
        date_str = date_obj.strftime('%Y-%m-%d')
        
    data = {
        "username": username,
        "subject": subject,
        "duration_minutes": minutes,
        "study_date": date_str
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
    return df

# --- DB操作: ショップ・ガチャ関連 ---
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
            
        supabase.table("users").update({
            "coins": new_coins, 
            "unlocked_titles": new_titles,
            "current_title": won_title
        }).eq("username", username).execute()
        
        return True, won_title, new_coins
    return False, None, current_coins

def set_title(username, title):
    supabase.table("users").update({"current_title": title}).eq("username", username).execute()


# --- ポップアップ詳細表示 (モーダル) ---
@st.dialog("📅 記録の詳細")
def show_detail_dialog(target_date, df_tasks, df_logs):
    st.write(f"**{target_date}** の頑張り記録です")
    
    day_tasks = pd.DataFrame()
    if not df_tasks.empty:
        day_tasks = df_tasks[df_tasks['due_date'] == target_date]
    
    day_logs = pd.DataFrame()
    total_minutes = 0
    if not df_logs.empty:
        day_logs = df_logs[df_logs['study_date'] == target_date]
        if not day_logs.empty:
            total_minutes = day_logs['duration_minutes'].sum()
    
    c_det1, c_det2 = st.columns(2)
    
    with c_det1:
        st.info("📝 **タスク**")
        if not day_tasks.empty:
            for _, row in day_tasks.iterrows():
                status_icon = "✅" if row['status'] == '完了' else "⬜"
                st.write(f"{status_icon} {row['task_name']}")
        else:
            st.caption("なし")
    
    with c_det2:
        st.success(f"📖 **勉強時間: {total_minutes}分**")
        if not day_logs.empty:
            for _, row in day_logs.iterrows():
                st.write(f"・{row['subject']}: {row['duration_minutes']}分")
        else:
            st.caption("なし")


# --- 日付補正処理 ---
def parse_correct_date(raw_date):
    """UTCのタイムスタンプを日本時間の日付に直す"""
    try:
        # Tが含まれている場合（例: 2026-01-28T00:00:00Z）
        if "T" in raw_date:
            # UTCとして解釈して日本時間に変換
            dt_utc = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            dt_jst = dt_utc.astimezone(JST)
            return dt_jst.strftime('%Y-%m-%d')
        else:
            # 単純な日付文字列ならそのまま返す
            return raw_date
    except:
        return raw_date

# --- 共通カレンダーコンポーネント (モーダル対応・ループ防止版) ---
def render_calendar_and_details(df_tasks, df_logs, unique_key):
    st.subheader("📅 カレンダー")
    st.caption("日付をクリックすると詳細がポップアップします")
    
    events = []
    
    if not df_tasks.empty:
        for _, row in df_tasks.iterrows():
            color = "#808080" if row['status'] == '完了' else "#FF4B4B" if row['priority']=="高" else "#1C83E1"
            events.append({
                "title": f"📝 {row['task_name']}",
                "start": row['due_date'],
                "backgroundColor": color,
                "allDay": True
            })
    
    if not df_logs.empty:
        for _, row in df_logs.iterrows():
            events.append({
                "title": f"📖 {row['subject']} ({row['duration_minutes']}m)",
                "start": row['study_date'],
                "backgroundColor": "#9C27B0",
                "borderColor": "#9C27B0",
                "allDay": True
            })

    # カレンダー設定 (日本時間を指定してズレを防止)
    cal_options = {
        "initialView": "dayGridMonth",
        "height": 450,
        "selectable": True,
        "timeZone": 'Asia/Tokyo', # これで日付ズレを直す！
    }
    
    cal_data = calendar(events=events, options=cal_options, callbacks=['dateClick', 'select', 'eventClick'], key=unique_key)
    
    # === 無限ループ防止ロジック ===
    # カレンダーからデータが来ていて、かつ「前回と同じデータ」でなければ処理する
    if cal_data and cal_data != st.session_state["last_cal_event"]:
        st.session_state["last_cal_event"] = cal_data # 今回のデータを保存
        
        raw_date_str = None
        
        # データ取り出し
        if "dateClick" in cal_data:
             raw_date_str = cal_data["dateClick"]["date"]
        elif "select" in cal_data:
             raw_date_str = cal_data["select"]["start"]
        elif "eventClick" in cal_data:
             raw_date_str = cal_data["eventClick"]["event"]["start"]
        
        # 日付が取れたら、補正してダイアログを開く
        if raw_date_str:
            target_date = parse_correct_date(raw_date_str)
            # ここで関数として直接呼び出す (st.rerunはしない！)
            show_detail_dialog(target_date, df_tasks, df_logs)


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
    user_data = get_user_data(current_user)
    
    xp = user_data.get('xp', 0) if user_data else 0
    coins = user_data.get('coins', 0) if user_data else 0
    my_themes = user_data.get('unlocked_themes', "標準").split(',') if user_data else ["標準"]
    my_title = user_data.get('current_title', "見習い") if user_data else "見習い"
    
    # --- サイドバー ---
    with st.sidebar:
        st.subheader(f"👤 {current_user}")
        st.caption(f"👑 {my_title}")
        
        if st.button("ログアウト"):
            st.session_state["logged_in"] = False
            st.rerun()
        st.divider()
        
        st.subheader("🎨 着せ替え設定")
        selected_theme = st.selectbox("フォント選択", my_themes, index=0)
        apply_theme(selected_theme)

    # --- メイン画面：ステータス ---
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

    if "celebrate" not in st.session_state: st.session_state["celebrate"] = False
    if st.session_state["celebrate"]:
        st.balloons()
        st.session_state["celebrate"] = False

    st.divider()

    df_tasks = get_tasks(current_user)
    df_logs = get_study_logs(current_user)

    # --- 画面レイアウト ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 ToDo", "⏱️ タイマー", "📊 分析", "🛒 ショップ"])
    
    # === タブ1: ToDoリスト ===
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
                        if st.button(f"✅ {len(selected_ids)}件完了 (+{len(selected_ids)*10} XP/Coin)", type="primary"):
                            amount, new_xp, new_coins = complete_tasks_bulk(selected_ids, current_user)
                            st.session_state["celebrate"] = True
                            st.session_state["toast_msg"] = f"+{amount}XP & +{amount}コイン 獲得！"
                            st.rerun()
                else:
                    st.info("タスクはありません！")
        
        with col_t2:
            render_calendar_and_details(df_tasks, df_logs, "cal_todo")

    # === タブ2: 勉強タイマー ===
    with tab2:
        col_s1, col_s2 = st.columns([0.5, 0.5])
        with col_s1:
            st.subheader("🔥 ストップウォッチ")
            if st.session_state["is_studying"]:
                start_dt = datetime.fromtimestamp(st.session_state["start_time"], JST)
                st.info(f"🕐 **{start_dt.strftime('%H:%M')}** から計測中...")
                elapsed_sec = time.time() - st.session_state["start_time"]
                st.metric("経過", f"{int(elapsed_sec // 60)} 分")
                
                study_subject = st.text_input("教科・内容", key="subject_input")
                if st.button("⏹️ 終了", type="primary"):
                    if not study_subject:
                        st.error("教科名を入力！")
                    else:
                        end_time = time.time()
                        duration_min = int((end_time - st.session_state["start_time"]) // 60)
                        if duration_min < 1: duration_min = 1
                        amount, nx, nc = add_study_log(current_user, study_subject, duration_min)
                        st.session_state["is_studying"] = False
                        st.session_state["start_time"] = None
                        st.session_state["celebrate"] = True
                        st.session_state["toast_msg"] = f"{duration_min}分勉強！ +{amount}XP & Coin"
                        st.rerun()
            else:
                if st.button("▶️ スタート", type="primary"):
                    st.session_state["is_studying"] = True
                    st.session_state["start_time"] = time.time()
                    st.rerun()

            st.divider()
            st.subheader("✏️ 手動記録")
            with st.expander("入力フォームを開く", expanded=True):
                with st.form("manual", clear_on_submit=True):
                    m_date = st.date_input("日付", value=date.today())
                    m_subj = st.text_input("教科")
                    ch, cm = st.columns(2)
                    mh = ch.number_input("時間", 0, 24, 0)
                    mm = cm.number_input("分", 0, 59, 0) # 初期値0
                    
                    if st.form_submit_button("記録", type="primary"):
                        total_m = (mh * 60) + mm
                        if m_subj and total_m > 0:
                            amt, nx, nc = add_study_log(current_user, m_subj, total_m, m_date)
                            st.session_state["celebrate"] = True
                            st.session_state["toast_msg"] = f"記録完了！ +{amt}XP & Coin"
                            st.rerun()
                        elif not m_subj:
                            st.error("教科を入力してください")
                        elif total_m <= 0:
                            st.error("時間を入力してください")

        with col_s2:
            render_calendar_and_details(df_tasks, df_logs, "cal_timer")

    # === タブ3: 分析レポート ===
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
            st.markdown("##### 📈 過去7日間の推移")
            today = date.today()
            last_7_days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
            daily_logs = df_logs.groupby('study_date')['duration_minutes'].sum().reset_index()
            df_trend = pd.DataFrame({'study_date': last_7_days})
            df_trend = pd.merge(df_trend, daily_logs, on='study_date', how='left').fillna(0)
            
            bar_chart = alt.Chart(df_trend).mark_bar().encode(
                x=alt.X('study_date', title='日付'),
                y=alt.Y('duration_minutes', title='時間(分)'),
                color=alt.value("#4CAF50"),
                tooltip=['study_date', 'duration_minutes']
            ).properties(height=300)
            st.altair_chart(bar_chart, use_container_width=True)
        else:
            st.info("データがありません")

    # === タブ4: ショップ・ガチャ ===
    with tab4:
        col_shop, col_gacha = st.columns(2)
        with col_shop:
            st.subheader("🛒 テーマショップ")
            st.write(f"所持コイン: **{coins} 💰**")
            shop_items = [
                {"name": "ピクセル風", "cost": 500, "desc": "レトロゲーム風"},
                {"name": "手書き風", "cost": 800, "desc": "黒板風"}
            ]
            for item in shop_items:
                with st.container(border=True):
                    st.write(f"**{item['name']}**")
                    st.caption(item['desc'])
                    if item['name'] in my_themes:
                        st.button("✅ 購入済み", disabled=True, key=f"btn_{item['name']}")
                    else:
                        if st.button(f"💰 {item['cost']} で購入", key=f"buy_{item['name']}"):
                            success, bal = buy_theme(current_user, item['name'], item['cost'])
                            if success:
                                st.balloons()
                                st.session_state["toast_msg"] = f"「{item['name']}」を購入しました！"
                                st.rerun()
                            else:
                                st.error("コイン不足！")

        with col_gacha:
            st.subheader("🎲 称号ガチャ")
            st.write("1回 **100 💰**")
            if st.button("ガチャを回す！", type="primary"):
                success, won_title, bal = play_gacha(current_user, 100)
                if success:
                    st.balloons()
                    st.success(f"🎉 **「{won_title}」** ゲット！")
                    st.session_state["toast_msg"] = f"称号「{won_title}」を獲得！"
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("コイン不足！")
            
            st.divider()
            st.write("📂 **称号コレクション**")
            my_titles_list = user_data.get('unlocked_titles', "見習い").split(',')
            selected_t = st.selectbox("称号を変更", my_titles_list, index=my_titles_list.index(my_title) if my_title in my_titles_list else 0)
            if selected_t != my_title:
                set_title(current_user, selected_t)
                st.session_state["toast_msg"] = f"称号を変更しました"
                st.rerun()

if __name__ == "__main__":
    main()
