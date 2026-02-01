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

# --- BGMデータ ---
BGM_DATA = {
    "なし": None,
    "雨の音": "https://upload.wikimedia.org/wikipedia/commons/8/8f/Rain_falling_on_leaves.ogg",
    "焚き火": "https://upload.wikimedia.org/wikipedia/commons/6/66/Fire_crackling_sound_effect.ogg",
    "カフェ": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Cafe_noise.ogg",
    "川のせせらぎ": "https://upload.wikimedia.org/wikipedia/commons/e/ec/River_Sound.ogg",
    "ホワイトノイズ": "https://upload.wikimedia.org/wikipedia/commons/9/98/White_Noise.ogg"
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
            "current_bgm": "なし", "unlocked_bgm": "なし",
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

# --- 科目管理 ---
def get_subjects(username):
    try:
        res = supabase.table("subjects").select("*").eq("username", username).execute()
        return [row['subject_name'] for row in res.data]
    except: return []

def add_subject_db(username, subject_name):
    try:
        supabase.table("subjects").insert({"username": username, "subject_name": subject_name}).execute()
        return True
    except: return False

def delete_subject_db(username, subject_name):
    try:
        supabase.table("subjects").delete().eq("username", username).eq("subject_name", subject_name).execute()
        return True
    except: return False

# --- タスク・ログ管理 ---
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
    return amount, u['xp'] + amount, u['coins'] + amount

def delete_task(tid):
    supabase.table("tasks").delete().eq("id", tid).execute()

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
    new_xp = user_data['xp'] if user_data else 0
    new_coins = user_data['coins'] if user_data else 0
    
    if user_data:
        new_xp = user_data.get('xp', 0) + amount
        new_coins = user_data.get('coins', 0) + amount
        supabase.table("users").update({"xp": new_xp, "coins": new_coins}).eq("username", username).execute()
        
    return amount, new_xp, new_coins

def delete_study_log(lid, username, mins):
    supabase.table("study_logs").delete().eq("id", lid).execute()
    u = get_user_data(username)
    if u: supabase.table("users").update({"xp": max(0, u['xp'] - mins), "coins": max(0, u['coins'] - mins)}).eq("username", username).execute()
    return True

def get_study_logs(username):
    try:
        res = supabase.table("study_logs").select("*").eq("username", username).execute()
        df = pd.DataFrame(res.data)
        return df.sort_values('created_at', ascending=False) if not df.empty else df
    except: return pd.DataFrame()

# ガチャリスト
GACHA_TITLES = ["駆け出し冒険者", "夜更かしの達人", "努力の天才", "タスクスレイヤー", "週末の戦士", "無限の集中力", "数学の悪魔", "コードの魔術師", "文房具マスター", "伝説の勇者", "睡眠不足の神", "カフェイン中毒"]

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
        supabase.table("users").update({"coins": new_coins, "unlocked_titles": new_titles, "current_title": won_title}).eq("username", username).execute()
        return True, won_title, new_coins
    return False, None, current_coins

def set_title(username, title):
    supabase.table("users").update({"current_title": title}).eq("username", username).execute()

def parse_correct_date(raw_date):
    try:
        if "T" in raw_date:
            dt_utc = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            dt_jst = dt_utc.astimezone(JST)
            return dt_jst.strftime('%Y-%m-%d')
        else: return raw_date
    except: return raw_date

# --- 詳細ダイアログ ---
@st.dialog("📅 記録の詳細")
def show_detail_dialog(target_date, df_tasks, df_logs, username):
    st.write(f"**{target_date}** の記録")
    day_tasks = pd.DataFrame()
    if not df_tasks.empty:
        day_tasks = df_tasks[df_tasks['due_date'] == target_date]
    day_logs = pd.DataFrame()
    if not df_logs.empty:
        day_logs = df_logs[df_logs['study_date'] == target_date]
    
    c1, c2 = st.columns(2)
    with c1:
        st.info("📝 **タスク**")
        if not day_tasks.empty:
            for _, row in day_tasks.iterrows():
                cc1, cc2 = st.columns([0.8, 0.2])
                icon = "✅" if row['status'] == '完了' else "⬜"
                cc1.write(f"{icon} {row['task_name']}")
                if cc2.button("🗑️", key=f"del_task_cal_{row['id']}"):
                    delete_task(row['id'])
                    st.session_state["toast_msg"] = "タスクを削除しました"
                    st.rerun()
        else: st.caption("なし")
    with c2:
        st.success(f"📖 **勉強**")
        if not day_logs.empty:
            for _, row in day_logs.iterrows():
                cc1, cc2 = st.columns([0.8, 0.2])
                cc1.write(f"・{row['subject']}: {row['duration_minutes']}分")
                if cc2.button("🗑️", key=f"del_log_cal_{row['id']}"):
                    delete_study_log(row['id'], username, row['duration_minutes'])
                    st.session_state["toast_msg"] = f"ログを削除 (-{row['duration_minutes']} XP/Coin)"
                    st.rerun()
        else: st.caption("なし")

# --- カレンダー表示 ---
def render_calendar_and_details(df_tasks, df_logs, unique_key, username):
    st.subheader("📅 カレンダー")
    events = []
    if not df_tasks.empty:
        for _, row in df_tasks.iterrows():
            color = "#808080" if row['status'] == '完了' else "#FF4B4B" if row['priority']=="高" else "#1C83E1"
            events.append({"title": f"📝 {row['task_name']}", "start": row['due_date'], "backgroundColor": color, "allDay": True})
    if not df_logs.empty:
        for _, row in df_logs.iterrows():
            events.append({"title": f"📖 {row['subject']} ({row['duration_minutes']}m)", "start": row['study_date'], "backgroundColor": "#9C27B0", "borderColor": "#9C27B0", "allDay": True})
    
    cal_data = calendar(events=events, options={"initialView": "dayGridMonth", "height": 450}, callbacks=['dateClick', 'eventClick'], key=unique_key)
    
    if cal_data and cal_data != st.session_state.get("last_cal_event"):
        st.session_state["last_cal_event"] = cal_data
        raw = None
        if "dateClick" in cal_data: raw = cal_data["dateClick"]["date"]
        elif "eventClick" in cal_data: raw = cal_data["eventClick"]["event"]["start"]
        if raw:
            target = parse_correct_date(raw)
            show_detail_dialog(target, df_tasks, df_logs, username)

# --- その日のタスク ---
def render_daily_task_list(df_tasks, unique_key):
    st.subheader("📅 今日のクエスト")
    c1, c2 = st.columns([0.5, 0.5])
    with c1:
        target_date = st.date_input("日付を確認", value=date.today(), key=f"date_{unique_key}")
    day_tasks = pd.DataFrame()
    if not df_tasks.empty:
        day_tasks = df_tasks[df_tasks['due_date'] == str(target_date)]
    st.markdown(f'<div class="task-container-box"><div style="border-bottom:1px solid #555; padding-bottom:5px; margin-bottom:10px; font-weight:bold; color:#FFD700;">📅 {target_date} のクエスト</div>', unsafe_allow_html=True)
    if not day_tasks.empty:
        active = day_tasks[day_tasks['status'] == '未完了']
        if not active.empty:
            for _, row in active.iterrows():
                icon = "🔥" if row['priority'] == "高" else "⚠️" if row['priority'] == "中" else "🟢"
                st.info(f"{icon} **{row['task_name']}**")
        else: st.success("🎉 全クエスト完了！")
    else: st.info("予定はありません。")
    st.markdown('</div>', unsafe_allow_html=True)

# --- メイン処理 ---
def main():
    # セッション初期化
    if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
    if "username" not in st.session_state: st.session_state["username"] = ""
    if "is_studying" not in st.session_state: st.session_state["is_studying"] = False
    if "celebrate" not in st.session_state: st.session_state["celebrate"] = False
    if "toast_msg" not in st.session_state: st.session_state["toast_msg"] = None
    if "start_time" not in st.session_state: st.session_state["start_time"] = None
    if "current_subject" not in st.session_state: st.session_state["current_subject"] = ""

    st.title("✅ 褒めてくれる勉強時間・タスク管理アプリ")

    # ログイン画面
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
        else:
            st.subheader("新規登録")
            nu = st.text_input("ユーザー名 (ID)")
            np = st.text_input("パスワード", type='password')
            nn = st.text_input("ニックネーム")
            if st.button("登録"):
                if nu and np and nn:
                    if add_user(nu, np, nn): st.success("登録完了！"); st.rerun()
                    else: st.error("そのIDは使われています。")
                else: st.warning("全項目入力してください")
        return

    # ユーザーロード
    current_user = st.session_state["username"]
    user = get_user_data(current_user)
    if not user:
        st.session_state["logged_in"] = False
        st.rerun()

    # ★ 集中モード (待機画面 & BGM) ★
    if st.session_state.get("is_studying", False):
        st.markdown(f"### 🔥 {st.session_state.get('current_subject', '勉強')} を勉強中...")
        
        # BGM再生
        bgm_name = user.get('current_bgm', 'なし')
        if bgm_name in BGM_DATA and BGM_DATA[bgm_name]:
            st.audio(BGM_DATA[bgm_name], format="audio/ogg", loop=True, autoplay=True)
            st.caption(f"🎵 Now Playing: {bgm_name}")

        now = time.time()
        start = st.session_state.get("start_time")
        if start is None: start = now
        elapsed = int(now - start)
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
        
        st.markdown(f"""
        <div style="text-align: center; font-size: 80px; font-weight: bold; color: #FF4B4B; background-color: rgba(0,0,0,0.5); padding: 20px; border-radius: 15px; margin: 50px 0;">
            {h:02}:{m:02}:{s:02}
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("⏹️ 終了して記録", type="primary", use_container_width=True):
                mins = max(1, elapsed // 60)
                add_study_log(current_user, st.session_state.get("current_subject", "自習"), mins)
                st.session_state["is_studying"] = False
                st.session_state["celebrate"] = True
                st.session_state["toast_msg"] = f"{mins}分 完了！お疲れ様！"
                st.rerun()
        
        time.sleep(1)
        st.rerun()
        return

    # 通常画面
    apply_font(user.get('unlocked_themes', '標準').split(',')[0])
    apply_wallpaper(user.get('current_wallpaper', '草原'))
    if st.session_state.get("celebrate", False):
        st.balloons()
        st.session_state["celebrate"] = False
    if st.session_state.get("toast_msg"):
        st.toast(st.session_state["toast_msg"], icon="🆙")
        st.session_state["toast_msg"] = None

    # サイドバー
    with st.sidebar:
        st.subheader(f"👤 {user['nickname']}")
        if st.button("ログアウト"): st.session_state["logged_in"] = False; st.rerun()
        st.divider()
        
        # BGM設定
        st.write("🎵 **BGM設定**")
        my_bgms = user.get('unlocked_bgm', 'なし').split(',')
        if 'なし' not in my_bgms: my_bgms.insert(0, 'なし')
        cur_bgm = user.get('current_bgm', 'なし')
        try: bgm_idx = my_bgms.index(cur_bgm)
        except: bgm_idx = 0
        new_bgm = st.selectbox("集中時の音楽", my_bgms, index=bgm_idx)
        if new_bgm != cur_bgm:
            supabase.table("users").update({"current_bgm": new_bgm}).eq("username", current_user).execute()
            st.rerun()

        st.divider()
        
        # 科目管理機能
        with st.expander("📚 科目管理"):
            new_sub = st.text_input("科目を追加", placeholder="例: 数学")
            if st.button("追加"):
                if new_sub:
                    if add_subject_db(current_user, new_sub): st.success("追加しました"); st.rerun()
            
            subjects = get_subjects(current_user)
            if subjects:
                st.write("登録済み:")
                for sub in subjects:
                    c_del1, c_del2 = st.columns([0.8, 0.2])
                    c_del1.write(f"- {sub}")
                    if c_del2.button("🗑️", key=f"del_sub_{sub}"):
                        delete_subject_db(current_user, sub)
                        st.rerun()
            else:
                st.caption("登録なし")

        st.divider()
        st.write("🔧 デザイン")
        bg_op = st.slider("壁紙の暗さ", 0.0, 1.0, 0.4)
        wall_list = user['unlocked_wallpapers'].split(',')
        new_wall = st.selectbox("壁紙", wall_list, index=wall_list.index(user['current_wallpaper']) if user['current_wallpaper'] in wall_list else 0)
        if new_wall != user['current_wallpaper']:
            supabase.table("users").update({"current_wallpaper": new_wall}).eq("username", current_user).execute()
            st.rerun()

    # メインコンテンツ
    level = (user['xp'] // 50) + 1
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
        c1.metric("Lv", f"{level}")
        c2.metric("XP", f"{user['xp']}")
        c3.metric("Coin", f"{user['coins']} 💰")
        c4.write(f"Next Lv: **{level*50 - user['xp']} XP**")
        c4.progress(min(1.0, (user['xp'] % 50) / 50))

    st.divider()
    tasks = get_tasks(current_user)
    logs = get_study_logs(current_user)
    t1, t2, t3, t4 = st.tabs(["📝 ToDo", "⏱️ タイマー", "🏆 ランク", "🛒 ショップ"])

    # ToDo
    with t1:
        col_a, col_b = st.columns([0.6, 0.4])
        with col_a:
            with st.expander("➕ タスク追加"):
                with st.form("at"):
                    n = st.text_input("タスク名")
                    d = st.date_input("期限")
                    if st.form_submit_button("追加"):
                        add_task(current_user, n, d, "中"); st.session_state["toast_msg"]="追加！"; st.rerun()
            if not tasks.empty:
                for _, r in tasks[tasks['status']=='未完了'].iterrows():
                    c1, c2 = st.columns([0.85, 0.15])
                    if c1.button(f"✅ {r['task_name']}", key=f"t_{r['id']}"):
                        complete_tasks_bulk([r['id']], current_user, 10); st.session_state["celebrate"]=True; st.rerun()
                    if c2.button("🗑️", key=f"d_{r['id']}"): delete_task(r['id']); st.rerun()
            else: st.info("タスクなし")
        with col_b:
            render_calendar_and_details(tasks, logs, "cal_todo", current_user)

    # タイマー
    with t2:
        col_s1, col_s2 = st.columns([0.5, 0.5]) # ★ここを修正しました！
        with col_s1:
            st.subheader("勉強タイマー")
            # 登録済み科目から選択できるように変更
            subjects = get_subjects(current_user)
            if subjects:
                subj = st.selectbox("科目を選択", subjects + ["その他 (自由入力)"])
                if subj == "その他 (自由入力)":
                    subj = st.text_input("内容を入力", key="free_sub")
            else:
                subj = st.text_input("勉強する内容", placeholder="サイドバーで科目を登録できます", key="timer_sub")

            if st.button("▶️ スタート", type="primary"):
                if subj:
                    st.session_state["is_studying"] = True
                    st.session_state["start_time"] = time.time()
                    st.session_state["current_subject"] = subj
                    st.rerun()
                else: st.warning("科目を選択してください")
            
            st.divider()
            
            # 手動記録フォーム
            st.subheader("✏️ 手動記録")
            with st.expander("入力フォームを開く", expanded=True):
                with st.form("manual", clear_on_submit=True):
                    c_date, c_time_h, c_time_m = st.columns([0.4, 0.3, 0.3])
                    m_date = c_date.date_input("日付", value=date.today())
                    mh = c_time_h.number_input("時間", 0, 24, 0)
                    mm = c_time_m.number_input("分", 0, 59, 0)
                    m_subj = st.text_input("教科 (Enterで記録)", placeholder="例: 数学")
                    
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

            if not logs.empty:
                st.markdown("---")
                st.subheader("📖 最近の記録 (削除可能)")
                recent_logs = logs.head(5)
                for _, row in recent_logs.iterrows():
                    rc1, rc2, rc3 = st.columns([0.5, 0.3, 0.2])
                    rc1.write(f"**{row['subject']}**")
                    rc2.caption(f"{row['study_date']} / {row['duration_minutes']}分")
                    if rc3.button("🗑️", key=f"del_{row['id']}"):
                        if delete_study_log(row['id'], current_user, row['duration_minutes']):
                            st.warning(f"削除しました (-{row['duration_minutes']} XP/Coin)")
                            time.sleep(1)
                            st.rerun()

        with col_s2:
            render_daily_task_list(tasks, "timer_list")

    # ランキング
    with t3:
        st.subheader("週間ランキング")
        start = (datetime.now(JST) - timedelta(days=7)).strftime('%Y-%m-%d')
        res = supabase.table("study_logs").select("username, duration_minutes").gte("study_date", start).execute()
        if res.data:
            df_r = pd.DataFrame(res.data)
            u_res = supabase.table("users").select("username, nickname").execute()
            if u_res.data:
                df_r = pd.merge(df_r, pd.DataFrame(u_res.data), on="username", how="left")
                st.table(df_r.groupby('nickname').sum()[['duration_minutes']].sort_values('duration_minutes', ascending=False))
        else: st.info("データなし")

    # ショップ
    with t4:
        c_wall, c_bgm, c_gacha = st.columns(3)
        with c_wall:
            st.subheader("🖼️ 壁紙")
            items = [("夕焼け", 800), ("夜空", 1000), ("ダンジョン", 1500), ("王宮", 2000), ("図書館", 1200), ("サイバー", 1800)]
            for name, price in items:
                with st.container(border=True):
                    st.write(f"**{name}** ({price}G)")
                    if name in user['unlocked_wallpapers'].split(','): st.button("済", disabled=True, key=f"w_{name}")
                    else:
                        if st.button("購入", key=f"bw_{name}"):
                            if user['coins']>=price:
                                nl = user['unlocked_wallpapers'] + f",{name}"
                                supabase.table("users").update({"coins":user['coins']-price, "unlocked_wallpapers":nl}).eq("username",current_user).execute()
                                st.balloons(); st.rerun()
                            else: st.error("コイン不足")
        
        with c_bgm:
            st.subheader("🎵 BGM")
            bgm_items = [("雨の音", 500), ("焚き火", 800), ("カフェ", 1000), ("川のせせらぎ", 1200), ("ホワイトノイズ", 1500)]
            my_bgms = user.get('unlocked_bgm', 'なし').split(',')
            for name, price in bgm_items:
                with st.container(border=True):
                    st.write(f"**{name}** ({price}G)")
                    if name in my_bgms: st.button("済", disabled=True, key=f"bgm_{name}")
                    else:
                        if st.button("購入", key=f"bb_{name}"):
                            if user['coins']>=price:
                                nl = user.get('unlocked_bgm', 'なし') + f",{name}"
                                supabase.table("users").update({"coins":user['coins']-price, "unlocked_bgm":nl}).eq("username",current_user).execute()
                                st.balloons(); st.rerun()
                            else: st.error("コイン不足")

        with c_gacha:
            st.subheader("🎲 ガチャ (100G)")
            if st.button("回す"):
                if user['coins']>=100:
                    won = random.choice(GACHA_TITLES)
                    play_gacha(current_user, 100)
                    st.success(f"🎉 {won}！"); st.balloons(); time.sleep(1); st.rerun()
                else: st.error("コイン不足")

if __name__ == "__main__":
    main()
