import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import textwrap
import io
import json
import os
import requests
import numpy as np

# --- 1. 設定頁面 ---
st.set_page_config(page_title="V30 終極修復版", layout="wide", page_icon="✨")

# --- 2. CSS 美學 (強力去框 + 隱藏提示) ---
st.markdown("""
<style>
    /* 全局字體 */
    html, body, [class*="css"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #ffffff !important; 
    }
    header {visibility: hidden;}
    .block-container {
        padding-top: 1rem; padding-bottom: 3rem;
    }
    .control-panel {
        background-color: #262730; padding: 25px; border-radius: 12px; border: 1px solid #444;
    }

    /* --- [關鍵] 強制移除 Streamlit 預設外框與提示 --- */
    div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="textarea"] {
        background-color: transparent !important; border: none !important; border-radius: 0px !important; box-shadow: none !important;
    }
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        background-color: transparent !important; border: none !important;
        border-bottom: 2px solid #666 !important; border-radius: 0px;
        color: #ffffff !important; padding: 5px 0px; caret-color: #ff4b4b;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
        border-bottom: 2px solid #ffffff !important; box-shadow: none !important;
    }
    /* 隱藏 Press Ctrl+Enter */
    div[data-testid="InputInstructions"] { display: none !important; }
    
    .stTextInput label, .stTextArea label, .stNumberInput label, .stSlider label, .stSelectbox label {
        font-size: 14px; color: #cccccc !important; font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px; background-color: transparent; border-bottom: 1px solid #444; margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px; padding: 0; background-color: transparent !important; border: none !important;
        font-size: 16px; color: #888 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important; font-weight: bold; border-bottom: 3px solid #ff4b4b !important;
    }
    .stButton>button {
        border-radius: 20px; font-weight: bold; border: 1px solid #555;
        background-color: #333; color: white !important; transition: all 0.2s;
    }
    .stButton>button:hover {
        border-color: #777; background-color: #444; color: white !important;
    }
    div[data-testid="stDownloadButton"] > button {
        background-color: #ff4b4b; color: white !important; border-radius: 8px;
        width: 100%; padding: 12px !important; font-weight: bold; border: none;
    }
    .element-container img { margin-top: 0px; }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. 核心邏輯區 ---
TEMPLATE_FILE = "my_templates.json"
FONT_URL = "https://github.com/justfont/open-huninn-font/releases/download/v2.0/jf-openhuninn-2.0.ttf"
DEFAULT_FONT_FILE = "font.ttf"

def load_all_templates():
    if os.path.exists(TEMPLATE_FILE):
        try:
            with open(TEMPLATE_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_new_template(name, data):
    templates = load_all_templates()
    templates[name] = data
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=4)

def handle_load_click():
    selected_name = st.session_state.get("template_selector_key")
    all_temps = load_all_templates()
    if selected_name and selected_name in all_temps:
        data = all_temps[selected_name]
        for k, v in data.items(): st.session_state[k] = v
        st.toast(f"✅ 已載入：{selected_name}")

def download_font_if_missing():
    if not os.path.exists(DEFAULT_FONT_FILE):
        try:
            response = requests.get(FONT_URL, timeout=5)
            if response.status_code == 200:
                with open(DEFAULT_FONT_FILE, "wb") as f:
                    f.write(response.content)
                return True
        except: pass
    return os.path.exists(DEFAULT_FONT_FILE)

# [修復] 字體載入邏輯
def load_fonts(uploaded_font_file, day_size, subtitle_size, title_size, body_size):
    font_path = None
    if uploaded_font_file: font_path = uploaded_font_file
    elif os.path.exists(DEFAULT_FONT_FILE): font_path = DEFAULT_FONT_FILE
    elif download_font_if_missing(): font_path = DEFAULT_FONT_FILE

    if font_path:
        try:
            f_day = ImageFont.truetype(font_path, day_size)
            f_sub = ImageFont.truetype(font_path, subtitle_size)
            f_title = ImageFont.truetype(font_path, title_size)
            f_body = ImageFont.truetype(font_path, body_size)
            return f_day, f_sub, f_title, f_body, True
        except: pass

    try:
        sys_font = "msjhbd.ttc" 
        f_day = ImageFont.truetype(sys_font, day_size)
        f_sub = ImageFont.truetype(sys_font, subtitle_size)
        f_title = ImageFont.truetype(sys_font, title_size)
        f_body = ImageFont.truetype(sys_font, body_size)
        return f_day, f_sub, f_title, f_body, True
    except:
        d = ImageFont.load_default()
        return d, d, d, d, False

def draw_multiline_text(draw, text, x, start_y, max_width, font, fill, line_spacing_ratio=1.5):
    current_y = start_y
    paragraphs = text.split('\n')
    char_width_approx = font.getbbox("A")[2]
    if char_width_approx == 0: char_width_approx = font.size * 0.5
    chars_per_line = max(1, int(max_width / char_width_approx))
    for p in paragraphs:
        if p.strip() == "":
            current_y += int(font.size * line_spacing_ratio)
            continue
        lines = textwrap.wrap(p, width=chars_per_line)
        for line in lines:
            draw.text((x, current_y), line, font=font, fill=fill)
            current_y += int(font.size * line_spacing_ratio)
    return current_y

def find_coeffs(pa, pb):
    matrix = []
    for p1, p2 in zip(pa, pb):
        matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
        matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])
    A = np.matrix(matrix, dtype=np.float32)
    B = np.array(pb).reshape(8)
    res = np.dot(np.linalg.inv(A.T * A) * A.T, B)
    return np.array(res).reshape(8)

# [修復] 確保接收 uploaded_font 參數
def create_layout_b(image_file, logo_file, uploaded_font, params):
    CANVAS_WIDTH = 1920 
    CANVAS_HEIGHT = 1080
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
    draw = ImageDraw.Draw(canvas)
    
    base_x = 150 + params['img_offset_x']
    base_y = 200 + params['img_offset_y']
    
    img = Image.open(image_file).convert("RGBA")
    
    zoom = params.get('img_zoom', 1.0) 
    min_side = min(img.width, img.height)
    crop_size = min_side / zoom
    
    center_x, center_y = img.width / 2, img.height / 2
    left = center_x - (crop_size / 2)
    top = center_y - (crop_size / 2)
    right = center_x + (crop_size / 2)
    bottom = center_y + (crop_size / 2)
    
    img_square = img.crop((left, top, right, bottom))
    
    SQUARE_SIZE = 700
    img_square = img_square.resize((SQUARE_SIZE, SQUARE_SIZE), Image.Resampling.LANCZOS)
    
    BORDER_SIZE = 30
    frame_size = SQUARE_SIZE + (BORDER_SIZE * 2)
    framed_img = Image.new("RGBA", (frame_size, frame_size), "white")
    framed_img.paste(img_square, (BORDER_SIZE, BORDER_SIZE))
    
    rotated_img = framed_img.rotate(params['rotation_angle'], resample=Image.Resampling.BICUBIC, expand=True)
    canvas.paste(rotated_img, (base_x, base_y), mask=rotated_img)

    font_day, font_subtitle, font_title, font_body, font_loaded = load_fonts(
        uploaded_font, params['day_size'], params['subtitle_size'], params['title_size'], params['body_size']
    )
    
    text_start_x = 900
    text_width = 900
    cursor_y = 200 + params['text_offset_y']

    draw.line([(text_start_x, cursor_y), (text_start_x + text_width, cursor_y)], fill="#ccc", width=2)
    cursor_y += 20
    
    day_text = f"♦ DAY {params['day_input']} TIPS ♦"
    text_bbox = draw.textbbox((0,0), day_text, font=font_day)
    day_text_w = text_bbox[2] - text_bbox[0]
    draw.text((text_start_x + text_width - day_text_w, cursor_y), day_text, font=font_day, fill=params['day_color'])
    cursor_y += (text_bbox[3] - text_bbox[1]) + 20

    draw.line([(text_start_x, cursor_y), (text_start_x + text_width, cursor_y)], fill="#ccc", width=2)
    cursor_y += 50

    if params['subtitle_input'].strip():
        cursor_y = draw_multiline_text(draw, params['subtitle_input'], text_start_x, cursor_y, text_width, font_subtitle, params['subtitle_color'])
        cursor_y += 30
    
    if params['title_input'].strip():
        cursor_y = draw_multiline_text(draw, params['title_input'], text_start_x, cursor_y, text_width, font_title, params['title_color'])
        cursor_y += 40

    if params['body_input'].strip():
        paragraphs = params['body_input'].split('\n')
        for p in paragraphs:
            if p.strip() == "": continue
            draw.text((text_start_x, cursor_y), "▪", font=font_body, fill=params['body_color'])
            draw_multiline_text(draw, p.strip(), text_start_x + 30, cursor_y, text_width - 30, font_body, params['body_color'])
            cursor_y += int(font_body.size * 2)

    if logo_file is not None:
        logo = Image.open(logo_file).convert("RGBA")
        l_ratio = params['logo_size'] / logo.width
        logo = logo.resize((params['logo_size'], int(logo.height * l_ratio)), Image.Resampling.LANCZOS)
        logo_x = CANVAS_WIDTH - params['side_padding'] - params['logo_size'] + params['logo_offset_x']
        logo_y = CANVAS_HEIGHT - params['bottom_padding'] - logo.height + params['logo_offset_y']
        canvas.paste(logo, (logo_x, logo_y), mask=logo)
    
    return canvas, font_loaded

# [修復] 確保接收 uploaded_font 參數
def create_layout_a(image_file, logo_file, uploaded_font, params):
    CANVAS_WIDTH = 1080
    side_padding = params['side_padding']
    CONTENT_WIDTH = CANVAS_WIDTH - (side_padding * 2) 
    
    img = Image.open(image_file)
    ratio = CONTENT_WIDTH / img.width
    target_height = int(img.height * ratio)
    img_resized = img.resize((CONTENT_WIDTH, target_height), Image.Resampling.LANCZOS)
    
    final_img_h = target_height
    crop_img = img_resized
    crop_t = params['crop_top']
    crop_b = params['crop_bottom']
    
    if crop_t + crop_b < target_height:
        crop_box = (0, crop_t, CONTENT_WIDTH, target_height - crop_b)
        crop_img = img_resized.crop(crop_box)
        final_img_h = crop_img.height
    
    canvas = Image.new("RGB", (CANVAS_WIDTH, 3000), "white")
    draw = ImageDraw.Draw(canvas)
    
    header_height = 300
    paste_x = side_padding + params['img_offset_x']
    paste_y = header_height + params['img_offset_y']
    canvas.paste(crop_img, (paste_x, paste_y))
    current_max_y = max(0, paste_y + final_img_h)

    font_day, font_subtitle, font_title, font_body, font_loaded = load_fonts(
        uploaded_font, params['day_size'], params['subtitle_size'], params['title_size'], params['body_size']
    )

    box_w, box_h = 220, 100
    box_x = (CANVAS_WIDTH - side_padding) - box_w + params['day_box_offset_x']
    box_y = 120 + params['day_box_offset_y']
    
    if params['show_day_box']:
        draw.rectangle([(box_x, box_y), (box_x + box_w, box_y + box_h)], outline=params['day_box_color'], width=3)
    
    text_bbox = draw.textbbox((0, 0), f"DAY {params['day_input']}", font=font_day)
    txt_x = box_x + (box_w - (text_bbox[2] - text_bbox[0])) / 2
    txt_y = box_y + (box_h - (text_bbox[3] - text_bbox[1])) / 2 - (font_day.size * 0.1)
    draw.text((txt_x, txt_y), f"DAY {params['day_input']}", font=font_day, fill=params['day_color'])

    cursor_y = current_max_y + params['text_offset_y']
    text_left_margin = side_padding

    if params['subtitle_input'].strip():
        cursor_y = draw_multiline_text(draw, params['subtitle_input'], text_left_margin, cursor_y, CONTENT_WIDTH, font_subtitle, params['subtitle_color'])
        cursor_y += 20
    if params['title_input'].strip():
        cursor_y = draw_multiline_text(draw, params['title_input'], text_left_margin, cursor_y, CONTENT_WIDTH, font_title, params['title_color'])
        cursor_y += 20
    if params['body_input'].strip():
        cursor_y = draw_multiline_text(draw, params['body_input'], text_left_margin, cursor_y, CONTENT_WIDTH, font_body, params['body_color'])
    
    current_max_y = cursor_y

    if logo_file is not None:
        logo = Image.open(logo_file).convert("RGBA")
        l_ratio = params['logo_size'] / logo.width
        logo = logo.resize((params['logo_size'], int(logo.height * l_ratio)), Image.Resampling.LANCZOS)
        logo_x = CANVAS_WIDTH - side_padding - params['logo_size'] + params['logo_offset_x']
        logo_y = current_max_y + 50 + params['logo_offset_y'] 
        canvas.paste(logo, (logo_x, logo_y), mask=logo)
        current_max_y = max(current_max_y, logo_y + logo.height)

    final_height = current_max_y + params['bottom_padding']
    final_image = canvas.crop((0, 0, CANVAS_WIDTH, final_height))
    return final_image, font_loaded

# --- 4. 初始化 Session State ---
default_values = {
    "layout_select": "版型 A (經典直式)",
    "day_input": "339",
    "show_day_box": True,
    "subtitle_input": "#愛的留言板 WEEK 17",
    "title_input": "信任讓愛穩固且持久",
    "body_input": "尊重界線 | 尊重每一個獨立個體的自由意識與選擇。\n放下控制 | 讓他做自己的樣子而不是成為我要的樣子。\n全然傾聽 | 不急著回應或評斷他人的說話、給建議。\n對未來保持開放 | 接受所有發生、享受每一過程。\n感恩練習 | 信任生命自有節奏，感謝所有支持的力量。",
    "day_color": "#888888", "day_box_color": "#000000", "day_size": 40,
    "subtitle_color": "#8B4513", "subtitle_size": 30,
    "title_color": "#DA70D6", "title_size": 48,
    "body_color": "#333333", "body_size": 28,
    "side_padding": 100, "bottom_padding": 100,
    "text_offset_y": 0,
    "crop_top": 0, "crop_bottom": 0, "img_offset_x": 0, "img_offset_y": 0,
    "day_box_offset_x": 0, "day_box_offset_y": 0,
    "logo_size": 150, "logo_offset_x": 0, "logo_offset_y": 0,
    "rotation_angle": 5,
    "img_zoom": 1.0
}
for key, val in default_values.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 5. UI 介面佈局 ---
st.title("綠善365 設計工具")

left_col, right_col = st.columns([35, 65], gap="large")

with left_col:
    st.markdown('<div class="control-panel">', unsafe_allow_html=True)
    
    st.selectbox("選擇版型", ["版型 A (經典直式)", "版型 B (傾斜橫式)"], key="layout_select")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["內容", "外觀", "排版", "模版"])

    with tab1:
        st.caption("素材")
        uploaded_file = st.file_uploader("📸 主照片", type=['jpg', 'png'])
        uploaded_logo = st.file_uploader("🏷️ Logo", type=['png'])
        
        st.markdown("---")
        # [修復] 這裡定義了 uploaded_font
        st.caption("字體 (解決亂碼用)")
        uploaded_font = st.file_uploader("🔤 上傳字體 (font.ttf)", type=['ttf', 'ttc'])

        st.markdown("---")
        st.caption("文字內容")
        c1, c2 = st.columns([1, 2])
        c1.text_input("DAY", key="day_input")
        c2.text_area("副標題", height=68, key="subtitle_input")
        st.text_area("主標題", height=70, key="title_input")
        st.text_area("內文 (版型B支援換行列表)", height=200, key="body_input")

    with tab2:
        st.caption("樣式設定")
        with st.expander("DAY 設定", expanded=True):
            if st.session_state.layout_select == "版型 A (經典直式)":
                st.checkbox("顯示 DAY 外框", key="show_day_box")
                c2.color_picker("框色", key="day_box_color")
            c1, c2 = st.columns(2)
            c1.color_picker("DAY色", key="day_color")
            st.slider("DAY 大小", 20, 100, key="day_size")
        
        with st.expander("文字配色", expanded=True):
            c1, c2 = st.columns(2)
            c1.color_picker("副標色", key="subtitle_color")
            c2.number_input("副標大小", 20, 100, key="subtitle_size")
            c3, c4 = st.columns(2)
            c3.color_picker("主標色", key="title_color")
            c4.number_input("主標大小", 20, 100, key="title_size")
            c5, c6 = st.columns(2)
            c5.color_picker("內文色", key="body_color")
            c6.number_input("內文大小", 15, 80, key="body_size")

    with tab3:
        st.caption("版面微調")
        
        if st.session_state.layout_select == "版型 B (傾斜橫式)":
            st.markdown("**主圖縮放 (Zoom)**")
            st.slider("縮放比例", 0.5, 3.0, 1.0, 0.1, key="img_zoom", help="1.0=原圖, >1放大, <1縮小")
            st.markdown("**傾斜設定**")
            st.slider("旋轉角度", -20, 20, key="rotation_angle")
        else:
            st.markdown("**裁切**")
            c1, c2 = st.columns(2)
            c1.number_input("上裁", 0, 1000, key="crop_top")
            c2.number_input("下裁", 0, 1000, key="crop_bottom")

        st.markdown("**位置**")
        c3, c4 = st.columns(2)
        c3.slider("圖X軸", -200, 200, key="img_offset_x")
        c4.slider("圖Y軸", -200, 200, key="img_offset_y")
        if st.session_state.layout_select == "版型 A (經典直式)":
             st.slider("左右寬", 0, 400, key="side_padding")
        else:
             st.slider("右側留白", 0, 400, key="side_padding") 

        st.slider("底留白", 20, 500, key="bottom_padding")
        st.slider("字位移", -200, 200, key="text_offset_y")

        with st.expander("Logo"):
            st.slider("大小", 50, 300, key="logo_size")
            c5, c6 = st.columns(2)
            c5.number_input("X軸", -300, 300, key="logo_offset_x")
            c6.number_input("Y軸", -200, 200, key="logo_offset_y")

    with tab4:
        st.caption("模版管理")
        all_templates = load_all_templates()
        if all_templates:
            selected = st.selectbox("選擇模版", list(all_templates.keys()), key="template_selector_key")
            st.button("📥 載入", on_click=handle_load_click, use_container_width=True)
        st.markdown("---")
        new_name = st.text_input("存檔名稱")
        if st.button("💾 儲存", use_container_width=True):
            if new_name:
                settings = {k: st.session_state[k] for k in default_values.keys() if k in st.session_state}
                save_new_template(new_name, settings)
                st.success("OK")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# === 右側：預覽中心 ===
with right_col:
    if uploaded_file:
        preview_width = st.slider("🔍 預覽大小", 200, 1000, 450, label_visibility="collapsed")
        
        params = {k: st.session_state[k] for k in default_values.keys() if k in st.session_state}
        
        if st.session_state.layout_select == "版型 A (經典直式)":
            # [修復] 這裡呼叫時傳入了 uploaded_font，且 create_layout_a 已在上方修復
            result, font_loaded = create_layout_a(uploaded_file, uploaded_logo, uploaded_font, params)
        else:
            result, font_loaded = create_layout_b(uploaded_file, uploaded_logo, uploaded_font, params)
        
        if not font_loaded:
            # 這裡不顯示錯誤，只默默使用預設字體，避免干擾畫面 (依使用者要求)
            pass

        st.image(result, width=preview_width)
        
        buf = io.BytesIO()
        result.save(buf, format="JPEG", quality=95)
        st.download_button("⬇️ 下載圖片", buf.getvalue(), "final_v30.jpg", "image/jpeg")
            
    else:
        st.info("👈 請先從左側上傳主照片以開始預覽")