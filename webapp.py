import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# 1. 雲端資料庫設定 & 連線功能 (使用 Secrets)
# ==========================================

SHEET_NAME = '會員系統資料庫'
OPAY_URL = "https://payment.opay.tw/Broadcaster/Donate/B3C827A2B2E3ADEDDAFCAA4B1485C4ED"

@st.cache_resource
def get_db_connection():
    """連線到 Google Sheets (使用 Streamlit Secrets，安全不外洩)"""
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # 從 Secrets 讀取金鑰
    key_dict = json.loads(st.secrets["gcp_key"])
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)
    return sheet

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
        return True, "註冊成功！資料已寫入雲端，請登入並付款開通。"
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
# 3. 網站介面 (UI)
# ==========================================
st.set_page_config(page_title="權證主力戰情室", layout="wide", page_icon="📈")

# 🔥 終極修復：直接把按鈕「釘」在螢幕左上角 (Fixed Position)
# 這樣不管 Header 怎麼變，按鈕都一定會在
st.markdown("""
    <style>
        /* 1. 隱藏右上角的選單 (Share, Star, GitHub 等) */
        [data-testid="stToolbar"] {
            visibility: hidden !important;
            display: none !important;
        }
        
        /* 2. 隱藏最上面的彩色列 */
        [data-testid="stDecoration"] {
            visibility: hidden !important;
            display: none !important;
        }
        
        /* 3. 隱藏頁尾 */
        footer {
            visibility: hidden !important;
            display: none !important;
        }
        
        /* 4. 讓 Header 透明，但保留空間給按鈕 */
        [data-testid="stHeader"] {
            background-color: transparent !important;
            z-index: 1 !important;
        }
        
        /* 5. 核彈級修復：強制把「展開側邊欄」按鈕釘在左上角 */
        [data-testid="stSidebarCollapsedControl"] {
            display: block !important;
            visibility: visible !important;
            position: fixed !important;  /* 脫離 Header，直接釘在視窗上 */
            top: 15px !important;
            left: 15px !important;
            z-index: 1000005 !important; /* 確保它在所有東西最上面 */
            
            /* 按鈕樣式優化 */
            background-color: rgba(255, 255, 255, 0.5); /* 半透明白色底 */
            border-radius: 8px;
            padding: 4px;
            color: #333333 !important; /* 箭頭顏色 */
            border: 1px solid rgba(0,0,0,0.1);
        }
        
        /* 針對手機版特別調整 */
        @media (max-width: 640px) {
            [data-testid="stSidebarCollapsedControl"] {
                top: 10px !important;
                left: 10px !important;
                background-color: rgba(255, 255, 255, 0.8); /* 手機版底色深一點比較明顯 */
            }
        }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔐 會員中心")
    if 'logged_in_user' not in st.session_state:
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

if 'logged_in_user' not in st.session_state:
    st.title("🚀 權證主力戰情室")
    st.markdown("### 每日盤後，掌握大戶資金流向")
    col1, col2 = st.columns(2)
    with col1: st.info("📊 **獨家籌碼表格**\n\n一眼看穿誰在買、誰在賣。")
    with col2: st.warning("🤖 **AI 深度點評**\n\n結合基本面與籌碼面的精闢分析。")
    st.divider()
    st.write("🔒 **請先在左側「註冊」或「登入」後觀看。**")
    st.link_button("👉 立即註冊並訂閱", OPAY_URL)
else:
    user = st.session_state['logged_in_user']
    is_vip, expiry = check_subscription(user)
    if user == 'BOSS07260304':
        st.subheader("🔧 管理員後台")
        tab1, tab2 = st.tabs(["發布文章", "會員管理"])
        with tab1:
            st.write("發布戰情報告：")
            with st.form("post_form"):
                new_title = st.text_input("文章標題")
                new_content = st.text_area("內容", height=200)
                new_img = st.text_input("圖片連結 (選填)")
                submitted = st.form_submit_button("發布")
                if submitted:
                    if add_new_post(new_title, new_content, new_img):
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
    if is_vip:
        st.title("📊 主力戰情日報")
        df_posts = get_data_as_df('posts')
        if not df_posts.empty:
            for index, row in df_posts.iloc[::-1].iterrows():
                with st.container():
                    st.markdown(f"### {row['title']}")
                    st.caption(f"{row['date']}")
                    if row['img']: st.image(row['img'])
                    st.write(row['content'])
                    st.divider()
        else:
            st.info("尚無文章")
    else:
        st.warning("⛔ 會員權限尚未開通")
        st.link_button("👉 前往付款", OPAY_URL)
