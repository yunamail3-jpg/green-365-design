import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import textwrap
import io
import json
import os

# --- 1. 設定頁面 (標題已更新) ---
st.set_page_config(page_title="綠善365 設計工具", layout="wide", page_icon="🌿")

# --- 2. CSS 美學注入 (V24 高對比無框風格) ---
st.markdown("""
<style>
    /* 全局字體顏色：白色 */
    html, body, [class*="css"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #ffffff !important; 
    }
    
    header {visibility: hidden;}
    .block-container {
        padding-top: 1rem;
        padding-bottom: 3rem;
    }

    /* 左側控制區背景 */
    .control-panel {
        background-color: #262730; 
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #444;
    }

    /* 輸入框去框化 (只有底線) */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 2px solid #666 !important;
        border-radius: 0px;
        color: #ffffff !important;
        padding-left: 0px;
        caret-color: #ff4b4b;
    }
    
    /* 聚焦時底線變亮白 */
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
        border-bottom: 2px solid #ffffff !important;
        box-shadow: none;
    }

    /* 標籤文字 */
    .stTextInput label, .stTextArea label, .stNumberInput label, .stSlider label {
        font-size: 14px;
        color: #cccccc !important;
        font-weight: bold;
    }

    /* 分頁標籤 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background-color: transparent;
        border-bottom: 1px solid #444;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        padding: 0;
        background-color: transparent !important;
        border: none !important;
        font-size: 16px;
        color: #888 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        font-weight: bold;
        border-bottom: 3px solid #ff4b4b !important;
    }

    /* 按鈕 */
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
        border: 1px solid #555;
        background-color: #333;
        color: white !important;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        border-color: #777;
        background-color: #444;
        color: white !important;
    }

    /* 下載按鈕 */
    div[data-testid="stDownloadButton"] > button {
        background-color: #ff4b4b;
        color: white !important;
        border-radius: 8px;
        width: 100%;
        padding: 12px !important;
        font-weight: bold;
        border: none;
    }
    
    .element-container img { margin-top: 0px; }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. 核心邏輯區 ---
TEMPLATE_FILE = "my_templates.json"

def load_all_templates():
    if os.path.exists(TEMPLATE_FILE):
        try:
            with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
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
        for k, v in data.items():
            st.session_state[k] = v
        st.toast(f"✅ 已載入：{selected_name}")

def draw_text_justified(draw, text, x, y, max_width, font, fill):
    if len(text) <= 1:
        draw.text((x, y), text, font=font, fill=fill)
        return
    total_char_width = sum([draw.textlength(char, font=font) for char in text])
    extra_space = max_width - total_char_width
    if extra_space < 0:
         draw.text((x, y), text, font=font, fill=fill)
         return
    gap_per_char = extra_space / (len(text) - 1)
    current_x = x
    char_widths = [draw.textlength(char, font=font) for char in text]
    for i, char in enumerate(text):
        draw.text((current_x, y), char, font=font, fill=fill)
        current_x += char_widths[i] + gap_per_char

def draw_multiline_text(draw, text, x, start_y, max_width, font, fill, line_spacing_ratio=1.5):
    current_y = start_y
    paragraphs = text.split('\n')
    char_width_approx = font.size + 2
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

def create_layout_logic(image_file, logo_file, day_text, 
                      subtitle_text, title_text, body_text, 
                      day_color, day_size, day_box_color, show_day_box, 
                      subtitle_color, subtitle_size,
                      title_color, body_color, title_size, body_size,
                      side_padding, bottom_padding,
                      crop_top, crop_bottom, img_offset_x, img_offset_y,
                      text_offset_y, day_box_offset_x, day_box_offset_y,
                      logo_size, logo_offset_x, logo_offset_y):
    
    CANVAS_WIDTH = 1080
    CONTENT_WIDTH = CANVAS_WIDTH - (side_padding * 2) 
    
    img = Image.open(image_file)
    ratio = CONTENT_WIDTH / img.width
    target_height = int(img.height * ratio)
    img_resized = img.resize((CONTENT_WIDTH, target_height), Image.Resampling.LANCZOS)
    
    final_img_h = target_height
    crop_img = img_resized
    if crop_top + crop_bottom < target_height:
        crop_box = (0, crop_top, CONTENT_WIDTH, target_height - crop_bottom)
        crop_img = img_resized.crop(crop_box)
        final_img_h = crop_img.height
    
    canvas = Image.new("RGB", (CANVAS_WIDTH, 3000), "white")
    draw = ImageDraw.Draw(canvas)
    
    header_height = 300
    paste_x = side_padding + img_offset_x
    paste_y = header_height + img_offset_y
    canvas.paste(crop_img, (paste_x, paste_y))
    current_max_y = max(0, paste_y + final_img_h)

    try:
        font_main = ImageFont.truetype("font.ttf", 20) 
        font_day = ImageFont.truetype("font.ttf", day_size)
        font_subtitle = ImageFont.truetype("font.ttf", subtitle_size)
        font_title = ImageFont.truetype("font.ttf", title_size)
        font_body = ImageFont.truetype("font.ttf", body_size)
    except:
        try:
            font_day = ImageFont.truetype("msjhbd.ttc", day_size)
            font_subtitle = ImageFont.truetype("msjhbd.ttc", subtitle_size)
            font_title = ImageFont.truetype("msjhbd.ttc", title_size)
            font_body = ImageFont.truetype("msjh.ttc", body_size)
        except:
            font_day = ImageFont.load_default()
            font_subtitle = ImageFont.load_default()
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()

    box_w = 220
    box_h = 100
    base_box_x = (CANVAS_WIDTH - side_padding) - box_w
    box_x = base_box_x + day_box_offset_x
    box_y = 120 + day_box_offset_y
    
    if show_day_box:
        draw.rectangle([(box_x, box_y), (box_x + box_w, box_y + box_h)], outline=day_box_color, width=3)
    
    text_bbox = draw.textbbox((0, 0), f"DAY {day_text}", font=font_day)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    
    txt_x = box_x + (box_w - text_w) / 2
    txt_y = box_y + (box_h - text_h) / 2 - (day_size * 0.1)
    draw.text((txt_x, txt_y), f"DAY {day_text}", font=font_day, fill=day_color)

    cursor_y = current_max_y + text_offset_y
    text_left_margin = side_padding

    if subtitle_text.strip():
        cursor_y = draw_multiline_text(draw, subtitle_text, text_left_margin, cursor_y, CONTENT_WIDTH, font_subtitle, subtitle_color)
        cursor_y += 20

    if title_text.strip():
        cursor_y = draw_multiline_text(draw, title_text, text_left_margin, cursor_y, CONTENT_WIDTH, font_title, title_color)
        cursor_y += 20

    chars_per_line = int(CONTENT_WIDTH / (body_size + 2)) 
    body_paragraphs = body_text.split('\n')
    for p in body_paragraphs:
        if p.strip() == "":
            cursor_y += int(body_size * 1.6)
            continue
        lines = textwrap.wrap(p, width=chars_per_line)
        for i, line in enumerate(lines):
            is_last_line = (i == len(lines) - 1)
            if is_last_line:
                draw.text((text_left_margin, cursor_y), line, font=font_body, fill=body_color)
            else:
                draw_text_justified(draw, line, text_left_margin, cursor_y, CONTENT_WIDTH, font_body, body_color)
            cursor_y += int(body_size * 1.6)
    
    current_max_y = cursor_y

    if logo_file is not None:
        logo = Image.open(logo_file).convert("RGBA")
        l_ratio = logo_size / logo.width
        l_height = int(logo.height * l_ratio)
        logo = logo.resize((logo_size, l_height), Image.Resampling.LANCZOS)
        logo_x = CANVAS_WIDTH - side_padding - logo_size + logo_offset_x
        logo_y = current_max_y + 50 + logo_offset_y 
        canvas.paste(logo, (logo_x, logo_y), mask=logo)
        current_max_y = max(current_max_y, logo_y + l_height)

    final_height = current_max_y + bottom_padding
    final_image = canvas.crop((0, 0, CANVAS_WIDTH, final_height))
    return final_image

# --- 4. 初始化 Session State ---
default_values = {
    "day_input": "339",
    "show_day_box": True,
    "subtitle_input": "#愛的留言板 WEEK 17\n這是第二行副標",
    "title_input": "愛是信任 Love is Trust",
    "body_input": "在愛裏的我們，應該是自由且完整的。我們常因為害怕失去或缺乏理解與接納的心，而想要控制及干涉身邊的人。",
    "day_color": "#000000", "day_box_color": "#000000", "day_size": 60,
    "subtitle_color": "#8B4513", "subtitle_size": 36,
    "title_color": "#DA70D6", "title_size": 40,
    "body_color": "#333333", "body_size": 26,
    "side_padding": 200, "bottom_padding": 100,
    "text_offset_y": 60,
    "crop_top": 0, "crop_bottom": 0, "img_offset_y": 0,
    "logo_size": 150, "logo_offset_x": 0, "logo_offset_y": 0
}
for key, val in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 5. UI 介面佈局 ---
st.title("綠善365 圖文設計")

left_col, right_col = st.columns([35, 65], gap="large")

# === 左側：控制中心 ===
with left_col:
    st.markdown('<div class="control-panel">', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["內容", "外觀", "排版", "模版"])

    with tab1:
        st.caption("素材")
        uploaded_file = st.file_uploader("📸 主照片", type=['jpg', 'png'])
        uploaded_logo = st.file_uploader("🏷️ Logo", type=['png'])
        st.markdown("---")
        st.caption("文字內容")
        c1, c2 = st.columns([1, 2])
        c1.text_input("DAY", key="day_input")
        c2.text_area("副標題", height=68, key="subtitle_input")
        st.text_area("主標題", height=70, key="title_input")
        st.text_area("內文", height=150, key="body_input")

    with tab2:
        st.caption("樣式設定")
        with st.expander("DAY 設定", expanded=True):
            st.checkbox("顯示 DAY 外框", key="show_day_box")
            c1, c2 = st.columns(2)
            c1.color_picker("DAY色", key="day_color")
            c2.color_picker("框色", key="day_box_color")
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
        st.markdown("**裁切**")
        c1, c2 = st.columns(2)
        c1.number_input("上裁", 0, 1000, key="crop_top")
        c2.number_input("下裁", 0, 1000, key="crop_bottom")
        st.markdown("**位置**")
        st.slider("左右寬", 0, 400, key="side_padding")
        st.slider("底留白", 20, 500, key="bottom_padding")
        st.slider("圖位移", -200, 200, key="img_offset_y")
        st.slider("字位移", 0, 200, key="text_offset_y")
        with st.expander("Logo"):
            st.slider("大小", 50, 300, key="logo_size")
            c3, c4 = st.columns(2)
            c3.number_input("X軸", -300, 300, key="logo_offset_x")
            c4.number_input("Y軸", -200, 200, key="logo_offset_y")

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
                settings = {k: st.session_state[k] for k in default_values.keys()}
                save_new_template(new_name, settings)
                st.success("OK")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# === 右側：預覽中心 ===
with right_col:
    if uploaded_file:
        preview_width = st.slider("🔍 預覽大小", 200, 800, 450, label_visibility="collapsed")
        
        result = create_layout_logic(
            uploaded_file, uploaded_logo, 
            st.session_state.day_input, 
            st.session_state.subtitle_input, 
            st.session_state.title_input, 
            st.session_state.body_input,
            st.session_state.day_color, st.session_state.day_size, st.session_state.day_box_color,
            st.session_state.show_day_box, 
            st.session_state.subtitle_color, st.session_state.subtitle_size,
            st.session_state.title_color, st.session_state.body_color, 
            st.session_state.title_size, st.session_state.body_size,
            st.session_state.side_padding, st.session_state.bottom_padding,
            st.session_state.crop_top, st.session_state.crop_bottom, 0, st.session_state.img_offset_y,
            st.session_state.text_offset_y, 0, 0,
            st.session_state.logo_size, st.session_state.logo_offset_x, st.session_state.logo_offset_y
        )
        
        st.image(result, width=preview_width)
        
        buf = io.BytesIO()
        result.save(buf, format="JPEG", quality=95)
        st.download_button("⬇️ 下載圖片 (Download)", buf.getvalue(), "final_v25.jpg", "image/jpeg")
            
    else:
        st.info("👈 請先從左側上傳照片")