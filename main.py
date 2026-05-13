import streamlit as st
import pandas as pd
import random
from gtts import gTTS
import io
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 音声読み上げ用の関数 ---
def speak_text(text):
    tts = gTTS(text=text, lang='ja')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    st.audio(fp, format='audio/mp3', autoplay=True)

# --- 2. スプレッドシート保存用の関数 ---
def save_to_spreadsheet(text):
    # 認証スコープの設定
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # Streamlit Secretsから認証情報を取得
    # ※GitHubに鍵を直接書かないためのセキュリティ対策
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)

    # 指定したスプレッドシートを開く（※名前を自分のシート名に合わせてください）
    sheet = client.open("介護アプリフィードバック").sheet1
    sheet.append_row([pd.Timestamp.now(tz='Asia/Tokyo').strftime('%Y-%m-%d %H:%M:%S'), text])

# --- 3. 初期設定とデータ読み込み ---
if "wrong_list" not in st.session_state:
    st.session_state.wrong_list = []

st.set_page_config(page_title="介護用語トレーニング", layout="centered")

@st.cache_data
def load_data():
    return pd.read_csv("data.csv")

all_df = load_data()

# --- 4. サイドバー（フィードバック送信欄） ---
with st.sidebar:
    st.header("💡 フィードバック")
    st.write("改善案や追加してほしい用語を教えてください。")
    
    # 入力欄を先に定義します
    feedback_input = st.text_area("内容を入力してください", key="feedback_area")
    
    if st.button("フィードバックを送信"):
        if feedback_input:
            try:
                save_to_spreadsheet(feedback_input)
                st.success("ありがとうございます！送信されました。")
            except Exception as e:
                st.error("送信に失敗しました。設定を確認してください。")
                # print(e) # デバッグ用にエラー詳細を表示する場合
        else:
            st.warning("内容を入力してください。")

# --- 5. セッション状態の初期化 ---
if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None
    st.session_state.index = 0
    st.session_state.answered = False
    st.session_state.correct_count = 0
    st.session_state.current_options = []
    st.session_state.max_questions = 0

# --- 6. 出題数選択画面 ---
if st.session_state.quiz_data is None:
    st.title("🏥 介護用語クイズ")
    st.subheader("今日は何問解きますか？")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("10問"):
            st.session_state.max_questions = 10
    with col2:
        if st.button("20問"):
            st.session_state.max_questions = 20
    with col3:
        if st.button("30問"):
            st.session_state.max_questions = 30
            
    if st.session_state.max_questions > 0:
        num = min(st.session_state.max_questions, len(all_df))
        st.session_state.quiz_data = all_df.sample(n=num).reset_index(drop=True)
        st.rerun()
    st.stop()

# --- 7. 全問題終了後の画面 ---
df = st.session_state.quiz_data
if st.session_state.index >= len(df):
    st.balloons()
    st.header("🎉 終了！")
    st.subheader(f"正解数: {st.session_state.correct_count} / {len(df)}")
    
    st.write("---")
    st.subheader("🚩 苦手克服リスト")
    if st.session_state.wrong_list:
        for q in st.session_state.wrong_list:
            st.write(f"・ **{q}**")
    else:
        st.success("完璧です！")

    if st.button("メニューに戻る"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.stop()

# --- 8. クイズ画面 ---
row = df.iloc[st.session_state.index]

st.title("🏥 介護用語クイズ")
st.progress(st.session_state.index / len(df))
st.write(f"進捗: {st.session_state.index + 1} / {len(df)} 問目")

st.info(f"「**{row['用語']}**」はどういう意味ですか？")

if st.button("🔊 用語を読み上げる"):
    speak_text(row['用語'])

if not st.session_state.answered and not st.session_state.current_options:
    options = [row['正しい意味'], row['不正解1'], row['不正解2']]
    random.shuffle(options)
    st.session_state.current_options = options

choice = st.radio("答えを選んでください：", st.session_state.current_options, index=None, key=f"q_{st.session_state.index}")

if not st.session_state.answered:
    if st.button("回答する"):
        if choice is None:
            st.warning("選択肢を選んでください！")
        else:
            st.session_state.answered = True
            st.rerun()

# --- 9. 回答後の判定と解説 ---
if st.session_state.answered:
    if choice == row['正しい意味']:
        st.success("⭕ 正解です！")
        if 'last_counted' not in st.session_state or st.session_state.last_counted != st.session_state.index:
            st.session_state.correct_count += 1
            st.session_state.last_counted = st.session_state.index
    else:
        st.error(f"❌ 残念！ 正解は： **{row['正しい意味']}**")
        if row['用語'] not in st.session_state.wrong_list:
            st.session_state.wrong_list.append(row['用語'])

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**【やさしい日本語】**\n\n" + str(row['やさしい日本語']))
    with col2:
        st.success("**【Bahasa Indonesia】**\n\n" + str(row['インドネシア語']))
    
    st.write("**【くわしい解説】**")
    st.write(row['解説'])

    if st.button("次の問題へ ➡️"):
        st.session_state.index += 1
        st.session_state.answered = False
        st.session_state.current_options = []
        st.rerun()
