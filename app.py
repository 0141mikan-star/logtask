import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time
import calendar
from datetime import datetime, date, timedelta, timezone
import altair as alt
import io
import base64
from PIL import Image
import hashlib
import extra_streamlit_components as stx

# ページ設定
st.set_page_config(page_title="褒めてくれる勉強時間・タスク管理アプリ", layout="wide", initial_sidebar_state="expanded")

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

# --- Cookieマネージャー ---
cookie_manager = stx.CookieManager(key="cookie_manager")

# --- 画像処理 ---
def image_to_base64(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# --- デザイン適用 ---
def apply_design(user_theme="標準", main_text_color="#000000", accent_color="#FFD700"):
    fonts = {
        "ピクセル風": "'DotGothic16', sans-serif",
        "手書き風": "'Yomogi', cursive",
        "ポップ": "'Hachi Maru Pop', cursive",
        "明朝体": "'Shippori Mincho', serif",
        "筆文字": "'Yuji Syuku', serif",
        "標準": "sans-serif"
    }
    font_family = fonts.get(user_theme, "sans-serif")
    
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DotGothic16&family=Yomogi&family=Hachi+Maru+Pop&family=Shippori+Mincho&family=Yuji+Syuku&display=swap');
    
    html, body, [class*="css"] {{ font-family: {font_family} !important; }}
    [data-testid="stAppViewContainer"], .stApp {{ background-color: #ffffff !important; }}
    
    /* サイドバー */
    [data-testid="stSidebar"] {{ background-color: #f8f9fa !important; border-right: 1px solid #ddd; }}
    [data-testid="stSidebar"] * {{ color: #000000 !important; }}
    
    /* 文字色 */
    .main h1, .main h2, .main h3, .main p, .main span, .main label, .main div {{ 
        color: {main_text_color} !important; 
    }}

    /* カレンダーの日付ボタン */
    .stButton button {{
        width: 100%;
        height: 80px;
        white-space: pre-wrap; /* 改行を許可 */
        line-height: 1.2;
        padding: 5px;
        border: 1px solid #eee;
        background-color: white;
        color: #333;
        transition: all 0.2s;
    }}
    .stButton button:hover {{
        border-color: {accent_color};
        background-color: #fffdf0;
        transform: translateY(-2px);
    }}
    /* 選択中の日付ボタン（primary） */
    div[data-testid="stVerticalBlock"] .stButton button[kind="primary"] {{
        background-color: {accent_color} !important;
        border-color: {accent_color} !important;
        color: #000 !important;
        font-weight: bold;
    }}

    /* コンテナ */
    div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stExpander"], div[data-testid="stForm"] {{
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0;
        border-radius: 12px; 
        padding: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    
    /* ステータスバー */
    .status-bar {{
        background: #ffffff; border: 1px solid #e0e0e0; padding: 15px; border-radius: 12px; 
        display: flex; justify-content: space-around; align-items: center; margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    .stat-val {{ font-size: 1.6em; font-weight: bold; }}
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
        data = {"username": username, "password": make_hashes(password), "nickname": nickname, "xp": 0, "coins": 0, "unlocked_themes": "標準", "current_theme": "標準", "current_title": "見習い", "unlocked_titles": "見習い", "current_wallpaper": "真っ白", "unlocked_wallpapers": "真っ白", "daily_goal": 60, "main_text_color": "#000000", "accent_color": "#FFD700"}
        supabase.table("users").insert(data).execute()
        return True, "登録成功"
    except: return False, "エラー"

def get_user_data(username):
    try:
        res = supabase.table("users").select("*").eq("username", username).execute()
        return res.data[0] if res.data else None
    except: return None

# --- DB操作 ---
def get_weekly_ranking():
    start = (datetime.now(JST) - timedelta(days=7)).strftime('%Y-%m-%d')
    try:
        logs = supabase.table("study_logs").select("username, duration_minutes").gte("study_date", start).execute()
        if not logs.data: return pd.DataFrame()
        df = pd.DataFrame(logs.data).groupby('username').sum().reset_index()
        users = supabase.table("users").select("username, nickname, current_title").execute()
        return pd.merge(df, pd.DataFrame(users.data), on='username', how='left').sort_values('duration_minutes', ascending=False)
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
    total = sum([l['duration_minutes'] for l in logs.data]) if logs.data else m
    goal_reached = False
    if ud.get('last_goal_reward_date') != today_str and total >= ud.get('daily_goal', 60):
        # ★修正：目標達成時は+100コイン（ログボとは別）
        supabase.table("users").update({"xp": ud['xp']+m, "coins": ud['coins']+m+100, "last_goal_reward_date": today_str}).eq("username", u).execute()
        goal_reached = True
    else:
        supabase.table("users").update({"xp": ud['xp']+m, "coins": ud['coins']+m}).eq("username", u).execute()
    return m, ud['xp']+m, ud['coins']+m, goal_reached

def delete_study_log(lid, u, m):
    supabase.table("study_logs").delete().eq("id", lid).execute()
    ud = get_user_data(u)
    if ud: supabase.table("users").update({"xp": max(0, ud['xp']-m), "coins": max(0, ud['coins']-m)}).eq("username", u).execute()

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

# --- タイマー ---
@st.fragment(run_every=1)
def show_timer_fragment(user_name):
    now = time.time()
    start = st.session_state.get("start_time", now)
    elapsed = int(now - start)
    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    st.markdown(f"<div style='text-align:center; font-size:6em; font-weight:bold; color:#000;'>{h:02}:{m:02}:{s:02}</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("⏹️ 終了して記録", use_container_width=True, type="primary"):
            duration = max(1, elapsed // 60)
            _, _, _, reached = add_study_log(user_name, st.session_state.get("current_subject", "自習"), duration, date.today())
            st.session_state["is_studying"] = False
            st.session_state["celebrate"] = True
            st.session_state["toast_msg"] = f"{duration}分 記録しました！"
            if reached: st.session_state["goal_reached_msg"] = "🎉 目標達成！"
            st.rerun()

# --- メイン処理 ---
def main():
    if "logged_in" not in st.session_state: 
        st.session_state.update({
            "logged_in": False, "username": "", "is_studying": False, 
            "start_time": None, "celebrate": False, "toast_msg": None, 
            "selected_date": str(date.today()),
            "cal_year": date.today().year, "cal_month": date.today().month # カレンダー用
        })

    if not st.session_state["logged_in"]:
        try:
            auth = cookie_manager.get('logtask_auth')
            if auth:
                u, h = auth.split(":", 1)
                res = supabase.table("users").select("password").eq("username", u).execute()
                if res.data and res.data[0]["password"] == h:
                    st.session_state["logged_in"] = True; st.session_state["username"] = u; st.rerun()
        except: pass

    if not st.session_state["logged_in"]:
        st.title("🛡️ ログイン")
        mode = st.selectbox("モード", ["ログイン", "新規登録"])
        u = st.text_input("ユーザーID"); p = st.text_input("パスワード", type="password")
        if mode == "新規登録":
            n = st.text_input("ニックネーム")
            if st.button("登録"):
                res, msg = add_user(u, p, n)
                if res: st.success(msg)
                else: st.error(msg)
        else:
            if st.button("ログイン"):
                res, msg = login_user(u, p)
                if res:
                    cookie_manager.set('logtask_auth', f"{u}:{make_hashes(p)}", expires_at=datetime.now() + timedelta(days=7))
                    st.session_state["logged_in"] = True; st.session_state["username"] = u; st.rerun()
                else: st.error(msg)
        return

    user = get_user_data(st.session_state["username"])
    if not user: st.session_state["logged_in"] = False; st.rerun()

    # 自動移行
    if user.get('current_wallpaper') != "真っ白":
        supabase.table("users").update({"current_wallpaper": "真っ白"}).eq("username", user['username']).execute()
        st.rerun()

    today_str = str(date.today())
    if user.get('last_login_date') != today_str:
        # ★修正：ログインボーナス 100コイン
        new_coins = user['coins'] + 100
        supabase.table("users").update({
            "coins": new_coins,
            "last_login_date": today_str
        }).eq("username", user['username']).execute()
        st.toast("🎁 ログインボーナス！ +100コイン GET！", icon="🎁")
        time.sleep(1)
        user['coins'] = new_coins

    # デザイン適用
    apply_design(
        user.get('current_theme', '標準'), 
        main_text_color=user.get('main_text_color', '#000000'),
        accent_color=user.get('accent_color', '#FFD700')
    )

    # サイドバー
    with st.sidebar:
        st.subheader("⚙️ 設定")
        with st.expander("🎨 文字色"):
            cur_m = user.get('main_text_color', '#000000'); cur_a = user.get('accent_color', '#FFD700')
            nm = st.color_picker("メイン", cur_m); na = st.color_picker("アクセント", cur_a)
            if nm != cur_m or na != cur_a:
                supabase.table("users").update({"main_text_color": nm, "accent_color": na}).eq("username", user['username']).execute()
                st.rerun()
        st.divider()
        ng = st.number_input("1日の目標(分)", value=user.get('daily_goal', 60), step=10)
        if ng != user.get('daily_goal', 60):
            if st.button("目標保存"):
                supabase.table("users").update({"daily_goal": ng}).eq("username", user['username']).execute()
                st.rerun()
        st.divider()
        
        VALID = ["標準", "ピクセル風", "手書き風", "ポップ", "明朝体", "筆文字"]
        my_fonts = [t for t in user.get('unlocked_themes', '').split(',') if t in VALID]
        if not my_fonts: my_fonts = ["標準"]
        cur_t = user.get('current_theme', '標準')
        if cur_t not in my_fonts: cur_t = "標準"
        nt = st.selectbox("フォント", my_fonts, index=my_fonts.index(cur_t))
        if nt != cur_t:
            supabase.table("users").update({"current_theme": nt}).eq("username", user['username']).execute()
            st.rerun()

        if st.button("ログアウト"):
            cookie_manager.delete('logtask_auth')
            st.session_state["logged_in"] = False; st.rerun()

    if st.session_state["is_studying"]:
        st.empty(); st.markdown(f"<h1 style='text-align:center;'>🔥 {st.session_state.get('current_subject','')} 中...</h1>", unsafe_allow_html=True)
        show_timer_fragment(user['username'])
        return

    # データ取得
    logs_df = get_study_logs(user['username'])
    tasks = get_tasks(user['username'])
    today_mins = 0
    if not logs_df.empty:
        today_mins = logs_df[logs_df['study_date'].astype(str).str.contains(str(date.today()))]['duration_minutes'].sum()

    # HUD
    st.markdown(f"""
    <div class="status-bar">
        <div class="stat-item"><div class="stat-label">PLAYER</div><div class="stat-val" style="font-size:1.2em;">{user['nickname']}</div><div style="font-size:0.7em;">{user.get('current_title', '見習い')}</div></div>
        <div class="stat-item"><div class="stat-label">XP</div><div class="stat-val">{user['xp']}</div></div>
        <div class="stat-item"><div class="stat-label">COIN</div><div class="stat-val" style="color:{user.get('accent_color')};">{user['coins']} G</div></div>
        <div class="stat-item"><div class="stat-label">TODAY</div><div class="stat-val">{today_mins} / {user.get('daily_goal')} min</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(min(1.0, today_mins / max(1, user.get('daily_goal', 60))))

    # 通知
    if st.session_state.get("celebrate"): st.balloons(); st.session_state["celebrate"] = False
    if st.session_state.get("toast_msg"): st.toast(st.session_state["toast_msg"]); st.session_state["toast_msg"] = None

    t1, t2, t3, t4, t5, t6 = st.tabs(["📅 カレンダー", "⏱️ タイマー", "📊 分析", "🏆 ランキング", "🛒 ショップ", "📚 科目"])

    with t1: 
        c1, c2 = st.columns([0.65, 0.35])
        
        # --- ★完全自作カレンダー ---
        with c1:
            with st.container(border=True):
                # 月移動ヘッダー
                mc1, mc2, mc3 = st.columns([0.2, 0.6, 0.2])
                with mc1:
                    if st.button("◀ 前月"):
                        st.session_state.cal_month -= 1
                        if st.session_state.cal_month == 0:
                            st.session_state.cal_month = 12; st.session_state.cal_year -= 1
                        st.rerun()
                with mc2:
                    st.markdown(f"<h3 style='text-align:center; margin:0;'>{st.session_state.cal_year}年 {st.session_state.cal_month}月</h3>", unsafe_allow_html=True)
                with mc3:
                    if st.button("次月 ▶"):
                        st.session_state.cal_month += 1
                        if st.session_state.cal_month == 13:
                            st.session_state.cal_month = 1; st.session_state.cal_year += 1
                        st.rerun()
                
                # 曜日ヘッダー
                cols = st.columns(7)
                weekdays = ["日", "月", "火", "水", "木", "金", "土"]
                for i, w in enumerate(weekdays):
                    cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#666;'>{w}</div>", unsafe_allow_html=True)
                
                # カレンダーデータ生成
                cal = calendar.Calendar(firstweekday=6) # 日曜始まり
                month_days = cal.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
                
                # 日付ボタン配置
                for week in month_days:
                    cols = st.columns(7)
                    for i, d in enumerate(week):
                        with cols[i]:
                            if d != 0:
                                d_str = f"{st.session_state.cal_year}-{st.session_state.cal_month:02}-{d:02}"
                                
                                # データ集計
                                label = f"{d}"
                                if not logs_df.empty:
                                    s_mins = logs_df[logs_df['study_date'].astype(str).str.contains(d_str)]['duration_minutes'].sum()
                                    if s_mins > 0: label += f"\n📚{s_mins}分"
                                
                                if not tasks.empty:
                                    t_cnt = len(tasks[(tasks['due_date'].astype(str) == d_str) & (tasks['status'] == '未完了')])
                                    if t_cnt > 0: label += f"\n📝{t_cnt}件"
                                
                                # 選択状態
                                b_type = "primary" if d_str == st.session_state.get("selected_date") else "secondary"
                                
                                if st.button(label, key=f"btn_{d_str}", type=b_type, use_container_width=True):
                                    st.session_state["selected_date"] = d_str
                                    st.rerun()
                            else:
                                st.write("")

        with c2:
            with st.container(border=True):
                raw_sel = st.session_state.get("selected_date", str(date.today()))
                display_date = raw_sel
                st.markdown(f"### 📌 {display_date}")
                
                # 詳細表示
                if not logs_df.empty:
                    day_logs = logs_df[logs_df['study_date'].astype(str).str.contains(display_date)]
                    if not day_logs.empty:
                        total_d = day_logs['duration_minutes'].sum()
                        st.info(f"📚 合計: {total_d}分")
                        sub_agg = day_logs.groupby('subject')['duration_minutes'].sum().reset_index()
                        for _, r in sub_agg.iterrows():
                            st.write(f"・{r['subject']}: {r['duration_minutes']}分")
                
                st.divider()
                st.write("📝 **タスク**")
                if not tasks.empty:
                    dt = tasks[tasks['due_date'].astype(str) == display_date]
                    if not dt.empty:
                        for _, task in dt.iterrows():
                            if task['status'] == "未完了":
                                if st.button(f"完了: {task['task_name']}", key=f"d_{task['id']}"):
                                    complete_task(task['id'], user['username']); st.rerun()
                            else: st.write(f"✅ {task['task_name']}")
                    else: st.caption("タスクなし")
                
                st.divider()
                with st.form("add_t"):
                    tn = st.text_input("タスク名")
                    try: dd = datetime.strptime(display_date, '%Y-%m-%d').date()
                    except: dd = date.today()
                    td = st.date_input("期日", value=dd)
                    if st.form_submit_button("追加"):
                        add_task(user['username'], tn, td, "中"); st.rerun()

    with t2: # タイマー
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🔥 集中")
            sub = st.selectbox("科目", get_subjects(user['username']) + ["その他"])
            if sub=="その他": sub = st.text_input("科目名")
            if st.button("スタート", type="primary", use_container_width=True):
                if sub:
                    st.session_state["is_studying"]=True; st.session_state["start_time"]=time.time(); st.session_state["current_subject"]=sub
                    st.rerun()
        with c2:
            st.subheader("✏️ 記録")
            with st.form("manual"):
                d = st.date_input("日付"); h = st.number_input("時間",0,23); m = st.number_input("分",0,59)
                s = st.text_input("科目", value=sub if sub!="その他" else "")
                if st.form_submit_button("記録"):
                    add_study_log(user['username'], s, h*60+m, d); st.rerun()
        
        st.write("履歴 (最新5件)")
        if not logs_df.empty:
            for _,r in logs_df.head(5).iterrows():
                c_a, c_b = st.columns([0.8, 0.2])
                c_a.text(f"{r['study_date']} : {r['subject']} ({r['duration_minutes']}分)")
                if c_b.button("削除", key=f"del_{r['id']}"): delete_study_log(r['id'], user['username'], r['duration_minutes']); st.rerun()

    with t3: # 分析
        k1, k2 = st.columns(2)
        k1.metric("総勉強時間", f"{logs_df['duration_minutes'].sum()//60}時間")
        k2.metric("今日", f"{today_mins}分")
        if not logs_df.empty:
            logs_df['dt'] = pd.to_datetime(logs_df['study_date'])
            rc = logs_df[logs_df['dt'] >= (datetime.now(JST)-timedelta(days=7)).replace(tzinfo=None)]
            if not rc.empty:
                st.altair_chart(alt.Chart(rc).mark_bar().encode(x='dt:T', y='duration_minutes', color='subject'), use_container_width=True)
                
    with t4: # ランキング
        st.subheader("🏆 週間ランキング")
        rk = get_weekly_ranking()
        if not rk.empty:
            for i, r in rk.iterrows():
                medal = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"{i+1}位"
                st.markdown(f"<div class='ranking-card'><div class='rank-medal'>{medal}</div><div class='rank-info'><div class='rank-name'>{r['nickname']}</div><div class='rank-title'>{r['current_title']}</div></div><div class='rank-score'>{int(r['duration_minutes'])} min</div></div>", unsafe_allow_html=True)

    with t5: # ショップ
        st.write("アイテム購入")
        for f, p in [("ピクセル風",500),("手書き風",800),("ポップ",1000),("明朝体",1200),("筆文字",1500)]:
            c1, c2 = st.columns([0.7,0.3])
            c1.write(f"{f} ({p}G)")
            if f not in user['unlocked_themes']:
                if c2.button("購入", key=f"buy_{f}"):
                    if user['coins']>=p:
                        supabase.table("users").update({"coins":user['coins']-p, "unlocked_themes":user['unlocked_themes']+","+f}).eq("username", user['username']).execute()
                        st.balloons(); st.rerun()
            else: c2.write("済")

    with t6: # 科目
        ns = st.text_input("新規科目")
        if st.button("追加", key="add_sub"):
            if ns: add_subject_db(user['username'], ns); st.rerun()
        for s in get_subjects(user['username']):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(s)
            if c2.button("削除", key=f"del_s_{s}"): delete_subject_db(user['username'], s); st.rerun()

if __name__ == "__main__":
    main()
