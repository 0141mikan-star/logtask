✅ Supa管理アプリ (Supabase版)

タスクを完了すると「盛大に褒めてくれる」モチベーションアップ型のタスク管理アプリです。
Supabase（クラウドデータベース）と連携しているため、ユーザー登録機能があり、どこからアクセスしても自分のタスクを管理できます。

**🚀 デモアプリはこちら:** [https://supabase-todo-app-yehzleuuxhto9q6hzjquel.streamlit.app/]

## ✨ 主な機能

* **🔐 ユーザー認証**:
    * アカウントの新規登録・ログイン機能。
    * ユーザーごとに個別のタスクリストを管理（他の人には見えません）。
* **📅 カレンダー連携**:
    * 登録したタスクをカレンダー形式で視覚的に確認。
    * Googleカレンダーへの登録リンク自動生成。
* **🎉 褒める機能**:
    * タスクを完了すると、画面に風船が飛び、ランダムなメッセージで褒めてくれます。
* **☁️ データの永続化**:
    * Supabase を使用しているため、アプリを閉じてもデータは消えません。

## 🛠 使用技術

* **Frontend**: Streamlit
* **Database**: Supabase (PostgreSQL)
* **Language**: Python
* **Libraries**:
    * `streamlit-calendar` (カレンダー表示)
    * `supabase` (DB接続)
    * `pandas` (データ操作)

## 💻 ローカルでの実行方法

このリポジトリをクローンして実行する場合の設定です。

1. **ライブラリのインストール**
   ```bash
   pip install -r requirements.txt
