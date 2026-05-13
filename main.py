import streamlit as st
import pandas as pd
import random

# --- 1. 音声読み上げ用のJavaScript関数（より安定した書き方に変更） ---
def speak_text(text, voice_key):
    js_code = f"""
    <script>
    (function() {{
        window.speechSynthesis.cancel();
        var msg = new SpeechSynthesisUtterance();
        msg.text = "{text}";
        msg.lang = 'ja-JP';
        msg.rate = 1.0;
        window.speechSynthesis.speak(msg);
    }})();
    </script>
    """
    # st.components.v1.html ではなく st.html または components.html を使います
    from streamlit.components.v1 import html
    html(js_code, height=0, key=voice_key)

# --- 2. 初期設定とデータ読み込み ---
if "wrong_list" not in st.session_state:
    st.session_state.wrong_list = []

st.set_page_config(page_title="介護用語トレーニング", layout="centered")

@st.cache_data
def load_data():
    return pd.read_csv("data.csv")

all_df = load_data()

# セッション状態の初期化
if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None
    st.session_state.index = 0
    st.session_state.answered = False
    st.session_state.correct_count = 0
    st.session_state.current_options = []
    st.session_state.max_questions = 0
    st.session_state.voice_trigger = 0

# --- 3. 出題数選択画面 ---
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

# --- 4. 全問題終了後の画面 ---
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

# --- 5. クイズ画面 ---
row = df.iloc[st.session_state.index]

st.title("🏥 介護用語クイズ")
st.progress(st.session_state.index / len(df))
st.write(f"進捗: {st.session_state.index + 1} / {len(df)} 問目")

st.info(f"「**{row['用語']}**」はどういう意味ですか？")

# ボタン部分
if st.button("🔊 用語を読み上げる"):
    st.session_state.voice_trigger += 1
    # 関数内で読み込みを行うことで TypeError を回避します
    speak_text(row['用語'], f"v_{st.session_state.index}_{st.session_state.voice_trigger}")

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

# --- 6. 回答後の処理 ---
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
        st.session_state.voice_trigger = 0
        st.rerun()
