import streamlit as st
import pandas as pd
import random
import datetime
import os
from gtts import gTTS
import io

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
    return pd.read_csv("data.csv")

try:
    df = load_data()
    # 列名の表記揺れ対策（「やさしい日本語」でも「やさしいにほんご」でも動くようにする）
    df.columns = [col.strip() for col in df.columns]
    if 'やさしいにほんご' in df.columns and 'やさしい日本語' not in df.columns:
        df = df.rename(columns={'やさしいにほんご': 'やさしい日本語'})
except Exception as e:
    st.error("data.csv が見つからないか、形式が正しくありません。")
    st.stop()

# --- 2. スプレッドシート（またはローカルCSV）への書き込み関数 ---
def save_consultation(name, category, content):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_data = [timestamp, name, category, content]

    try:
        if GSPREAD_AVAILABLE and "gcp_service_account" in st.secrets:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            gc = gspread.authorize(credentials)
            
            # 【重要】スプレッドシート名を「相談・提案窓口」に変更
            workbook = gc.open("相談・提案窓口")
            # 一番最初のワークシートを指定
            worksheet = workbook.get_worksheet(0)
            
            worksheet.append_row(new_data)
            return True, "スプレッドシートへの保存に成功しました！"
        else:
            return False, "Streamlit Secretsに認証情報（gcp_service_account）が見つかりません。Secretsの設定を確認してください。"
    except Exception as e:
        # エラーの原因を分かりやすく画面に返す
        return False, f"スプレッドシート接続エラー: {str(e)}"

# --- 3. 音声生成・再生関数 ---
def play_audio(text):
    try:
        tts = gTTS(text=text, lang='ja')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format='audio/mp3')
    except Exception as e:
        st.warning("音声の生成に失敗しました。")

# --- 4. セッション状態（State）の初期化 ---
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

# タイトルエリア（常時表示）
st.title("🏥 介護用語学習アプリ")
st.subheader("外国人スタッフ向け クイズ＆サポート")

# 相談フォームを表示するかどうかのフラグ
show_form = False

# --- 5. メインコンテンツ（クイズ制御） ---

# 【画面A】問題数選択画面（初期状態）
if not st.session_state.quiz_started:
    st.write("日本の介護現場でよく使う言葉を勉強しましょう。")
    show_form = True  # 最初の画面ではフォームを表示
    
    max_questions = len(df)
    options = [5, 10, 20, 30]  # 問題数の選択肢を30問までに制限
    options = [opt for opt in options if opt <= max_questions]
    if not options:
        options = [max_questions]
    
    num_choice = st.selectbox("何問クイズに挑戦しますか？", options)
    
    if st.button("クイズを始める 🚀", use_container_width=True):
        num_to_sample = int(num_choice)
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

    if current_idx < total_q:
        st.markdown(f"### 📝 問題 {current_idx + 1} / {total_q}")
        row = quiz_list[current_idx]
        
        st.info(f"「**{row['用語']}**」の意味は何ですか？")
        
        # 音声再生ボタン（復活）
        st.write("🔊 用語のよみをきく：")
        play_audio(row['用語'])
        
        # やさしい日本語の表示ロジック（復活）
        display_easy_ja = ""
        if 'やさしい日本語' in row and pd.notna(row['やさしい日本語']):
            display_easy_ja = row['やさしい日本語']
        elif 'やさしいにほんご' in row and pd.notna(row['やさしいにほんご']):
            display_easy_ja = row['やさしいにほんご']
            
        if display_easy_ja:
            st.caption(f"💡 やさしいにほんご：{display_easy_ja}")
            
        choices = [row['正しい意味'], row['不正解1'], row['不正解2']]
        random.seed(current_idx)
        random.shuffle(choices)
        
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
                    
                if '解説' in row and pd.notna(row['解説']):
                    st.write(f"📖 **解説:** {row['解説']}")
                if 'インドネシア語' in row and pd.notna(row['インドネシア語']):
                    st.write(f"🇮🇩 **Bahasa Indonesia:** {row['インドネシア語']}")
                
                st.session_state.current_index += 1
                st.form_submit_button("次の問題へ ➡️")

    # 【画面C】全問終了・リザルト画面
    else:
        st.markdown("### 🏁 クイズ終了！")
        show_form = True  # クイズ終了画面でもフォームを表示
        score = st.session_state.score
        st.metric(label="あなたの正解数", value=f"{score} / {total_q}")
        
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
                        
        if st.button("もう一度最初から遊ぶ 🔄", use_container_width=True):
            st.session_state.quiz_started = False
            st.rerun()

# --- 6. 提案・相談フォーム（条件付き表示） ---
if show_form:
    st.write("---")
    st.subheader("💬 アプリへの提案や、業務・生活の相談窓口")
    st.write("日本の生活や仕事で困っていること、アプリへの要望があれば教えてください。")
    st.caption("※「仕事、生活の相談」以外は、匿名（名前なし）でも送信できます。")

    with st.form(key="consultation_form", clear_on_submit=True):
        category = st.selectbox(
            "内容の種類を選んでください", 
            ["アプリに関すること", "仕事、生活の相談", "その他"]
        )
        name = st.text_input("お名前（ニックネーム）")
        content = st.text_area("具体的な内容（必須）")
        
        submit_consult = st.form_submit_button(label="送信する")
        
        if submit_consult:
            if not content.strip():
                st.error("❌ 具体的な内容を入力してください。")
            elif category == "仕事、生活の相談" and not name.strip():
                st.error("⚠️ 「仕事、生活の相談」の場合は、必ずあなたのお名前を入力してください。")
            else:
                final_name = name.strip() if name.strip() else "匿名"
                
                # スプレッドシートへの保存を実行
                success, message = save_consultation(final_name, category, content)
                
                if success:
                    st.success(f"⭕ {message}")
                else:
                    # 失敗した場合はエラー原因を画面にオレンジ色で表示する
                    st.warning(f"⚠️ {message}")
