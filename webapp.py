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

@st.cache_resource
def get_db_connection():
    """連線到 Google Sheets"""
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    key_dict = json.loads(st.secrets["gcp_key"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)
    return sheet

def upload_image_to_drive(image_file):
    """
    自動將上傳的圖片轉存到 Google Drive 並回傳公開連結
    """
    if not image_file:
        return ""
    
    try:
        # 1. 取得權限 (每次上傳都重新取得最新 Token，避免過期)
        scope = ['https://www.googleapis.com/auth/drive']
        key_dict = json.loads(st.secrets["gcp_key"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        token = creds.get_access_token().access_token
        
        # 2. 上傳檔案 (POST 到 Google Drive API)
        headers = {"Authorization": f"Bearer {token}"}
        files = {
            'metadata': (None, json.dumps({'name': image_file.name}), 'application/json'),
            'file': (image_file.name, image_file, image_file.type)
        }
        response = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers=headers,
            files=files
        )
        file_id = response.json().get('id')
        
        if not file_id:
            return ""

        # 3. 設定權限為「公開讀取」(讓會員看得到)
        requests.post(
            f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
            headers=headers,
            json={"role": "reader", "type": "anyone"}
        )
        
        # 4. 回傳可以直接顯示的連結
        return f"https://drive.google.com/uc?export=view&id={file_id}"
        
    except Exception as e:
        st.error(f"圖片上傳失敗: {e}")
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
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
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
            if expiry_date >= datetime.now().date():
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
        try:
            current_expiry = datetime.strptime(current_expiry_str, "%Y-%m-%d").date()
        except:
            current_expiry = datetime.now().date()
        start_date = max(current_expiry, datetime.now().date())
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
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
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

    # --- 管理員後台 (修改區：改為圖片上傳) ---
    if user == 'BOSS07260304':
        with st.expander("🔧 管理員後台 (點擊展開)", expanded=True):
            tab1, tab2 = st.tabs(["發布文章", "會員管理"])
            with tab1:
                with st.form("post_form"):
                    st.write("### 發布新戰情")
                    new_title = st.text_input("文章標題")
                    new_content = st.text_area("內容", height=200)
                    
                    # 🔥 修改處：改成檔案上傳器
                    uploaded_file = st.file_uploader("上傳圖片 (支援手機拍照)", type=['png', 'jpg', 'jpeg'])
                    
                    submitted = st.form_submit_button("發布文章")
                    
                    if submitted:
                        # 如果有選圖片，就先上傳到 Drive 拿連結
                        final_img_url = ""
                        if uploaded_file:
                            with st.spinner('正在上傳圖片到雲端...'):
                                final_img_url = upload_image_to_drive(uploaded_file)
                        
                        if add_new_post(new_title, new_content, final_img_url):
                            st.success("發布成功！")
            
            with tab2:
                target_user = st.text_input("輸入會員帳號")
                if st.button("加值 30 天"):
                    if add_days_to_user(target_user):
                        st.success(f"已幫 {target_user} 加值！")
                    else:
                        st.error("找不到帳號")
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
                    
                    # 顯示圖片 (如果有)
                    if row['img']: 
                        st.image(row['img'])
                    
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
