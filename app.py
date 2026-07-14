import streamlit as st
import cv2
import numpy as np
import re
import datetime
from PIL import Image
import pytesseract
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import urllib.request
import os

# اسم الخط العربي والمسار
FONT_NAME = "Amiri"
FONT_PATH = "Amiri-Regular.ttf"

# محاولة تحميل وتثبيت الخط العربي لضمان طباعة الـ PDF بنجاح وبدون مربعات
@st.cache_resource
def setup_fonts():
    if not os.path.exists(FONT_PATH):
        font_url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        try:
            # تحميل الخط من سيرفرات جوجل الرسمية
            urllib.request.urlretrieve(font_url, FONT_PATH)
        except Exception as e:
            st.error(f"خطأ في تحميل الخط العربي من الإنترنت: {e}")
            return False
            
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
        return True
    except Exception as e:
        st.error(f"خطأ في تسجيل الخط داخل نظام PDF: {e}")
        return False

# تشغيل إعداد الخطوط
font_available = setup_fonts()

# دالة ذكية لتجهيز النصوص العربية وعرضها من اليمين إلى اليسار
def format_arabic(text):
    if not font_available:
        return text # إرجاع النص العادي في حال عدم توفر الخط لمنع الانهيار
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception:
        return text

# تعريف النطاقات المرجعية الشاملة
VET_REFERENCE_RANGES = {
    "Dog / الكلاب": {
        "RBC": {"min": 5.5, "max": 8.5, "unit": "x10^6/µL"},
        "Hb": {"min": 12.0, "max": 18.0, "unit": "g/dL"},
        "PCV": {"min": 37.0, "max": 55.0, "unit": "%"},
        "MCV": {"min": 60.0, "max": 77.0, "unit": "fL"},
        "MCHC": {"min": 32.0, "max": 36.0, "unit": "g/dL"},
        "WBC": {"min": 6.0, "max": 17.0, "unit": "x10^3/µL"},
        "PLT": {"min": 200, "max": 500, "unit": "x10^3/µL"},
        "Neutrophils": {"min": 60.0, "max": 77.0, "unit": "%"},
        "Lymphocytes": {"min": 12.0, "max": 30.0, "unit": "%"},
        "Eosinophils": {"min": 2.0, "max": 10.0, "unit": "%"},
        "Basophils": {"min": 0.0, "max": 1.0, "unit": "%"},
        "Monocytes": {"min": 3.0, "max": 10.0, "unit": "%"}
    },
    "Cat / القطط": {
        "RBC": {"min": 6.0, "max": 10.0, "unit": "x10^6/µL"},
        "Hb": {"min": 8.0, "max": 15.0, "unit": "g/dL"},
        "PCV": {"min": 24.0, "max": 45.0, "unit": "%"},
        "MCV": {"min": 39.0, "max": 55.0, "unit": "fL"},
        "MCHC": {"min": 30.0, "max": 36.0, "unit": "g/dL"},
        "WBC": {"min": 5.5, "max": 19.5, "unit": "x10^3/µL"},
        "PLT": {"min": 300, "max": 800, "unit": "x10^3/µL"},
        "Neutrophils": {"min": 35.0, "max": 75.0, "unit": "%"},
        "Lymphocytes": {"min": 20.0, "max": 55.0, "unit": "%"},
        "Eosinophils": {"min": 2.0, "max": 12.0, "unit": "%"},
        "Basophils": {"min": 0.0, "max": 1.0, "unit": "%"},
        "Monocytes": {"min": 1.0, "max": 4.0, "unit": "%"}
    },
    "Cattle / الأبقار": {
        "RBC": {"min": 5.0, "max": 10.0, "unit": "x10^6/µL"},
        "Hb": {"min": 8.0, "max": 15.0, "unit": "g/dL"},
        "PCV": {"min": 24.0, "max": 46.0, "unit": "%"},
        "MCV": {"min": 40.0, "max": 60.0, "unit": "fL"},
        "MCHC": {"min": 30.0, "max": 36.0, "unit": "g/dL"},
        "WBC": {"min": 4.0, "max": 12.0, "unit": "x10^3/µL"},
        "PLT": {"min": 100, "max": 800, "unit": "x10^3/µL"},
        "Neutrophils": {"min": 15.0, "max": 45.0, "unit": "%"},
        "Lymphocytes": {"min": 45.0, "max": 75.0, "unit": "%"},
        "Eosinophils": {"min": 2.0, "max": 20.0, "unit": "%"},
        "Basophils": {"min": 0.0, "max": 2.0, "unit": "%"},
        "Monocytes": {"min": 2.0, "max": 12.0, "unit": "%"}
    }
}

# المسميات البديلة لضمان دقة القراءة التلقائية
PARAM_ALIASES = {
    "RBC": ["RBC", "Red Blood", "R.B.C", "Erythrocytes"],
    "Hb": ["Hb", "Hgb", "Hemoglobin", "HGB", "HGB "],
    "PCV": ["PCV", "Hct", "Hematocrit", "HCT", "PCV%"],
    "MCV": ["MCV", "M.C.V", "Mean Corpuscular Volume"],
    "MCHC": ["MCHC", "M.C.H.C"],
    "WBC": ["WBC", "White Blood", "W.B.C", "Leukocytes"],
    "PLT": ["PLT", "Platelet", "Platelets", "Thrombocytes"],
    "Neutrophils": ["Neutrophils", "NEUT", "Neut", "Neutrophil", "neut#"],
    "Lymphocytes": ["Lymphocytes", "LYMP", "Lym", "Lymph", "Lymphocyte", "lymph#"],
    "Eosinophils": ["Eosinophils", "EOS", "Eos", "Eosinophil", "eos#"],
    "Basophils": ["Basophils", "BAS", "Bas", "Basophil", "baso#"],
    "Monocytes": ["Monocytes", "MON", "Mon", "Monocyte", "mono#"]
}

st.set_page_config(
    page_title="عيادة الحي البيطرية - Al-Hay Vet Clinic", 
    page_icon="🐾",
    layout="wide"
)

st.title("🐾 عيادة الحي البيطرية - Al-Hay Veterinary Clinic")
st.subheader("Professional Automated CBC Interpretation System")

# إعداد حقول واجهة الاستخدام الجانبية
st.sidebar.header("📋 Case Information / بيانات الحالة")
owner_name = st.sidebar.text_input("Owner Name / اسم المربّي:", "Client")
animal_id = st.sidebar.text_input("Animal ID / رقم الحيوان:", "None")
species = st.sidebar.selectbox("Species / الفصيلة:", list(VET_REFERENCE_RANGES.keys()))

# تهيئة وإعادة تعيين القيم في Session State لضمان التفاعلية وعدم تكرار التفسير القديم
ranges = VET_REFERENCE_RANGES[species]
if "current_species" not in st.session_state or st.session_state.current_species != species:
    st.session_state.current_species = species
    for param in ranges.keys():
        st.session_state[f"val_{param}"] = 0.0

# دالة البحث عن القيم باستخدام ريجيكس مرن
def extract_param_value_robust(text_lines, param_name):
    aliases = PARAM_ALIASES.get(param_name, [param_name])
    for i, line in enumerate(text_lines):
        if any(re.search(r'\b' + re.escape(alias) + r'\b', line, re.IGNORECASE) for alias in aliases):
            for offset in range(0, 4):
                if i + offset < len(text_lines):
                    target_line = text_lines[i + offset]
                    matches = re.findall(r'\b\d+(?:\.\d+)?\b', target_line)
                    if matches:
                        for m in matches:
                            val = float(m)
                            if val > 0:
                                return val
    return None

# اختيار طريقة الإدخال
st.markdown("### 📥 Select Input Method / اختر طريقة الإدخال:")
tab_gallery, tab_camera = st.tabs([
    "📁 Upload from Gallery (رفع من الاستوديو)", 
    "📸 Use Live Camera (استخدام الكاميرا)"
])

uploaded_file = None
with tab_gallery:
    gallery_file = st.file_uploader("Choose an image / اختر صورة التقرير", type=["jpg", "jpeg", "png"], key="gallery_uploader")
    if gallery_file:
        uploaded_file = gallery_file

with tab_camera:
    camera_file = st.camera_input("Capture photo / التقط صورة للتقرير", key="camera_capturer")
    if camera_file:
        uploaded_file = camera_file

# معالجة قراءة النص OCR
if uploaded_file is not None:
    try:
        image = Image.open(uploaded_file)
        st.image(image, caption="صورة التحليل النشطة", width=350)
        
        with st.spinner("جاري قراءة بيانات التقرير بدقة..."):
            img_np = np.array(image)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            ocr_text = pytesseract.image_to_string(gray, config='--psm 6')
            ocr_lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
            
            for param in ranges.keys():
                val = extract_param_value_robust(ocr_lines, param)
                if val is not None:
                    st.session_state[f"val_{param}"] = float(val)
                else:
                    st.session_state[f"val_{param}"] = 0.0
        st.success("تم مسح وقراءة البيانات بنجاح! يرجى مراجعتها وتعديلها بالأسفل إذا لزم الأمر:")
    except Exception as e:
        st.error(f"حدث خطأ أثناء فحص الصورة: {e}. يرجى إدخال القيم يدوياً.")

# عرض ومراجعة القيم (تتأثر مباشرة بالـ Session State لضمان الحفظ اللحظي والتغير الفوري للتفسير)
st.markdown("### ✏️ Verify and Edit Parameters / مراجعة وتعديل قيم الفحص")
final_data = {}
col1, col2, col3 = st.columns(3)

for idx, param in enumerate(ranges.keys()):
    state_key = f"val_{param}"
    current_val = st.session_state.get(state_key, 0.0)
    
    with col1 if idx % 3 == 0 else col2 if idx % 3 == 1 else col3:
        final_data[param] = st.number_input(
            f"{param} ({ranges[param]['unit']}):", 
            value=float(current_val),
            step=0.01,
            key=f"input_{param}"
        )

# معالجة التفسير الطبي التفاعلي بمجرد النقر على الزر
if st.button("🧬 Run Deep Clinical Interpretation & Generate PDF"):
    status = {}
    insights_ar = []
    
    # حساب الحالات الطبية بناءً على القيم المدخلة حالياً في الحقول
    for param, val in final_data.items():
        r = ranges[param]
        if val < r["min"]:
            status[param] = "LOW"
        elif val > r["max"]:
            status[param] = "HIGH"
        else:
            status[param] = "NORMAL"
            
    # صياغة التفسير السريري التفاعلي بناءً على الأرقام الحالية في الحقول
    # RBC
    if status.get("RBC") == "HIGH":
        insights_ar.append("• ارتفاع RBC: قد يشير إلى الجفاف، الاستسقاء، أو أمراض الكلى.")
    elif status.get("RBC") == "LOW":
        insights_ar.append("• انخفاض RBC: يشير إلى فقر الدم (Anemia)؛ قد يكون بسبب نقص B12، نقص الحديد، أو إصابة مزمنة.")
        
    # Hb
    if status.get("Hb") == "HIGH":
        insights_ar.append("• ارتفاع Hb: قد يشير إلى وجود جفاف، سموم الكبد، أو تضخم في الكلى.")
    elif status.get("Hb") == "LOW":
        insights_ar.append("• انخفاض Hb: يشير إلى فقر الدم (Anemia) الناتج عن سوء التغذية أو نقص الحديد في الجسم.")
        
    # MCV & MCHC
    if final_data.get("MCV", 0) > 0 and status.get("MCV") == "LOW":
        insights_ar.append("• انخفاض MCV: مؤشر على نقص الحديد في الجسم أو تسمم بالرصاص.")
    if status.get("MCV") == "HIGH" and status.get("MCHC") == "LOW":
        insights_ar.append("• ارتفاع MCV مع انخفاض MCHC: يشير سريرياً إلى احتمالية الإصابة بالأنيميا الخبيثة.")
    elif status.get("MCHC") == "LOW":
        insights_ar.append("• انخفاض MCHC: يشير إلى أنيميا نقص الحديد.")

    # PLT
    if status.get("PLT") == "HIGH":
        insights_ar.append("• ارتفاع PLT: قد يشير إلى ورم دموي، التهابات نشطة، أو نزيف حاد.")
    elif status.get("PLT") == "LOW":
        insights_ar.append("• انخفاض PLT: يشير إلى خطر النزيف، نقص اليود، أو الإصابة بأمراض مناعية.")

    # WBC
    if status.get("WBC") == "HIGH":
        if final_data.get("WBC", 0) > (ranges["WBC"]["max"] * 2):
            insights_ar.append("• ارتفاع شديد جداً في WBC: مؤشر قوي يستدعي فحص خطر الإصابة بسرطان الدم (Leukemia).")
        else:
            insights_ar.append("• ارتفاع WBC: يشير إلى وجود التهابات في الجسم أو عدوى بكتيرية.")
    elif status.get("WBC") == "LOW":
        insights_ar.append("• انخفاض WBC: يشير إلى ضعف المناعة العام أو التعرض لعدوى فيروسية.")

    # Neutrophils
    if status.get("Neutrophils") == "HIGH":
        insights_ar.append("• ارتفاع Neutrophils: قد يرجع إلى التهاب بكتيري، جهد بدني شاق، أو تعرض الأنسجة لإصابات.")
    elif status.get("Neutrophils") == "LOW":
        insights_ar.append("• انخفاض Neutrophils: قد يشير إلى عدوى فيروسية، تسمم دموي، أو تسمم دوائي.")

    # Lymphocytes
    if status.get("Lymphocytes") == "HIGH":
        insights_ar.append("• ارتفاع Lymphocytes: مؤشر لعدوى فيروسية أو التهاب الكبد.")
    elif status.get("Lymphocytes") == "LOW":
        insights_ar.append("• انخفاض Lymphocytes: يشير إلى ضعف الجهاز المناعي أو تأثير علاج الكورتيزون.")

    # Eosinophils, Basophils, Monocytes
    if status.get("Eosinophils") == "HIGH":
        insights_ar.append("• ارتفاع Eosinophils: دليل على رد فعل تحسسي أو إصابة بالطفيليات.")
    if status.get("Basophils") == "HIGH":
        insights_ar.append("• ارتفاع Basophils: يشير إلى حالات الحساسية المفرطة.")
    if status.get("Monocytes") == "HIGH":
        insights_ar.append("• ارتفاع Monocytes: يشير إلى وجود التهاب مزمن في الجسم.")

    if not insights_ar:
        insights_ar.append("• كافة المؤشرات تقع ضمن الحدود الطبيعية للفصيلة المحددة.")

    st.write("---")
    st.markdown("### 📄 Clinical Interpretation / التفسير السريري المعتمد:")
    for ins in insights_ar:
        st.markdown(f"⭐ **{ins}**")

    # توليد ملف الـ PDF بأمان
    try:
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        
        # اختيار الألوان للتصميم
        title_color = colors.HexColor('#c0392b')
        green_color = colors.HexColor('#27ae60')
        dark_color = colors.HexColor('#2c3e50')
        border_color = colors.HexColor('#bdc3c7')
        bg_light = colors.HexColor('#f8f9fa')
        bg_alt = colors.HexColor('#f2f4f4')
        
        # استخدام خط Amiri إذا كان متاحاً لتجنب المربعات والرموز الغريبة بالكامل
        active_font = FONT_NAME if font_available else "Helvetica"
        
        arabic_style_title = ParagraphStyle(
            'ArabicTitle',
            fontName=active_font,
            fontSize=18,
            textColor=title_color,
            alignment=1, # توسيط
            spaceAfter=15
        )
        
        arabic_style_sub = ParagraphStyle(
            'ArabicSub',
            fontName=active_font,
            fontSize=10,
            textColor=dark_color,
            alignment=2, # يمين
            leading=14,
            spaceAfter=6
        )
        
        arabic_style_body = ParagraphStyle(
            'ArabicBody',
            fontName=active_font,
            fontSize=11,
            textColor=dark_color,
            alignment=2, # يمين
            leading=16,
            spaceAfter=6
        )
        
        arabic_style_header = ParagraphStyle(
            'ArabicHeader',
            fontName=active_font,
            fontSize=13,
            textColor=green_color,
            alignment=2, # يمين
            spaceBefore=12,
            spaceAfter=6
        )
        
        story = []
        
        # إضافة العناوين المنسقة والمقلوبة للغة العربية
        story.append(Paragraph(format_arabic("عيادة الحي البيطرية - AL-HAY VETERINARY CLINIC"), arabic_style_title))
        
        meta_info = f"<b>التاريخ:</b> {datetime.date.today().strftime('%Y-%m-%d')} | <b>اسم المربّي:</b> {owner_name} | <b>رقم الحيوان:</b> {animal_id}"
        story.append(Paragraph(format_arabic(meta_info), arabic_style_sub))
        
        species_info = f"<b>الفصيلة التي تم تحليلها:</b> {species}"
        story.append(Paragraph(format_arabic(species_info), arabic_style_sub))
        story.append(Spacer(1, 15))
        
        # إنشاء جدول التحاليل
        table_data = [
            ["Parameter", "Result", "Unit", "Status", "Reference Range"]
        ]
        for p, v in final_data.items():
            r = ranges[p]
            table_data.append(
                [p, f"{v:.2f}", r['unit'], status[p], f"{r['min']} - {r['max']}"]
            )
            
        t = Table(table_data, colWidths=[120, 80, 80, 80, 120])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), title_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('BACKGROUND', (0,1), (-1,-1), bg_light),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_alt]),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        
        # إضافة التفسيرات الطبية الصحيحة والمتزامنة
        story.append(Paragraph(format_arabic("الملاحظات والتفسيرات الطبية التفاعلية:"), arabic_style_header))
        story.append(Spacer(1, 5))
        
        for ins in insights_ar:
            story.append(Paragraph(format_arabic(ins), arabic_style_body))
            
        doc.build(story)
        pdf_data = pdf_buffer.getvalue()
        
        st.write("---")
        st.success("🎉 تم توليد التقرير بنجاح! اضغط بالأسفل لتحميل ملف الـ PDF:")
        st.download_button(
            label="⬇️ Download PDF Report / تحميل التقرير الطبي المعتمد",
            data=pdf_data,
            file_name=f"AlHay_CBC_Report_{animal_id}.pdf",
            mime="application/pdf"
        )
    except Exception as pdf_err:
        st.error(f"فشل في إنشاء ملف PDF بسبب خطأ في ترميز النصوص: {pdf_err}")
