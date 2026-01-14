import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 模擬資料庫
# ==========================================
if 'db_users' not in st.session_state:
    st.session_state['db_users'] = {
        'admin': {'pwd': 'admin', 'expiry': '2099-12-31'},  # 管理員
        'vip':   {'pwd': '123',   'expiry': '2025-12-31'},  # 範例VIP
        'user':  {'pwd': '123',   'expiry': '2023-01-01'}   # 範例過期者
    }

if 'db_posts' not in st.session_state:
    st.session_state['db_posts'] = [
        {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "title": "【盤後重點】外資今日大買百億，權證主力動向解析",
            "content": "今日台積電(2330)出現明顯隔日沖買盤，主力「元大-向上」大舉敲進...",
            "img": None
        }
    ]

# 你的歐付寶收款連結
OPAY_URL = "https://payment.opay.tw/Broadcaster/Donate/B3C827A2B2E3ADEDDAFCAA4B1485C4ED"

# ==========================================
# 2. 核心功能函數
# ==========================================
def check_login(username, password):
    users = st.session_state['db_users']
    if username in users and users[username]['pwd'] == password:
        return True
    return False

def register_user(username, password):
    """註冊新用戶 (預設為過期狀態)"""
    users = st.session_state['db_users']
    if username in users:
        return False, "帳號已存在"
    
    # 設定昨天的日期 (代表一註冊就是過期，需要付款)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    users[username] = {'pwd': password, 'expiry': yesterday}
    return True, "註冊成功！請登入並付款開通。"

def check_subscription(username):
    if username == 'admin': return True, "永久會員"
    
    user_info = st.session_state['db_users'][username]
    expiry_str = user_info['expiry']
    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    
    if expiry_date >= today:
        return True, expiry_str
    else:
        return False, expiry_str

def add_days_to_user(username, days=30):
    if username in st.session_state['db_users']:
        user_info = st.session_state['db_users'][username]
        current_expiry = datetime.strptime(user_info['expiry'], "%Y-%m-%d").date()
        today = datetime.now().date()
        
        start_date = max(current_expiry, today)
        new_expiry = start_date + timedelta(days=days)
        
        st.session_state['db_users'][username]['expiry'] = new_expiry.strftime("%Y-%m-%d")
        return True
    return False

# ==========================================
# 3. 網站介面 (UI)
# ==========================================
st.set_page_config(page_title="權證主力戰情室", layout="wide", page_icon="📈")

# 隱藏選單
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- 側邊欄：登入/註冊系統 ---
with st.sidebar:
    st.title("🔐 會員中心")
    
    if 'logged_in_user' not in st.session_state:
        # 使用頁籤切換 登入/註冊
        tab_login, tab_register = st.tabs(["登入", "註冊新帳號"])
        
        with tab_login:
            user_input = st.text_input("帳號", key="login_user")
            pwd_input = st.text_input("密碼", type="password", key="login_pwd")
            if st.button("登入", key="btn_login"):
                if check_login(user_input, pwd_input):
                    st.session_state['logged_in_user'] = user_input
                    st.rerun()
                else:
                    st.error("帳號或密碼錯誤！")
        
        with tab_register:
            new_user = st.text_input("設定帳號", key="reg_user")
            new_pwd = st.text_input("設定密碼", type="password", key="reg_pwd")
            new_pwd_confirm = st.text_input("確認密碼", type="password", key="reg_pwd2")
            
            if st.button("立即註冊", key="btn_reg"):
                if new_pwd != new_pwd_confirm:
                    st.error("兩次密碼輸入不一致")
                elif not new_user or not new_pwd:
                    st.error("帳號密碼不能為空")
                else:
                    success, msg = register_user(new_user, new_pwd)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

    else:
        # 已登入狀態
        curr_user = st.session_state['logged_in_user']
        is_active, expiry_date = check_subscription(curr_user)
        
        st.write(f"歡迎回來，**{curr_user}**")
        
        if is_active:
            st.success(f"✅ 會員效期：{expiry_date}")
        else:
            st.error(f"⛔ 已過期：{expiry_date}")
            st.markdown("---")
            st.markdown(f"👉 **[點我續約 (歐付寶 $188)]({OPAY_URL})**")
            
        st.markdown("---")
        if st.button("登出"):
            del st.session_state['logged_in_user']
            st.rerun()

# --- 主畫面內容 ---

if 'logged_in_user' not in st.session_state:
    # 未登入首頁
    st.title("🚀 權證主力戰情室")
    st.markdown("### 每日盤後，掌握大戶資金流向")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("📊 **獨家籌碼表格**\n\n一眼看穿誰在買、誰在賣，不再當韭菜。")
    with col2:
        st.warning("🤖 **AI 深度點評**\n\n結合基本面與籌碼面的精闢分析，省去你 3 小時做功課時間。")
    
    st.divider()
    st.write("🔒 **請先在左側「註冊」或「登入」後觀看。**")
    st.markdown("### 💰 訂閱方案：每月只要 NT$ 188")
    st.link_button("👉 立即註冊並訂閱", OPAY_URL)

else:
    user = st.session_state['logged_in_user']
    is_vip, expiry = check_subscription(user)

    # --- 管理員後台 ---
    if user == 'admin':
        st.subheader("🔧 管理員後台")
        
        tab1, tab2 = st.tabs(["發布文章", "會員管理"])
        
        with tab1:
            st.write("在此發布每日戰情報告：")
            with st.form("post_form"):
                new_title = st.text_input("文章標題")
                new_content = st.text_area("文章內容 (支援 Markdown)", height=200)
                new_img = st.file_uploader("上傳圖片 (選填)", type=['png', 'jpg', 'jpeg'])
                submitted = st.form_submit_button("發布文章")
                
                if submitted:
                    post_data = {
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "title": new_title,
                        "content": new_content,
                        "img": new_img
                    }
                    st.session_state['db_posts'].insert(0, post_data)
                    st.success("文章發布成功！")
        
        with tab2:
            st.info("收到歐付寶通知後，請在此輸入對方註冊的帳號進行開通。")
            col_a, col_b = st.columns([3, 1])
            with col_a:
                target_user = st.text_input("輸入會員帳號")
            with col_b:
                st.write("") # 排版用
                st.write("")
                if st.button("加值 30 天"):
                    if add_days_to_user(target_user):
                        st.success(f"已成功幫 {target_user} 延長 30 天！")
                    else:
                        st.error("找不到此帳號，請確認對方是否已註冊。")
            
            # 顯示所有會員 (方便你查看)
            st.write("📋 目前註冊會員列表：")
            st.json(st.session_state['db_users'])

        st.divider()

    # --- VIP 內容區 ---
    if is_vip:
        st.title("📊 主力戰情日報")
        
        for post in st.session_state['db_posts']:
            with st.container():
                st.markdown(f"### {post['title']}")
                st.caption(f"發布時間: {post['date']}")
                
                if post['img']:
                    st.image(post['img'])
                
                st.write(post['content'])
                st.divider()
    
    # --- 過期會員區 ---
    else:
        st.warning("⛔ 您的會員權限尚未開通或已到期。")
        st.write("請依照以下步驟開通：")
        st.markdown(f"""
        1. 點擊下方按鈕前往歐付寶付款 (**$188/月**)。
        2. 付款時，請在備註欄填寫您的帳號： **{user}**
        3. 付款完成後，管理員將在 12 小時內為您開通權限。
        """)
        
        st.link_button("👉 前往付款 (歐付寶)", OPAY_URL)
        
        st.write("#### 🔒 最新文章列表 (VIP限定)")
        for post in st.session_state['db_posts']:
            st.info(f"🔒 {post['date']} | {post['title']}")
