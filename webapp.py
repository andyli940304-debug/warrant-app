import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 模擬資料庫 (暫存於記憶體中)
# ==========================================
if 'db_users' not in st.session_state:
    st.session_state['db_users'] = {
        # 格式: '帳號': {'pwd': '密碼', 'expiry': '到期日(YYYY-MM-DD)'}
        'admin': {'pwd': 'admin', 'expiry': '2099-12-31'},  # 管理員
        'vip':   {'pwd': '123',   'expiry': '2025-12-31'},  # 測試VIP
        'user':  {'pwd': '123',   'expiry': '2023-01-01'}   # 測試過期會員
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
# 2. 核心功能函數 (邏輯處理)
# ==========================================
def check_login(username, password):
    """驗證帳號密碼"""
    users = st.session_state['db_users']
    if username in users and users[username]['pwd'] == password:
        return True
    return False

def check_subscription(username):
    """檢查會員是否過期"""
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
    """(管理員用) 手動幫會員充值天數"""
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

# 🔥🔥🔥【這裡就是隱藏選單的魔法代碼】🔥🔥🔥
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# 🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥

# --- 側邊欄：登入/登出區 ---
with st.sidebar:
    st.title("🔐 會員中心")
    
    if 'logged_in_user' not in st.session_state:
        st.info("請先登入以查看戰情室")
        user_input = st.text_input("帳號")
        pwd_input = st.text_input("密碼", type="password")
        
        if st.button("登入"):
            if check_login(user_input, pwd_input):
                st.session_state['logged_in_user'] = user_input
                st.rerun()
            else:
                st.error("帳號或密碼錯誤！")
    else:
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

# 情況 A: 未登入 -> 顯示廣告頁 (Landing Page)
if 'logged_in_user' not in st.session_state:
    st.title("🚀 權證主力戰情室")
    st.markdown("### 每日盤後，掌握大戶資金流向")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("📊 **獨家籌碼表格**\n\n一眼看穿誰在買、誰在賣，不再當韭菜。")
    with col2:
        st.warning("🤖 **AI 深度點評**\n\n結合基本面與籌碼面的精闢分析，省去你 3 小時做功課時間。")
    
    st.divider()
    st.write("🔒 **本站為會員制，請登入或訂閱後觀看。**")
    st.markdown("### 💰 訂閱方案：每月只要 NT$ 188")
    
    st.link_button("👉 立即註冊並訂閱", OPAY_URL)

# 情況 B: 已登入 -> 檢查權限
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
            st.write("手動幫會員加值 (模擬收到歐付寶通知)：")
            target_user = st.text_input("輸入會員帳號")
            if st.button("加值 30 天"):
                if add_days_to_user(target_user):
                    st.success(f"已成功幫 {target_user} 延長 30 天！")
                else:
                    st.error("找不到此帳號")
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
        st.warning("⛔ 您的訂閱已到期，無法查看完整內容。")
        st.write("請續費以解鎖最新主力籌碼分析報告。")
        st.link_button("👉 立即續約 (歐付寶 $188)", OPAY_URL)
        
        st.write("#### 🔒 最新文章列表 (VIP限定)")
        for post in st.session_state['db_posts']:
            st.info(f"🔒 {post['date']} | {post['title']}")
            
