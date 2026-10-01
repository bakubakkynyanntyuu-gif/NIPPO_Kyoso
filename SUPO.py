import streamlit as st
import json
import os
import time
import random
import pandas as pd
from datetime import datetime, date
from PIL import Image

# --- 設定 ---
PLAYER_PIN = "1234"
ADMIN_PIN = "2589"
DATA_FILE = "data.json"
IMAGE_DIR = "images"

os.makedirs(IMAGE_DIR, exist_ok=True)

st.set_page_config(page_title="日報掲示板", layout="centered")

# ==========================================
# 【最終調整】スマホ特化・横スクロール防止＆横並びCSS
# ==========================================
st.markdown("""
<style>
/* ボタンのパディング（内側の余白）を減らして、コンパクトに */
.stButton > button {
    padding: 0.2rem 0.2rem !important;
    min-height: 2.5rem !important;
}

/* スマホ画面での縦積みを解除し、画面幅にピタッと収める */
@media (max-width: 640px) {
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important; /* 絶対に横に並べる */
        gap: 4px !important; /* ボタン同士の隙間を小さく */
    }
    div[data-testid="column"] {
        min-width: 0 !important; /* 画面幅をオーバーするのを防ぐ */
        width: auto !important;
        flex: 1 1 0% !important; /* 指定した数（3列や5列）で均等に分割する */
    }
}
</style>
""", unsafe_allow_html=True)


# --- データ読み書き ---
def load_data():
  if not os.path.exists(DATA_FILE):
    return []
  try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  except:
    return []

def save_data(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

def save_uploaded_image(uploaded_file):
  img = Image.open(uploaded_file)
  if img.mode in ("RGBA", "P"):
    img = img.convert("RGB")
  img.thumbnail((800, 800))
  filename = f"img_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.jpg"
  filepath = os.path.join(IMAGE_DIR, filename)
  img.save(filepath, "JPEG", quality=80)
  return filepath

# --- おみくじ ---
def draw_omikuji():
  results = ["大吉", "中吉", "小吉", "吉", "凶", "大凶"]
  weights = [10, 20, 20, 20, 20, 10]
  res = random.choices(results, weights=weights, k=1)[0]
  comments = {
      "大吉": "自己ベスト更新の予感！キレキレです！",
      "中吉": "いいコンディション！今日のメニューもバッチリ！",
      "小吉": "地道なトレーニングが力になる日。",
      "吉": "焦らずマイペースに。継続は力なり！",
      "凶": "ケガに注意！ウォーミングアップは念入りに。",
      "大凶": "休むのも練習のうち。違和感があれば無理は禁物！",
  }
  return res, comments[res]

# --- セッション初期化 ---
if "logged_in" not in st.session_state:
  st.session_state.update({
      "logged_in": False,
      "role": "",
      "numpad_pin": "",
      "edit_post_id": None,
      "edit_comment_id": None,
      "omikuji_drawn": False,
      "fatigue_reported": {},
      "selected_tag": None,
      "tag_page": 0
  })

def add_num(num):
  if len(st.session_state["numpad_pin"]) < 4:
    st.session_state["numpad_pin"] += str(num)
def clear_num():
  st.session_state["numpad_pin"] = ""


# --- ログイン画面 ---
if not st.session_state["logged_in"]:
  st.title("🔐 日報掲示板")
  st.markdown("### パスワード入力")
  keyboard_pin = st.text_input("⌨️ キーボード用", type="password", max_chars=4)

  st.markdown("---")
  st.markdown("<div style='text-align: center;'>📱 <strong>スマホ用テンキー</strong></div>", unsafe_allow_html=True)
  display_pin = st.session_state["numpad_pin"].ljust(4, "〇")
  st.markdown(f"<h3 style='text-align: center; letter-spacing: 0.5em;'>{display_pin}</h3>", unsafe_allow_html=True)

  # 【変更】余白（スペーサー）を廃止し、素直に3等分して画面幅に収める
  col1, col2, col3 = st.columns(3)
  with col1:
    st.button("1", on_click=add_num, args=(1,), use_container_width=True)
    st.button("4", on_click=add_num, args=(4,), use_container_width=True)
    st.button("7", on_click=add_num, args=(7,), use_container_width=True)
    st.button("C", on_click=clear_num, use_container_width=True)
  with col2:
    st.button("2", on_click=add_num, args=(2,), use_container_width=True)
    st.button("5", on_click=add_num, args=(5,), use_container_width=True)
    st.button("8", on_click=add_num, args=(8,), use_container_width=True)
    st.button("0", on_click=add_num, args=(0,), use_container_width=True)
  with col3:
    st.button("3", on_click=add_num, args=(3,), use_container_width=True)
    st.button("6", on_click=add_num, args=(6,), use_container_width=True)
    st.button("9", on_click=add_num, args=(9,), use_container_width=True)

  st.markdown("<br>", unsafe_allow_html=True)
  final_pin = keyboard_pin if keyboard_pin else st.session_state["numpad_pin"]

  if st.button("ログインする", type="primary", use_container_width=True):
    if final_pin == PLAYER_PIN:
      st.session_state.update({"logged_in": True, "role": "player"})
      st.rerun()
    elif final_pin == ADMIN_PIN:
      st.session_state.update({"logged_in": True, "role": "admin"})
      st.rerun()
    else:
      st.error("パスワードが違います")
      st.session_state["numpad_pin"] = ""


# --- メイン画面 ---
else:
  data = load_data()
  data_changed = False
  current_now = datetime.now()

  for post in data:
    post_date = datetime.strptime(post["date"], "%Y/%m/%d %H:%M")
    if (current_now - post_date).days >= 10 and not post.get("archived", False):
      post["archived"] = True
      if post.get("images"):
        for img_path in post["images"]:
          if os.path.exists(img_path):
            try: os.remove(img_path)
            except: pass
        post["images"] = []
      data_changed = True
  if data_changed:
    save_data(data)

  # サイドバー（メニュー）
  with st.sidebar:
    st.title("📚 メニュー")
    if st.button("🏠 最新のタイムライン", use_container_width=True, type="primary"):
        st.session_state["selected_tag"] = None
        st.rerun()
    
    st.markdown("---")
    st.markdown("**🏷️ タグで探す**")
    
    all_tags = []
    for p in data:
        all_tags.extend(p.get("tags", []))
    unique_tags = sorted(list(set(all_tags)))
    
    if not unique_tags:
        st.caption("まだタグがありません")
    else:
        for t in unique_tags:
            if st.button(f"・{t}", key=f"side_tag_{t}", use_container_width=True):
                st.session_state["selected_tag"] = t
                st.session_state["tag_page"] = 0
                st.rerun()
                
    st.markdown("---")
    if st.button("🚪 ログアウト", use_container_width=True):
      st.session_state.update({"logged_in": False, "role": "", "numpad_pin": "", "selected_tag": None})
      st.rerun()

  # ⬇️ 【モードA】タグ検索結果の表示
  if st.session_state["selected_tag"]:
      tag = st.session_state["selected_tag"]
      st.title(f"🏷️ 「{tag}」の投稿")
      st.caption("※タイトルと本文のみを表示しています")
      
      filtered_posts = [p for p in data if tag in p.get("tags", [])]
      
      if not filtered_posts:
          st.info("該当する投稿がありません。")
      else:
          items_per_page = 5
          page = st.session_state["tag_page"]
          start_idx = page * items_per_page
          end_idx = start_idx + items_per_page
          
          for p in filtered_posts[start_idx:end_idx]:
              with st.container(border=True):
                  date_only = p["date"].split(" ")[0]
                  st.markdown(f"**{date_only}**")
                  st.subheader(p["title"])
                  st.write(p["content"])
          
          st.markdown("---")
          c1, c2, c3 = st.columns(3)
          with c1:
              if page > 0:
                  if st.button("◀ 前の5件", use_container_width=True):
                      st.session_state["tag_page"] -= 1
                      st.rerun()
          with c3:
              if end_idx < len(filtered_posts):
                  if st.button("次の5件 ▶", use_container_width=True):
                      st.session_state["tag_page"] += 1
                      st.rerun()

  # ⬇ 【モードB】通常のタイムライン表示
  else:
      col_title, col_omi = st.columns([6, 2])
      with col_title:
        st.title("📋 日報掲示板")

      with col_omi:
        btn_disabled = st.session_state["omikuji_drawn"]
        if st.button("⛩️ 運勢", disabled=btn_disabled, use_container_width=True):
          st.session_state["omikuji_drawn"] = True
          res, cmt = draw_omikuji()
          msg_area = st.empty()
          color = "#E74C3C" if "吉" in res else "#34495E"
          msg_area.markdown(f"<div style='text-align: center; margin: 20px 0;'><h1 style='font-size: 80px; color: {color}; margin-bottom: 0px;'>{res}！！</h1><p style='color: gray;'>{cmt}</p></div>", unsafe_allow_html=True)
          time.sleep(3)
          msg_area.empty()
          st.rerun()

      if st.session_state["role"] == "admin":
        with st.expander("📝 新しい日報・お知らせを投稿", expanded=False):
          with st.form("new_post_form", clear_on_submit=True):
            post_title = st.text_input("タイトル")
            post_intro = st.text_area("導入 (挨拶や背景など)")
            post_main = st.text_area("本題 (具体的なメニューや内容)")
            
            st.markdown("**➕ タグを追加 (最大3つまで)**")
            t_col1, t_col2, t_col3 = st.columns(3)
            with t_col1: tag1 = st.text_input("タグ 1", placeholder="例: 試合前")
            with t_col2: tag2 = st.text_input("タグ 2", placeholder="例: 下半身")
            with t_col3: tag3 = st.text_input("タグ 3")

            uploaded_files = st.file_uploader("画像を添付 (最大2枚まで)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

            if st.form_submit_button("投稿する"):
                if not post_intro and not post_main:
                    st.error("導入か本題のどちらかは入力してください。")
                elif len(uploaded_files) > 2:
                    st.error("エラー: 画像は2枚までにしてください。")
                else:
                    saved_image_paths = [save_uploaded_image(f) for f in uploaded_files]
                    merged_content = f"{post_intro}\n\n{post_main}".strip()
                    input_tags = [t.strip() for t in [tag1, tag2, tag3] if t.strip()]

                    new_post = {
                        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "date": datetime.now().strftime("%Y/%m/%d %H:%M"),
                        "title": post_title,
                        "content": merged_content,
                        "tags": input_tags,
                        "images": saved_image_paths,
                        "comments": [],
                        "reactions": {"👍": 0, "😊": 0, "❤️": 0, "😢": 0, "🏋️": 0},
                        "fatigue_logs": [],
                        "archived": False,
                    }
                    data.insert(0, new_post)
                    save_data(data)
                    st.rerun()

      st.divider()

      active_posts_count = sum(1 for p in data if not p.get("archived", False))
      if active_posts_count == 0:
        st.info("最近の投稿はありません。")

      for i, post in enumerate(data):
        if post.get("archived", False):
          continue

        with st.container(border=True):
          if st.session_state["edit_post_id"] == post["id"]:
            st.info("✏️ 投稿を編集中")
            edit_title = st.text_input("タイトル", post["title"], key=f"et_{post['id']}")
            edit_content = st.text_area("本文", post["content"], key=f"ec_{post['id']}", height=150)
            
            existing_tags = post.get("tags", [])
            st.markdown("**タグの編集**")
            et_col1, et_col2, et_col3 = st.columns(3)
            with et_col1: e_tag1 = st.text_input("タグ1", existing_tags[0] if len(existing_tags)>0 else "", key=f"et1_{post['id']}")
            with et_col2: e_tag2 = st.text_input("タグ2", existing_tags[1] if len(existing_tags)>1 else "", key=f"et2_{post['id']}")
            with et_col3: e_tag3 = st.text_input("タグ3", existing_tags[2] if len(existing_tags)>2 else "", key=f"et3_{post['id']}")

            e_col1, e_col2 = st.columns(2)
            if e_col1.button("保存する", key=f"esave_{post['id']}", type="primary"):
              post["title"] = edit_title
              post["content"] = edit_content
              post["tags"] = [t.strip() for t in [e_tag1, e_tag2, e_tag3] if t.strip()]
              st.session_state["edit_post_id"] = None
              save_data(data)
              st.rerun()
            if e_col2.button("キャンセル", key=f"ecancel_{post['id']}"):
              st.session_state["edit_post_id"] = None
              st.rerun()
          else:
            date_only = post["date"].split(" ")[0]
            
            # 【変更】編集・削除ボタンが横並びで潰れないように比率を微調整
            h_col1, h_col2, h_col3 = st.columns([7, 1.5, 1.5])

            with h_col1:
              st.subheader(post["title"])
              st.markdown(f"**{date_only}**")

            if st.session_state["role"] == "admin":
              with h_col2:
                if st.button("✏️", key=f"p_edit_{post['id']}", help="投稿を編集"):
                  st.session_state["edit_post_id"] = post["id"]
                  st.rerun()
              with h_col3:
                if st.button("🗑️", key=f"p_del_{post['id']}", help="投稿を削除"):
                  data.remove(post)
                  save_data(data)
                  st.rerun()

            if post.get("tags"):
                st.markdown(" ".join([f"`🏷️{t}`" for t in post["tags"]]))

            st.write(post["content"])

            if post.get("images"):
              img_cols = st.columns(len(post["images"]))
              for idx, img_path in enumerate(post["images"]):
                if os.path.exists(img_path):
                  with img_cols[idx]:
                    st.image(img_path, use_container_width=True)

          st.markdown("---")
          if "reactions" not in post:
            post["reactions"] = {"👍": 0, "😊": 0, "❤️": 0, "😢": 0, "🏋️": 0}

          # 【変更】余白をなくし、素直に5等分して表示
          cols = st.columns(5)
          emojis = ["👍", "😊", "❤️", "😢", "🏋️"]
          for col, emoji in zip(cols, emojis):
            count = post["reactions"].get(emoji, 0)
            with col:
              if st.button(f"{emoji} {count}", key=f"react_{emoji}_{post['id']}", use_container_width=True):
                post["reactions"][emoji] = count + 1
                save_data(data)
                st.rerun()

          with st.expander("⚡ 今日のコンディションを報告する"):
            is_reported = st.session_state["fatigue_reported"].get(post['id'], False)
            if is_reported:
              st.success("今日のコンディション報告ありがとうございます！")
            else:
              st.caption("今の状態を選んでタップ！（1回のみ）")
              
              # 【変更】ここも素直に5等分
              f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
              fatigue_options = [("1:元気", "1"), ("2:良好", "2"), ("3:普通", "3"), ("4:疲労", "4"), ("5:限界", "5")]
              for col, (label, val) in zip([f_col1, f_col2, f_col3, f_col4, f_col5], fatigue_options):
                with col:
                  if st.button(label, key=f"fatigue_{val}_{post['id']}", use_container_width=True):
                    if "fatigue_logs" not in post: post["fatigue_logs"] = []
                    post["fatigue_logs"].append({"level": val, "time": datetime.now().strftime("%m/%d %H:%M")})
                    st.session_state["fatigue_reported"][post['id']] = True
                    save_data(data)
                    st.toast(f"疲労度『{label}』を記録しました！お疲れ様です！", icon="✅")
                    st.rerun()

            if st.session_state["role"] == "admin" and post.get("fatigue_logs"):
              st.markdown("---")
              st.markdown("**📊 チームの疲労度傾向 (管理者用)**")
              f_counts = {"1: 元気": 0, "2: 良好": 0, "3: 普通": 0, "4: 疲労": 0, "5: 限界": 0}
              for log in post["fatigue_logs"]:
                if log["level"] == "1": f_counts["1: 元気"] += 1
                elif log["level"] == "2": f_counts["2: 良好"] += 1
                elif log["level"] == "3": f_counts["3: 普通"] += 1
                elif log["level"] == "4": f_counts["4: 疲労"] += 1
                elif log["level"] == "5": f_counts["5: 限界"] += 1
              df_fatigue = pd.DataFrame(list(f_counts.values()), index=list(f_counts.keys()), columns=["人数"])
              st.bar_chart(df_fatigue)

          # --- コメント表示 ---
          if post.get("comments"):
            st.markdown("**💬 コメント**")
            for c_idx, comment in enumerate(post.get("comments", [])):
              c_id = comment.get("id", f"{post['id']}_{c_idx}")
              is_author = (comment.get("is_admin", False) or comment.get("name") == "BAKU")
              avatar_icon = "🔵" if is_author else "🔴"

              with st.chat_message("user", avatar=avatar_icon):
                if st.session_state["edit_comment_id"] == c_id:
                  new_text = st.text_input("コメントを編集", comment["text"], key=f"ct_{c_id}")
                  cc1, cc2 = st.columns(2)
                  if cc1.button("保存", key=f"csave_{c_id}", type="primary"):
                    comment["text"] = new_text
                    st.session_state["edit_comment_id"] = None
                    save_data(data)
                    st.rerun()
                  if cc2.button("キャンセル", key=f"ccancel_{c_id}"):
                    st.session_state["edit_comment_id"] = None
                    st.rerun()
                else:
                  c_col1, c_col2, c_col3 = st.columns([7, 1.5, 1.5])
                  with c_col1:
                    st.markdown(f"**{comment['name']}**   {comment['text']}")

                  if st.session_state["role"] == "admin":
                    with c_col2:
                      if st.button("✏️", key=f"cedit_{c_id}", help="コメントを編集"):
                        st.session_state["edit_comment_id"] = c_id
                        st.rerun()
                    with c_col3:
                      if st.button("🗑️", key=f"cdel_{c_id}", help="コメントを削除"):
                        post["comments"].remove(comment)
                        save_data(data)
                        st.rerun()

          # --- コメント投稿フォーム ---
          with st.expander("✍️ コメントを書く (匿名OK)", expanded=False):
            with st.form(key=f"comment_form_{post['id']}", clear_on_submit=True):
              default_name = "BAKU" if st.session_state["role"] == "admin" else ""
              commenter_name = st.text_input("ニックネーム (最大8文字)", value=default_name, max_chars=8, placeholder="匿名可")
              comment_text = st.text_input("コメント")

              if st.form_submit_button("送信") and commenter_name and comment_text:
                new_comment = {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                    "name": commenter_name,
                    "text": comment_text,
                    "date": datetime.now().strftime("%Y/%m/%d %H:%M"),
                    "is_admin": (st.session_state["role"] == "admin"),
                }
                post["comments"].append(new_comment)
                save_data(data)
                st.rerun()

      # --- アーカイブ表示エリア ---
      st.divider()
      st.subheader("📦 アーカイブ (過去の投稿)")
      with st.expander("日付を選んで過去の日報を見る"):
        selected_date = st.date_input("表示する日付を選択してください")
        archived_posts = [
            p for p in data
            if p.get("archived", False) and datetime.strptime(p["date"], "%Y/%m/%d %H:%M").date() == selected_date
        ]

        if not archived_posts:
          st.info("この日付の過去の投稿はありません。")
        else:
          for post in archived_posts:
            with st.container(border=True):
              date_only = post["date"].split(" ")[0]
              st.subheader(post["title"])
              st.markdown(f"**{date_only}**")
              if post.get("tags"):
                  st.markdown(" ".join([f"`🏷️{t}`" for t in post["tags"]]))
              st.write(post["content"])

              if post.get("comments"):
                st.markdown("**💬 コメント**")
                for comment in post.get("comments", []):
                  is_author = (comment.get("is_admin", False) or comment.get("name") == "BAKU")
                  avatar_icon = "🔵" if is_author else "🔴"
                  with st.chat_message("user", avatar=avatar_icon):
                    st.markdown(f"**{comment['name']}**   {comment['text']}")
