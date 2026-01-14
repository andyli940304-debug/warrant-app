import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests

# ==========================================
# 1. 雲端資料庫設定 & 連線功能
# ==========================================

SHEET_NAME = '會員系統資料庫'
OPAY_URL = "https://payment.opay.tw/Broadcaster/Donate/B3C827A2B2E3ADEDDAFCAA4B1485C4ED"

# ImgBB API 金鑰
IMGBB_API_KEY = "fef8684953f08c5da5faff27ce582fdb"

@st.cache_resource
def get_db_connection():
    """連線到 Google Sheets"""
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # 從 Secrets 讀取 GCP 金鑰
    key_dict = json.loads(st.secrets["gcp_key"])
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)
    return sheet

def upload_image_to_imgbb(image_file):
    """
    上傳圖片到 ImgBB
    """
    if not image_file:
        return ""
    
    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": IMGBB_API_KEY,
        }
        files = {
            "image": image_file.getvalue()
        }
        
        response = requests.post(url, data=payload, files=files)
        
        if response.status_code == 200:
            result = response.json()
            return result['data']['url']
        else:
            st.error(f"❌ ImgBB 上傳失敗 (HTTP {response.status_code})")
            return ""
            
    except Exception as e:
        st.error(f"❌ 程式執行錯誤: {e}")
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
    except Exception as e:
        return pd.DataFrame()

def check_login(username, password):
    if username == 'BOSS07260304' and password == '04036270BOSS':
        return True
    df = get_data_as_df('users')
    if df.empty: return False
    user_row = df[df['username'].astype(str) == str(username)]
    if not user_row.empty:
        stored_pwd = str(user_row.iloc[0]['password'])
        if stored_pwd == str(password):
            return True
    return False

def register_user(username, password):
    df = get_data_as_df('users')
    if not df.empty and str(username) in df['username'].astype(str).values:
        return False, "帳號已存在"
    try:
        sh = get_db_connection()
        ws = sh.worksheet('users')
        
        # 🔥 修正時區：取得台灣時間 (UTC+8)
        tw_now = datetime.now() + timedelta(hours=8)
        yesterday = (tw_now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        ws.append_row([str(username), str(password), yesterday])
        return True, "註冊成功！請切換到「登入」分頁進入。"
    except Exception as e:
        return False, f"連線錯誤: {e}"

def check_subscription(username):
    if username == 'BOSS07260304': return True, "永久會員 (管理員)"
    df = get_data_as_df('users')
    if df.empty: return False, "資料庫讀取失敗"
    user_row = df[df['username'].astype(str) == str(username)]
    if not user_row.empty:
        expiry_str = str(user_row.iloc[0]['expiry'])
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            # 🔥 修正時區：比對時也要用台灣時間
            tw_today = (datetime.now() + timedelta(hours=8)).date()
            
            if expiry_date >= tw_today:
                return True, expiry_str
            else:
                return False, expiry_str
        except:
            return False, "日期格式異常"
    return False, "無此帳號"

def add_days_to_user(username, days=30):
    try:
        sh = get_db_connection()
        ws = sh.worksheet('users')
        cell = ws.find(str(username))
        if not cell: return False
        row_num = cell.row
        current_expiry_str = ws.cell(row_num, 3).value
        
        # 🔥 修正時區：取得台灣時間
        tw_today = (datetime.now() + timedelta(hours=8)).date()
        
        try:
            current_expiry = datetime.strptime(current_expiry_str, "%Y-%m-%d").date()
        except:
            current_expiry = tw_today
            
        start_date = max(current_expiry, tw_today)
        new_expiry = start_date + timedelta(days=days)
        new_expiry_str = new_expiry.strftime("%Y-%m-%d")
        ws.update_cell(row_num, 3, new_expiry_str)
        return True
    except Exception as e:
        st.error(f"充值失敗: {e}")
        return False

def add_new_post(title, content, img_url=""):
    try:
        sh = get_db_connection()
        ws = sh.worksheet('posts')
        
        # 🔥 修正時區：發文時間強制 +8 小時 (台灣時間)
        tw_time = datetime.now() + timedelta(hours=8)
        date_str = tw_time.strftime("%Y-%m-%d %H:%M")
        
        ws.append_row([date_str, title, content, img_url])
        return True
    except Exception as e:
        st.error(f"發文失敗: {e}")
        return False

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

if 'logged_in_user' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🚀 權證主力戰情室</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>每日盤後籌碼分析 | 掌握大戶資金流向</p>", unsafe_allow_html=True)
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
    st.write("")
    c1, c2 = st.columns(2)
    with c1: st.success("📊 **獨家籌碼表格**\n\n一眼看穿誰在買、誰在賣。")
    with c2: st.warning("🤖 **AI 深度點評**\n\n結合基本面與籌碼面的精闢分析。")

else:
    user = st.session_state['logged_in_user']
    is_vip, expiry = check_subscription(user)
    
    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.title("🚀 權證主力戰情室")
        st.write(f"👋 歡迎回來，**{user}**")
        if is_vip:
            st.caption(f"✅ 會員效期至：{expiry}")
        else:
            st.caption(f"⛔ 會員已過期 ({expiry})")
    with top_col2:
        st.write("")
        if st.button("登出系統", use_container_width=True):
            del st.session_state['logged_in_user']
            st.rerun()
            
    st.divider()

    # --- 管理員後台 ---
    if user == 'BOSS07260304':
        with st.expander("🔧 管理員後台 (點擊展開)", expanded=True):
            tab1, tab2 = st.tabs(["發布文章", "會員管理"])
            with tab1:
                with st.form("post_form"):
                    st.write("### 發布新戰情")
                    new_title = st.text_input("文章標題")
                    new_content = st.text_area("內容", height=200)
                    uploaded_files = st.file_uploader(
                        "上傳圖片 (支援多選，最多10張)", 
                        type=['png', 'jpg', 'jpeg'], 
                        accept_multiple_files=True
                    )
                    
                    submitted = st.form_submit_button("發布文章")
                    
                    if submitted:
                        final_img_str = ""
                        if uploaded_files:
                            img_urls = []
                            files_to_process = uploaded_files[:10]
                            progress_text = "正在上傳圖片中，請稍候..."
                            my_bar = st.progress(0, text=progress_text)
                            total_files = len(files_to_process)
                            
                            for i, img_file in enumerate(files_to_process):
                                url = upload_image_to_imgbb(img_file)
                                if url:
                                    img_urls.append(url)
                                percent_complete = int((i + 1) / total_files * 100)
                                my_bar.progress(percent_complete, text=f"正在上傳第 {i+1}/{total_files} 張...")
                            
                            final_img_str = ",".join(img_urls)
                            my_bar.empty()
                        
                        if add_new_post(new_title, new_content, final_img_str):
                            st.success(f"發布成功！共上傳 {len(uploaded_files)} 張圖片。")
            
            with tab2:
                target_user = st.text_input("輸入會員帳號")
                st.write("👇 選擇要加值的天數：")
                btn_col0, btn_col1, btn_col2, btn_col3 = st.columns(4)
                
                with btn_col0:
                    if st.button("💰 +1 天 (測試)", use_container_width=True):
                        if add_days_to_user(target_user, 1):
                            st.success(f"已幫 {target_user} 加值 1 天！")
                        else: st.error("找不到帳號")

                with btn_col1:
                    if st.button("💰 +30 天", use_container_width=True):
                        if add_days_to_user(target_user, 30):
                            st.success(f"已幫 {target_user} 加值 30 天！")
                        else: st.error("找不到帳號")
                
                with btn_col2:
                    if st.button("💰 +60 天", use_container_width=True):
                        if add_days_to_user(target_user, 60):
                            st.success(f"已幫 {target_user} 加值 60 天！")
                        else: st.error("找不到帳號")
                            
                with btn_col3:
                    if st.button("💰 +90 天", use_container_width=True):
                        if add_days_to_user(target_user, 90):
                            st.success(f"已幫 {target_user} 加值 90 天！")
                        else: st.error("找不到帳號")

                st.write("📋 會員列表：")
                st.dataframe(get_data_as_df('users'))
        st.divider()

    # --- VIP 內容區 ---
    if is_vip:
        st.subheader("📊 主力戰情日報")
        df_posts = get_data_as_df('posts')
        if not df_posts.empty:
            for index, row in df_posts.iloc[::-1].iterrows():
                with st.container():
                    st.markdown(f"### {row['title']}")
                    st.caption(f"{row['date']}")
                    
                    img_data = row['img']
                    if img_data:
                        if "," in str(img_data):
                            img_list = img_data.split(",")
                            st.image(img_list)
                        else:
                            st.image(img_data)
                    
                    st.write(row['content'])
                    st.divider()
        else:
            st.info("尚無文章")
    else:
        st.error("⛔ 您的會員權限尚未開通或已到期。")
        st.write("請付款後，等待管理員開通權限。")
        st.link_button("👉 前往歐付寶付款 ($188/月)", OPAY_URL, use_container_width=True)
        
        st.write("#### 🔒 最新文章預覽")
        df_posts = get_data_as_df('posts')
        if not df_posts.empty:
            for index, row in df_posts.iloc[::-1].iterrows():
                st.info(f"🔒 {row['date']} | {row['title']}")
