import streamlit as st
import pandas as pd
import random

# --- 1. 初期設定 ---
# 間違えた問題を記録する場所を作る
if "wrong_list" not in st.session_state:
    st.session_state.wrong_list = []

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

# --- 2. 全問題終了後の画面 ---
if st.session_state.index >= len(df):
    st.balloons()
    st.header("🎉 全問終了！")
    st.subheader(f"正解数: {st.session_state.correct_count} / {len(df)}")
    
    # 🚩 苦手克服リストの表示（インデントを下げて終了画面の中に入れました）
    st.write("---")
    st.subheader("🚩 苦手克服リスト")
    if st.session_state.wrong_list:
        st.write("以下の単語をもう一度確認しましょう：")
        for q in st.session_state.wrong_list:
            st.write(f"・ **{q}**")
    else:
        st.success("完璧です！間違えた問題はありません。")

    if st.button("もう一度最初からやる"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.stop()

# --- 3. クイズ画面の表示 ---
row = df.iloc[st.session_state.index]

st.title("🏥 介護用語クイズ")
st.progress(st.session_state.index / len(df))
st.subheader(f"問題 {st.session_state.index + 1}:")
st.info(f"「**{row['用語']}**」はどういう意味ですか？")

# 選択肢の管理
if not st.session_state.answered and not st.session_state.current_options:
    options = [row['正しい意味'], row['不正解1'], row['不正解2']]
    random.shuffle(options)
    st.session_state.current_options = options

# 選択肢の表示
choice = st.radio("答えを選んでください：", st.session_state.current_options, index=None, key=f"q_{st.session_state.index}")

# 回答ボタン
if not st.session_state.answered:
    if st.button("回答する"):
        if choice is None:
            st.warning("選択肢を選んでください！")
        else:
            st.session_state.answered = True
            st.rerun()

# --- 4. 回答後の処理 ---
if st.session_state.answered:
    if choice == row['正しい意味']:
        st.success("⭕ 正解です！ (Benar!)")
        if 'last_counted' not in st.session_state or st.session_state.last_counted != st.session_state.index:
            st.session_state.correct_count += 1
            st.session_state.last_counted = st.session_state.index
    else:
        st.error(f"❌ 残念！ (Salah)")
        st.write(f"正解は： **{row['正しい意味']}**")
        
        # 【修正ポイント！】item['question'] ではなく row['用語'] を使います
        if row['用語'] not in st.session_state.wrong_list:
            st.session_state.wrong_list.append(row['用語'])

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
        st.session_state.current_options = []
        st.rerun()
