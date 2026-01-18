import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests
import streamlit.components.v1 as components  # 🔥 新增這個元件庫

# ==========================================
# 1. 雲端資料庫設定 & 連線功能
# ==========================================

SHEET_NAME = '會員系統資料庫'
OPAY_URL = "https://payment.opay.tw/Broadcaster/Donate/B3C827A2B2E3ADEDDAFCAA4B1485C4ED"

@st.cache_resource
def get_db_connection():
    """連線到 Google Sheets"""
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # 從 Secrets 讀取
    if "gcp_key" in st.secrets:
        key_data = st.secrets["gcp_key"]
        if isinstance(key_data, str):
            key_dict = json.loads(key_data)
        else:
            key_dict = key_data
            
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME)
        return sheet
    else:
        st.error("找不到 GCP Key，請檢查 Secrets 設定！")
        return None

def upload_image_to_imgbb(image_file):
    if not image_file: return ""
    try:
        if "imgbb_key" in st.secrets:
            api_key = st.secrets["imgbb_key"]
        else:
            return ""
            
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": api_key}
        files = {"image": image_file.getvalue()}
        response = requests.post(url, data=payload, files=files)
        if response.status_code == 200:
            return response.json()['data']['url']
        else:
            return ""
    except:
        return ""

# ==========================================
# 2. 核心功能函數
# ==========================================

def get_data_as_df(worksheet_name):
    try:
        sh = get_db_connection()
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def check_login(username, password):
    if "admin_username" in st.secrets:
        admin_user = st.secrets["admin_username"]
        admin_pwd = st.secrets["admin_password"]
        if str(username) == str(admin_user) and str(password) == str(admin_pwd):
            return True
            
    df = get_data_as_df('users')
    if df.empty: return False
    user_row = df[df['username'].astype(str) == str(username)]
    if not user_row.empty:
        if str(user_row.iloc[0]['password']) == str(password):
            return True
    return False

def register_user(username, password):
    df = get_data_as_df('users')
    if not df.empty and str(username) in df['username'].astype(str).values:
        return False, "帳號已存在"
    try:
        sh = get_db_connection()
        ws = sh.worksheet('users')
        tw_now = datetime.now() + timedelta(hours=8)
        yesterday = (tw_now - timedelta(days=1)).strftime("%Y-%m-%d")
        ws.append_row([str(username), str(password), yesterday])
        return True, "註冊成功！請切換到「登入」分頁進入。"
    except Exception as e:
        return False, f"連線錯誤: {e}"

def check_subscription(username):
    if "admin_username" in st.secrets:
        if str(username) == str(st.secrets["admin_username"]): 
            return True, "永久會員 (管理員)"
    
    df = get_data_as_df('users')
    if df.empty: return False, "資料庫讀取失敗"
    user_row = df[df['username'].astype(str) == str(username)]
    if not user_row.empty:
        expiry_str = str(user_row.iloc[0]['expiry'])
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            tw_today = (datetime.now() + timedelta(hours=8)).date()
            if expiry_date >= tw_today: return True, expiry_str
            else: return False, expiry_str
        except: return False, "日期格式異常"
    return False, "無此帳號"

def add_days_to_user(username, days=30):
    try:
        sh = get_db_connection()
        ws = sh.worksheet('users')
        cell = ws.find(str(username))
        if not cell: return False
        row_num = cell.row
        current_expiry_str = ws.cell(row_num, 3).value
        tw_today = (datetime.now() + timedelta(hours=8)).date()
        try: current_expiry = datetime.strptime(current_expiry_str, "%Y-%m-%d").date()
        except: current_expiry = tw_today
        start_date = max(current_expiry, tw_today)
        new_expiry = start_date + timedelta(days=days)
        ws.update_cell(row_num, 3, new_expiry.strftime("%Y-%m-%d"))
        return True
    except: return False

def add_new_post(title, content, img_url=""):
    try:
        sh = get_db_connection()
        ws = sh.worksheet('posts')
        tw_time = datetime.now() + timedelta(hours=8)
        ws.append_row([tw_time.strftime("%Y-%m-%d %H:%M"), title, content, img_url])
        return True
    except: return False

# ==========================================
# 3. 網站介面
# ==========================================
st.set_page_config(page_title="權證主力戰情室", layout="wide", page_icon="📈")

st.markdown("""
    <style>
        [data-testid="stToolbar"] {visibility: hidden; display: none;}
        [data-testid="stDecoration"] {visibility: hidden; display: none;}
        footer {visibility: hidden; display: none;}
    </style>
""", unsafe_allow_html=True)

# --- 尚未登入區 ---
if 'logged_in_user' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🚀 權證主力戰情室</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>每日盤後籌碼分析 | 掌握大戶資金流向</p>", unsafe_allow_html=True)
    
    st.error("⚠️ **法律免責聲明**：本網站數據僅供學術研究參考，**絕不構成任何投資建議**。使用者應自行承擔所有投資風險，盈虧自負。")
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("🔒 請先登入或註冊以繼續")
        tab_login, tab_register = st.tabs(["🔑 會員登入", "📝 免費註冊"])
        with tab_login:
            st.write("")
            user_input = st.text_input("帳號", key="login_user")
            pwd_input = st.text_input("密碼", type="password", key="login_pwd")
            if st.button("登入系統", key="btn_login", use_container_width=True):
                if check_login(user_input, pwd_input):
                    st.session_state['logged_in_user'] = user_input
                    st.rerun()
                else:
                    st.error("帳號或密碼錯誤！")
        with tab_register:
            st.write("")
            new_user = st.text_input("設定帳號", key="reg_user")
            new_pwd = st.text_input("設定密碼", type="password", key="reg_pwd")
            new_pwd_confirm = st.text_input("確認密碼", type="password", key="reg_pwd2")
            if st.button("提交註冊", key="btn_reg", use_container_width=True):
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
    st.write("")
    c1, c2 = st.columns(2)
    with c1: st.success("📊 **獨家籌碼表格**\n\n一眼看穿誰在買、誰在賣。")
    with c2: st.warning("🤖 **AI 深度點評**\n\n結合基本面與籌碼面的精闢分析。")

# --- 已登入區 ---
else:
    user = st.session_state['logged_in_user']
    is_vip, expiry = check_subscription(user)
    
    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.title("🚀 權證主力戰情室")
        st.write(f"👋 歡迎回來，**{user}**")
        if is_vip: st.caption(f"✅ 會員效期至：{expiry}")
        else: st.caption(f"⛔ 會員已過期 ({expiry})")
    with top_col2:
        st.write("")
        if st.button("登出系統", use_container_width=True):
            del st.session_state['logged_in_user']
            st.rerun()
            
    st.warning("⚠️ **免責聲明**：本網站內容僅為資訊整理，**不構成投資建議**。盈虧自負。")
    st.divider()

    # --- 管理員後台 ---
    is_admin = False
    if "admin_username" in st.secrets:
        if str(user) == str(st.secrets["admin_username"]): is_admin = True
        
    if is_admin:
        with st.expander("🔧 管理員後台 (點擊展開)", expanded=True):
            tab1, tab2 = st.tabs(["發布文章", "會員管理"])
            with tab1:
                with st.form("post_form"):
                    st.write("### 發布新戰情")
                    st.info("💡 提示：如果使用 Mark 63 生成的 HTML，直接將 HTML 原始碼貼在「內容」框中即可。")
                    new_title = st.text_input("文章標題")
                    # 🔥 修改：增加高度，方便貼上大量 HTML 代碼
                    new_content = st.text_area("內容 (支援 HTML 代碼或純文字)", height=300)
                    uploaded_files = st.file_uploader("上傳圖片 (選填)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
                    submitted = st.form_submit_button("發布文章")
                    if submitted:
                        final_img_str = ""
                        if uploaded_files:
                            img_urls = []
                            files_to_process = uploaded_files[:10]
                            bar = st.progress(0, text="上傳中...")
                            for i, f in enumerate(files_to_process):
                                url = upload_image_to_imgbb(f)
                                if url: img_urls.append(url)
                                bar.progress(int((i+1)/len(files_to_process)*100))
                            final_img_str = ",".join(img_urls)
                            bar.empty()
                        if add_new_post(new_title, new_content, final_img_str):
                            st.success(f"發布成功！")
            
            with tab2:
                target_user = st.text_input("輸入會員帳號")
                st.write("👇 加值天數：")
                b0, b1, b2, b3 = st.columns(4)
                with b0:
                    if st.button("+1 天", use_container_width=True):
                        if add_days_to_user(target_user, 1):
                            st.success("成功 +1 天")
                        else:
                            st.error("失敗")
                with b1:
                    if st.button("+30 天", use_container_width=True):
                        if add_days_to_user(target_user, 30):
                            st.success("成功 +30 天")
                        else:
                            st.error("失敗")
                with b2:
                    if st.button("+60 天", use_container_width=True):
                        if add_days_to_user(target_user, 60):
                            st.success("成功 +60 天")
                        else:
                            st.error("失敗")
                with b3:
                    if st.button("+90 天", use_container_width=True):
                        if add_days_to_user(target_user, 90):
                            st.success("成功 +90 天")
                        else:
                            st.error("失敗")
                st.dataframe(get_data_as_df('users'))
        st.divider()

    # --- VIP 內容區 (🔥 重點修改區) ---
    if is_vip:
        st.subheader("📊 主力戰情日報")
        df_posts = get_data_as_df('posts')
        if not df_posts.empty:
            for index, row in df_posts.iloc[::-1].iterrows():
                with st.container():
                    st.markdown(f"### {row['title']}")
                    st.caption(f"{row['date']}")
                    
                    # 圖片顯示 (選填)
                    if row['img']:
                        if "," in str(row['img']): st.image(row['img'].split(","))
                        else: st.image(row['img'])
                    
                    content = row['content']
                    
                    # 🔥 智慧判斷：如果是 HTML 程式碼 (包含 <div 或 <html)，就用 iframe 渲染
                    if "<div" in content or "<html" in content or "<style>" in content:
                        # height 設定高一點，並開啟捲軸，讓完整的卡片可以滑動閱讀
                        components.html(content, height=600, scrolling=True)
                    else:
                        # 否則當作一般文字顯示
                        st.write(content)
                        
                    st.divider()
        else: st.info("尚無文章")
    else:
        st.error("⛔ 您的會員權限尚未開通或已到期。")
        st.link_button("👉 前往歐付寶付款 ($188/月)", OPAY_URL, use_container_width=True)
        st.write("#### 🔒 最新文章預覽")
        df_posts = get_data_as_df('posts')
        if not df_posts.empty:
            for index, row in df_posts.iloc[::-1].iterrows():
                st.info(f"🔒 {row['date']} | {row['title']}")
