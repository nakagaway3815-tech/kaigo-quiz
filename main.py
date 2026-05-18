import streamlit as st
import pandas as pd
import random
import datetime
import os

# Googleスプレッドシート連携用ライブラリの読み込み
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# --- 1. データの読み込み ---
@st.cache_data
def load_data():
    # 既存のdata.csv（クイズ問題）を読み込む
    return pd.read_csv("data.csv")

try:
    df = load_data()
except Exception as e:
    st.error("data.csv が見つからないか、形式が正しくありません。")
    st.stop()

# --- 2. スプレッドシート（またはローカルCSV）への書き込み関数 ---
def save_consultation(name, category, content):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # スプレッドシートの「相談・提案窓口」シートの列順（A:タイムスタンプ, B:名前, C:種類, D:内容）に合わせる
    new_data = [timestamp, name, category, content]

    # Streamlit Secretsから認証情報を取得してスプレッドシートに書き込みを試みる
    try:
        if GSPREAD_AVAILABLE and "gcp_service_account" in st.secrets:
            # 認証設定
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            gc = gspread.authorize(credentials)
            
            # スプレッドシート名と追加したワークシート（タブ）名を指定
            workbook = gc.open("介護アプリ管理シート")
            worksheet = workbook.worksheet("相談・提案窓口")
            
            # シートの最終行にデータを追加
            worksheet.append_row(new_data)
            return True
    except Exception as e:
        # エラーが起きた場合は、デバッグ用に標準出力（ログ）へ流す
        print(f"Spreadsheet Write Error: {e}")

    # 【フォールバック】スプレッドシートが使えない、または未設定の場合はローカルのCSVに保存
    csv_file = "consultations.csv"
    columns = ["タイムスタンプ", "名前（ニックネーム）", "内容の種類", "具体的な内容"]
    
    if os.path.exists(csv_file):
        consult_df = pd.read_csv(csv_file)
    else:
        consult_df = pd.DataFrame(columns=columns)
        
    new_row = pd.DataFrame([new_data], columns=columns)
    consult_df = pd.concat([consult_df, new_row], ignore_index=True)
    consult_df.to_csv(csv_file, index=False)
    return True

# --- 3. セッション状態（State）の初期化 ---
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []
if "wrong_list" not in st.session_state:
    st.session_state.wrong_list = []

# --- 4. 画面遷移の制御 ---

# 【画面A】問題数選択画面（初期状態）
if not st.session_state.quiz_started:
    st.title("🏥 介護用語学習アプリ")
    st.subheader("外国人スタッフ向け クイズ＆サポート")
    st.write("日本の介護現場でよく使う言葉を勉強しましょう。")
    
    # 問題数の選択
    max_questions = len(df)
    options = [5, 10, 20, "全問"]
    # 登録問題数が選択肢より少ない場合のケア
    options = [opt for opt in options if opt == "全問" or opt <= max_questions]
    
    num_choice = st.selectbox("何問クイズに挑戦しますか？", options)
    
    if st.button("クイズを始める 🚀", use_container_width=True):
        # 出題数を決定
        if num_choice == "全問":
            num_to_sample = max_questions
        else:
            num_to_sample = int(num_choice)
            
        # ランダムに問題を抽出してセッションに保存
        sampled_df = df.sample(n=num_to_sample).reset_index(drop=True)
        st.session_state.quiz_data = sampled_df.to_dict(orient="records")
        st.session_state.quiz_started = True
        st.session_state.current_index = 0
        st.session_state.score = 0
        st.session_state.wrong_list = []
        st.rerun()

# 【画面B】クイズ進行中
else:
    quiz_list = st.session_state.quiz_data
    total_q = len(quiz_list)
    current_idx = st.session_state.current_index

    # クイズがまだ残っている場合
    if current_idx < total_q:
        st.title(f"問題 {current_idx + 1} / {total_q}")
        row = quiz_list[current_idx]
        
        # 問題文表示（やさしい日本語も併記してアクセシビリティ向上）
        st.info(f"「**{row['用語']}**」の意味は何ですか？")
        if 'やさしい日本語' in row and pd.notna(row['やさしい日本語']):
            st.caption(f"💡 やさしいにほんご：{row['やさしい日本語']}")
            
        # 選択肢の作成（正解と不正解を混ぜる）
        choices = [row['正しい意味'], row['不正解1'], row['不正解2']]
        # 画面更新で選択肢の順序がシャッフルし直されないよう、インデックスを固定シードにする
        random.seed(current_idx)
        random.shuffle(choices)
        
        # クイズフォーム
        with st.form(key=f"quiz_form_{current_idx}"):
            answer = st.radio("答えを選んでください：", choices)
            submit = st.form_submit_button("回答を確定する")
            
            if submit:
                if answer == row['正しい意味']:
                    st.success("⭕ 正解（Benar）！")
                    st.session_state.score += 1
                else:
                    st.error(f"❌ 不正解... 正解は「{row['正しい意味']}」です。")
                    st.session_state.wrong_list.append(row['用語'])
                    
                # 解説とインドネシア語の表示
                if '解説' in row and pd.notna(row['解説']):
                    st.write(f"📖 **解説:** {row['解説']}")
                if 'インドネシア語' in row and pd.notna(row['インドネシア語']):
                    st.write(f"🇮🇩 **Bahasa Indonesia:** {row['インドネシア語']}")
                
                st.session_state.current_index += 1
                st.form_submit_button("次の問題へ ➡️")

    # 【画面C】全問終了・リザルト＆相談フォーム画面
    else:
        st.title("🏁 クイズ終了！")
        score = st.session_state.score
        st.metric(label="あなたの正解数", value=f"{score} / {total_q}")
        
        # スコアに応じたフィードバック
        accuracy = (score / total_q) * 100
        if accuracy == 100:
            st.balloons()
            st.success("素晴らしい！完璧です！💯")
        elif accuracy >= 70:
            st.success("よくできました！その調子です！✨")
        else:
            st.warning("もう一度復習してみましょう！📖")
            
        if st.session_state.wrong_list:
            st.write("🔺 **間違えた単語（もう一度確認しましょう）:**")
            st.write(", ".join(st.session_state.wrong_list))
            
        # --- 提案・相談フォーム ---
        st.write("---")
        st.subheader("💬 アプリへの提案や、業務・生活の相談窓口")
        st.write("日本の生活や仕事で困っていること、アプリへの要望があれば教えてください。")
        st.caption("※「仕事、生活の相談」以外は、匿名（名前なし）でも送信できます。")
        
        with st.form(key="consultation_form", clear_on_submit=True):
            # 1. カテゴリの選択
            category = st.selectbox(
                "内容の種類を選んでください", 
                ["アプリに関すること", "仕事、生活の相談", "その他"]
            )
            
            # 2. 名前の入力欄
            name = st.text_input("お名前（ニックネーム）")
            
            # 3. 本文の入力欄
            content = st.text_area("具体的な内容（必須）")
            
            submit_consult = st.form_submit_button(label="送信する")
            
            if submit_consult:
                # 入力バリデーション（チェック）
                if not content.strip():
                    st.error("❌ 具体的な内容を入力してください。")
                    
                # 「仕事、生活の相談」のときだけ名前入力を必須（空欄を禁止）にする
                elif category == "仕事、生活の相談" and not name.strip():
                    st.error("⚠️ 「仕事、生活の相談」の場合は、必ずあなたのお名前を入力してください。")
                    
                else:
                    # 空欄のまま「アプリに関すること」や「その他」を送った場合は自動で「匿名」に変換
                    final_name = name.strip() if name.strip() else "匿名"
                    
                    # 保存処理を実行
                    success = save_consultation(final_name, category, content)
                    if success:
                        st.success("⭕ 送信ありがとうございました！管理者に届けられました。")
                    else:
                        st.error("❌ 送信に失敗しました。時間をおいて再度お試しください。")
                        
        # 最初に戻るボタン
        if st.button("もう一度最初から遊ぶ 🔄", use_container_width=True):
            st.session_state.quiz_started = False
            st.rerun()
