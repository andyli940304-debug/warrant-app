import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# 1. 雲端資料庫設定 & 連線功能
# ==========================================

# 你的金鑰檔案路徑 (請確保檔案真的在這個位置)
JSON_PATH =KEY.json"
# 你的試算表名稱
SHEET_NAME = '會員系統資料庫'
# 你的歐付寶收款連結
OPAY_URL = "https://payment.opay.tw/Broadcaster/Donate/B3C827A2B2E3ADEDDAFCAA4B1485C4ED"

@st.cache_resource
def get_db_connection():
    """連線到 Google Sheets (使用快取，避免每次操作都重新連線)"""
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_PATH, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)
    return sheet

# ==========================================
# 2. 核心功能函數 (讀寫雲端版)
# ==========================================

def get_data_as_df(worksheet_name):
    """讀取某個分頁的所有資料轉成 DataFrame"""
    try:
        sh = get_db_connection()
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

def check_login(username, password):
    """檢查登入"""
    # 🔥 超級管理員通道 (寫死在程式碼最安全)
    if username == 'BOSS07260304' and password == '04036270BOSS':
        return True
    
    # 一般會員：去雲端查
    df = get_data_as_df('users')
    if df.empty: return False
    
    # 搜尋帳號 (強制轉字串比對)
    user_row = df[df['username'].astype(str) == str(username)]
    
    if not user_row.empty:
        stored_pwd = str(user_row.iloc[0]['password'])
        if stored_pwd == str(password):
            return True
    return False

def register_user(username, password):
    """註冊新用戶"""
    df = get_data_as_df('users')
    
    # 檢查是否重複
    if not df.empty and str(username) in df['username'].astype(str).values:
        return False, "帳號已存在"
    
    try:
        sh = get_db_connection()
        ws = sh.worksheet('users')
        # 預設過期日 (昨天)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        # 寫入 [帳號, 密碼, 到期日]
        ws.append_row([str(username), str(password), yesterday])
        return True, "註冊成功！資料已寫入雲端，請登入並付款開通。"
    except Exception as e:
        return False, f"連線錯誤: {e}"

def check_subscription(username):
    """檢查會員效期"""
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
    """幫會員充值 (直接修改儲存格)"""
    try:
        sh = get_db_connection()
        ws = sh.worksheet('users')
        
        # 尋找該帳號在哪一列
        cell = ws.find(str(username))
        if not cell: return False
        
        row_num = cell.row
        # 取得目前到期日 (第3欄)
        current_expiry_str = ws.cell(row_num, 3).value
        
        try:
            current_expiry = datetime.strptime(current_expiry_str, "%Y-%m-%d").date()
        except:
            current_expiry = datetime.now().date()
            
        # 計算新日期
        start_date = max(current_expiry, datetime.now().date())
        new_expiry = start_date + timedelta(days=days)
        new_expiry_str = new_expiry.strftime("%Y-%m-%d")
        
        # 更新儲存格
        ws.update_cell(row_num, 3, new_expiry_str)
        return True
    except Exception as e:
        st.error(f"充值失敗: {e}")
        return False

def add_new_post(title, content, img_url=""):
    """新增文章到雲端"""
    try:
        sh = get_db_connection()
        ws = sh.worksheet('posts')
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        # 寫入 [日期, 標題, 內容, 圖片] (新文章在最下面，顯示時我們再反轉)
        ws.append_row([date_str, title, content, img_url])
        return True
    except Exception as e:
        st.error(f"發文失敗: {e}")
        return False

# ==========================================
# 3. 網站介面 (UI)
# ==========================================
st.set_page_config(page_title="權證主力戰情室", layout="wide", page_icon="📈")

# 隱藏選單樣式
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 側邊欄：登入/註冊系統 ---
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

# --- 主畫面內容 ---

if 'logged_in_user' not in st.session_state:
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

    # --- 管理員後台 (只有 BOSS 能看) ---
    if user == 'BOSS07260304':
        st.subheader("🔧 管理員後台")
        
        tab1, tab2 = st.tabs(["發布文章", "會員管理"])
        
        with tab1:
            st.write("在此發布每日戰情報告：")
            with st.form("post_form"):
                new_title = st.text_input("文章標題")
                new_content = st.text_area("文章內容 (支援 Markdown)", height=200)
                # 暫時不支援真實圖片上傳到 Drive，這裡先用文字連結代替，或留空
                new_img = st.text_input("圖片連結 (選填)") 
                submitted = st.form_submit_button("發布文章")
                
                if submitted:
                    if add_new_post(new_title, new_content, new_img):
                        st.success("文章已發布到雲端！")
                    else:
                        st.error("發布失敗，請檢查網路或權限。")
        
        with tab2:
            st.info("收到歐付寶通知後，請在此輸入對方註冊的帳號進行開通。")
            col_a, col_b = st.columns([3, 1])
            with col_a:
                target_user = st.text_input("輸入會員帳號")
            with col_b:
                st.write("")
                st.write("")
                if st.button("加值 30 天"):
                    if add_days_to_user(target_user):
                        st.success(f"已成功幫 {target_user} 延長 30 天！")
                    else:
                        st.error("找不到此帳號，請確認對方是否已註冊。")
            
            st.write("📋 雲端會員資料庫預覽：")
            st.dataframe(get_data_as_df('users'))

        st.divider()

    # --- VIP 內容區 (讀取雲端文章) ---
    if is_vip:
        st.title("📊 主力戰情日報")
        
        # 從雲端讀取文章
        df_posts = get_data_as_df('posts')
        
        if not df_posts.empty:
            # 將資料反轉，讓最新的文章在最上面
            for index, row in df_posts.iloc[::-1].iterrows():
                with st.container():
                    st.markdown(f"### {row['title']}")
                    st.caption(f"發布時間: {row['date']}")
                    
                    if row['img']:
                        st.image(row['img'])
                    
                    st.write(row['content'])
                    st.divider()
        else:
            st.info("目前還沒有發布任何文章。")
    
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
        
        st.write("#### 🔒 最新文章標題 (VIP限定)")
        df_posts = get_data_as_df('posts')
        if not df_posts.empty:
            for index, row in df_posts.iloc[::-1].iterrows():
                st.info(f"🔒 {row['date']} | {row['title']}")

