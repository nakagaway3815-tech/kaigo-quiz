import streamlit as st
import pandas as pd
import random

# ページの設定
st.set_page_config(page_title="介護用語トレーニング", layout="centered")

# データの読み込み
@st.cache_data
def load_data():
    return pd.read_csv("data.csv")

df = load_data()

# セッション状態の初期化
if 'index' not in st.session_state:
    st.session_state.index = 0
    st.session_state.answered = False
    st.session_state.correct_count = 0
    st.session_state.current_options = []

# 全問題終了後の画面
if st.session_state.index >= len(df):
    st.balloons()
    st.header("🎉 全問終了！")
    st.subheader(f"正解数: {st.session_state.correct_count} / {len(df)}")
    if st.button("もう一度最初からやる"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
    st.stop()

# 現在の問題データ
row = df.iloc[st.session_state.index]

st.title("🏥 介護用語クイズ")
st.progress(st.session_state.index / len(df))
st.subheader(f"問題 {st.session_state.index + 1}:")
st.info(f"「**{row['用語']}**」はどういう意味ですか？")

# --- 重要：選択肢の管理 ---
# まだ回答していない、かつ選択肢が空の場合だけシャッフルして保存
if not st.session_state.answered and not st.session_state.current_options:
    # ここはCSVの列名と完全に一致させてください（① or 1）
    options = [row['正しい意味'], row['不正解1'], row['不正解2']]
    random.shuffle(options)
    st.session_state.current_options = options

# 選択肢の表示（保存された選択肢を使い続ける）
choice = st.radio("答えを選んでください：", st.session_state.current_options, index=None, key=f"q_{st.session_state.index}")

# 回答ボタン
if not st.session_state.answered:
    if st.button("回答する"):
        if choice is None:
            st.warning("選択肢を選んでください！")
        else:
            st.session_state.answered = True
            st.rerun()

# --- 回答後の処理 ---
if st.session_state.answered:
    if choice == row['正しい意味']:
        st.success("⭕ 正解です！ (Benar!)")
        # 正解数のカウント（二重カウント防止）
        if 'last_counted' not in st.session_state or st.session_state.last_counted != st.session_state.index:
            st.session_state.correct_count += 1
            st.session_state.last_counted = st.session_state.index
    else:
        st.error(f"❌ 残念！ (Salah)")
        st.write(f"正解は： **{row['正しい意味']}**")

    # 解説セクション
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**【やさしい日本語】**\n\n" + str(row['やさしい日本語']))
    with col2:
        st.success("**【Bahasa Indonesia】**\n\n" + str(row['インドネシア語']))
    
    st.write("**【くわしい解説】**")
    st.write(row['解説'])

    # 次へボタン
    if st.button("次の問題へ ➡️"):
        st.session_state.index += 1
        st.session_state.answered = False
        st.session_state.current_options = [] # 選択肢をクリア
        st.rerun()