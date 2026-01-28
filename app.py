import streamlit as st
from supabase import create_client, Client

# 1. Supabaseへの接続設定
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
except FileNotFoundError:
    st.error("secrets.toml が見つかりません。.streamlitフォルダの中に作成しましたか？")
    st.stop()
except KeyError:
    st.error("secrets.toml の中身が正しくありません。[supabase] の設定を確認してください。")
    st.stop()

@st.cache_resource
def init_connection():
    return create_client(url, key)

try:
    supabase: Client = init_connection()
except Exception as e:
    st.error(f"Supabaseへの接続に失敗しました: {e}")
    st.stop()

st.title("📝 Supabase Todo アプリ")

# 2. タスクの追加機能
with st.form("add_task_form", clear_on_submit=True):
    new_task = st.text_input("新しいタスクを入力")
    submitted = st.form_submit_button("追加")
    
    if submitted and new_task:
        data = {"task": new_task, "is_complete": False}
        try:
            supabase.table("todos").insert(data).execute()
            st.success("タスクを追加しました！")
            st.rerun()
        except Exception as e:
            st.error(f"書き込みエラー: {e}")

# 3. データの取得
try:
    response = supabase.table("todos").select("*").order("id", desc=True).execute()
    todos = response.data
except Exception as e:
    st.error(f"読み込みエラー: {e}")
    todos = []

# 4. タスク一覧の表示と操作
st.subheader("タスク一覧")

if not todos:
    st.info("タスクはまだありません。")

for todo in todos:
    col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
    
    with col1:
        is_done = st.checkbox("", value=todo["is_complete"], key=f"check_{todo['id']}")
    
    if is_done != todo["is_complete"]:
        supabase.table("todos").update({"is_complete": is_done}).eq("id", todo["id"]).execute()
        st.rerun()

    with col2:
        if todo["is_complete"]:
            st.write(f"~~{todo['task']}~~")
        else:
            st.write(todo["task"])
            
    with col3:
        if st.button("削除", key=f"del_{todo['id']}"):
            supabase.table("todos").delete().eq("id", todo["id"]).execute()
            st.rerun()