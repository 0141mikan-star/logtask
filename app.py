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

# --- デザイン適用関数（ここを共通化して短縮しました！） ---
def apply_design(user_theme="標準", wallpaper="草原", bg_opacity=0.4):
    # フォント設定
    fonts = {
        "ピクセル風": "'DotGothic16', sans-serif",
        "手書き風": "'Yomogi', cursive",
        "ポップ": "'Hachi Maru Pop', cursive",
        "明朝体": "'Shippori Mincho', serif",
        "筆文字": "'Yuji Syuku', serif",
        "標準": "sans-serif"
    }
    font_family = fonts.get(user_theme, "sans-serif")
    
    # 壁紙設定
    wallpapers = {
        "草原": "1472214103451-9374bd1c798e", "夕焼け": "1472120435266-53107fd0c44a",
        "夜空": "1462331940025-496dfbfc7564", "ダンジョン": "1518709268805-4e9042af9f23",
        "王宮": "1544939514-aa98d908bc47", "図書館": "1521587760476-6c12a4b040da",
        "サイバー": "1535295972055-1c762f4483e5", "シンプル": ""
    }
    bg_url = f"https://images.unsplash.com/photo-{wallpapers.get(wallpaper, '')}?auto=format&fit=crop&w=1920&q=80" if wallpapers.get(wallpaper) else ""
    
    bg_css = f"""
        background-image: linear-gradient(rgba(0,0,0,{bg_opacity}), rgba(0,0,0,{bg_opacity})), url("{bg_url}");
        background-attachment: fixed; background-size: cover; background-color: #1E1E1E;
    """ if bg_url else "background-color: #1E1E1E;"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DotGothic16&family=Yomogi&family=Hachi+Maru+Pop&family=Shippori+Mincho&family=Yuji+Syuku&display=swap');
    
    .stApp {{ {bg_css} }}
    
    html, body, [class*="css"] {{ font-family: {font_family} !important; color: #ffffff; }}
    .stMarkdown, .stText, h1, h2, h3, p, span, div {{ color: #ffffff !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }}
    
    div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stExpander"], div[data-testid="stForm"] {{
        background-color: rgba(30, 30, 30, 0.85) !important;
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255,255,255,0.15);
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }}
    
    .ranking-card {{
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        border: 1px solid rgba(255,255,255,0.2);
    }}
    .rank-num {{ font-size: 24px; font-weight: bold; width: 50px; text-align: center; margin-right: 15px; }}
    .rank-name {{ font-size: 18px; font-weight: bold; }}
    .rank-title {{ font-size: 14px; color: #FFD700 !important; }}
    .rank-score {{ margin-left: auto; font-size: 20px; font-weight: bold; color: #00FF00 !important; }}
    
    button[kind="primary"] {{
        background: linear-gradient(45deg, #FF4B4B, #FF914D) !important;
        border: none !important;
        transition: transform 0.2s;
    }}
    button[kind="primary"]:hover {{ transform: scale(1.05); }}
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
                "xp": 0, "coins": 0, "unlocked_themes": "標準", "current_title": "見習い",
                "unlocked_titles": "見習い", "current_wallpaper": "草原", "unlocked_wallpapers": "草原",
                "current_bgm": "なし", "unlocked_bgm": "なし", "custom_title_unlocked": False}
        supabase.table("users").insert(data).execute()
        return True
    except: return False

def get_user_data(username):
    try:
        res = supabase.table("users").select("*").eq("username", username).execute()
        return res.data[0] if res.data else None
    except: return None

# --- ランキングデータ取得 (称号対応) ---
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

# --- 科目管理 ---
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
    return m

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

# --- メイン処理 ---
def main():
    if "logged_in" not in st.session_state: st.session_state.update({"logged_in": False, "username": "", "is_studying": False, "start_time": None, "celebrate": False, "toast_msg": None})

    if not st.session_state["logged_in"]:
        st.title("🛡️ ログイン")
        mode = st.selectbox("モード", ["ログイン", "新規登録"])
        u = st.text_input("ユーザーID")
        p = st.text_input("パスワード", type="password")
        if mode == "新規登録":
            n = st.text_input("ニックネーム")
            if st.button("登録"):
                if add_user(u, p, n): st.success("登録成功！ログインしてください")
                else: st.error("エラー：IDが重複しています")
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

    # デザイン適用
    apply_design(user.get('unlocked_themes', '標準').split(',')[0], user.get('current_wallpaper', '草原'))

    # BGM再生 (集中モードのみ)
    if st.session_state["is_studying"]:
        bgm = user.get('current_bgm', 'なし')
        if bgm != 'なし' and BGM_DATA.get(bgm):
            st.audio(BGM_DATA[bgm], format="audio/ogg", loop=True, autoplay=True)

    # サイドバー
    with st.sidebar:
        st.markdown(f"### 👤 {user['nickname']}")
        st.markdown(f"**👑 {user.get('current_title', '見習い')}**")
        st.progress(min(1.0, (user['xp'] % 100) / 100))
        st.caption(f"Lv.{(user['xp']//100)+1} | XP: {user['xp']} | Coin: {user['coins']}")
        
        if st.button("ログアウト"):
            st.session_state["logged_in"] = False
            st.rerun()
        
        st.divider()
        st.subheader("⚙️ 設定")
        # 壁紙変更
        walls = user['unlocked_wallpapers'].split(',')
        cur_w = user.get('current_wallpaper', '草原')
        new_w = st.selectbox("壁紙", walls, index=walls.index(cur_w) if cur_w in walls else 0)
        if new_w != cur_w:
            supabase.table("users").update({"current_wallpaper": new_w}).eq("username", user['username']).execute()
            st.rerun()
        
        # BGM変更
        bgms = user.get('unlocked_bgm', 'なし').split(',')
        if 'なし' not in bgms: bgms.insert(0, 'なし')
        cur_b = user.get('current_bgm', 'なし')
        new_b = st.selectbox("集中BGM", bgms, index=bgms.index(cur_b) if cur_b in bgms else 0)
        if new_b != cur_b:
            supabase.table("users").update({"current_bgm": new_b}).eq("username", user['username']).execute()
            st.rerun()

    # 集中モード画面
    if st.session_state["is_studying"]:
        st.empty()
        st.markdown(f"<h1 style='text-align: center; font-size: 3em;'>🔥 {st.session_state['current_subject']} 中...</h1>", unsafe_allow_html=True)
        elapsed = int(time.time() - st.session_state["start_time"])
        h, m, s = elapsed//3600, (elapsed%3600)//60, elapsed%60
        st.markdown(f"<div style='text-align: center; font-size: 6em; font-weight: bold; color: #00FF00; text-shadow: 0 0 20px #00FF00;'>{h:02}:{m:02}:{s:02}</div>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("⏹️ 終了して記録", use_container_width=True, type="primary"):
                mins = max(1, elapsed // 60)
                add_study_log(user['username'], st.session_state['current_subject'], mins, date.today())
                st.session_state["is_studying"] = False
                st.session_state["celebrate"] = True
                st.rerun()
        time.sleep(1)
        st.rerun()
        return

    # メイン画面
    if st.session_state.get("celebrate"):
        st.balloons()
        st.session_state["celebrate"] = False
    
    if st.session_state.get("toast_msg"):
        st.toast(st.session_state["toast_msg"])
        st.session_state["toast_msg"] = None

    t1, t2, t3, t4, t5 = st.tabs(["⏱️ タイマー", "📝 タスク", "🏆 ランキング", "🛒 ショップ", "📚 科目"])

    with t1: # タイマー
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
                mm = st.number_input("時間(分)", 1, 999, 30)
                ms = st.text_input("科目", value=s_name if s_name != "その他" else "")
                if st.form_submit_button("記録"):
                    add_study_log(user['username'], ms, mm, md)
                    st.session_state["toast_msg"] = "記録しました！"
                    st.session_state["celebrate"] = True
                    st.rerun()
        
        st.divider()
        st.write("📖 **最近の記録**")
        logs = get_study_logs(user['username'])
        if not logs.empty:
            for _, r in logs.head(5).iterrows():
                lc1, lc2 = st.columns([0.8, 0.2])
                lc1.write(f"・{r['subject']} ({r['duration_minutes']}分) - {r['study_date']}")
                if lc2.button("削除", key=f"dl_{r['id']}"):
                    if delete_study_log(r['id'], user['username'], r['duration_minutes']):
                        st.session_state["toast_msg"] = "削除しました"
                        st.rerun()

    with t2: # タスク
        c1, c2 = st.columns([2, 1])
        with c1:
            tasks = get_tasks(user['username'])
            if not tasks.empty:
                for _, task in tasks.iterrows():
                    if task['status'] == '未完了':
                        cc1, cc2 = st.columns([0.8, 0.2])
                        cc1.info(f"**{task['task_name']}** (期限: {task['due_date']})")
                        if cc2.button("完了", key=f"c_{task['id']}"):
                            complete_task(task['id'], user['username'])
                            st.session_state["celebrate"] = True
                            st.rerun()
            else:
                st.info("タスクはありません")
        with c2:
            with st.form("new_task"):
                tn = st.text_input("タスク名")
                td = st.date_input("期限")
                tp = st.selectbox("優先度", ["高", "中", "低"])
                if st.form_submit_button("追加"):
                    add_task(user['username'], tn, td, tp)
                    st.rerun()

    with t3: # ランキング（豪華版）
        st.subheader("🏆 週間ランキング")
        df_rank = get_weekly_ranking()
        if not df_rank.empty:
            for i, row in df_rank.iterrows():
                rank = i + 1
                medal = "🥇" if rank==1 else "🥈" if rank==2 else "🥉" if rank==3 else f"{rank}位"
                bg = "rgba(255,215,0,0.2)" if rank==1 else "rgba(192,192,192,0.2)" if rank==2 else "rgba(205,127,50,0.2)" if rank==3 else "transparent"
                border = "2px solid #FFD700" if rank==1 else "1px solid #555"
                
                st.markdown(f"""
                <div class="ranking-card" style="border: {border}; background: {bg};">
                    <div class="rank-num">{medal}</div>
                    <div style="flex-grow: 1;">
                        <div class="rank-name">{row['nickname']}</div>
                        <div class="rank-title">👑 {row.get('current_title', '見習い')}</div>
                    </div>
                    <div class="rank-score">{int(row['duration_minutes'])} min</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("データが集計されていません")

    with t4: # ショップ
        st.write(f"所持コイン: **{user['coins']} 💰**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("### 🖼️ 壁紙")
            items = [("夕焼け", 500), ("夜空", 800), ("ダンジョン", 1200), ("王宮", 2000)]
            for n, p in items:
                if st.button(f"{n} ({p}G)", key=f"w_{n}", disabled=(n in user['unlocked_wallpapers'])):
                    if user['coins'] >= p:
                        nl = user['unlocked_wallpapers'] + f",{n}"
                        supabase.table("users").update({"coins": user['coins']-p, "unlocked_wallpapers": nl}).eq("username", user['username']).execute()
                        st.balloons()
                        st.rerun()
        with c2:
            st.markdown("### 🎵 BGM")
            items = [("雨の音", 300), ("焚き火", 500), ("カフェ", 800)]
            for n, p in items:
                if st.button(f"{n} ({p}G)", key=f"b_{n}", disabled=(n in user.get('unlocked_bgm', ''))):
                    if user['coins'] >= p:
                        nl = user.get('unlocked_bgm', 'なし') + f",{n}"
                        supabase.table("users").update({"coins": user['coins']-p, "unlocked_bgm": nl}).eq("username", user['username']).execute()
                        st.balloons()
                        st.rerun()
        with c3:
            st.markdown("### 🎲 称号ガチャ")
            if st.button("1回 100G", type="primary"):
                if user['coins'] >= 100:
                    titles = ["駆け出し", "努力家", "集中王", "夜更かし", "天才", "凡人", "覚醒者", "勇者"]
                    got = random.choice(titles)
                    # DB更新
                    current_titles = user.get('unlocked_titles', '')
                    if got not in current_titles:
                        current_titles += f",{got}"
                    supabase.table("users").update({
                        "coins": user['coins']-100,
                        "unlocked_titles": current_titles,
                        "current_title": got
                    }).eq("username", user['username']).execute()
                    st.toast(f"🎉 称号『{got}』を獲得しました！")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("コイン不足")

    with t5: # 科目管理
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
