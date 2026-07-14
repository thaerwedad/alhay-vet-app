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

# إعداد خط اللغة العربية لتفادي المربعات السوداء في الـ PDF
FONT_PATH = "Amiri-Regular.ttf"
@st.cache_resource
def download_arabic_font():
    if not os.path.exists(FONT_PATH):
        font_url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        try:
            urllib.request.urlretrieve(font_url, FONT_PATH)
            pdfmetrics.registerFont(TTFont('Amiri', FONT_PATH))
        except Exception as e:
            st.warning(f"Failed to download Arabic font. Fallback to English in PDF. Error: {e}")

download_arabic_font()

# دالة ذكية لتجهيز النصوص العربية للطباعة في الـ PDF
def format_arabic(text):
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception:
        return text

# المسميات البديلة لضمان دقة القراءة التلقائية
PARAM_ALIASES = {
    "RBC": ["RBC", "Red Blood", "R.B.C", "Erythrocytes"],
    "Hb": ["Hb", "Hgb", "Hemoglobin", "HGB"],
    "PCV": ["PCV", "Hct", "Hematocrit", "HCT"],
    "MCV": ["MCV", "M.C.V", "Mean Corpuscular Volume"],
    "MCHC": ["MCHC", "M.C.H.C"],
    "WBC": ["WBC", "White Blood", "W.B.C", "Leukocytes"],
    "PLT": ["PLT", "Platelet", "Platelets", "Thrombocytes"],
    "Neutrophils": ["Neutrophils", "NEUT", "Neut", "Neutrophil"],
    "Lymphocytes": ["Lymphocytes", "LYMP", "Lym", "Lymph", "Lymphocyte"],
    "Eosinophils": ["Eosinophils", "EOS", "Eos", "Eosinophil"],
    "Basophils": ["Basophils", "BAS", "Bas", "Basophil"],
    "Monocytes": ["Monocytes", "MON", "Mon", "Monocyte"]
}

# النطاقات المرجعية الشاملة للحيوانات والدواجن
VET_REFERENCE_RANGES = {
    "Dog": {
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
    "Cat": {
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
    "Poultry": {
        "RBC": {"min": 2.5, "max": 3.5, "unit": "x10^6/µL"},
        "Hb": {"min": 7.0, "max": 13.0, "unit": "g/dL"},
        "PCV": {"min": 22.0, "max": 35.0, "unit": "%"},
        "MCV": {"min": 90.0, "max": 140.0, "unit": "fL"},
        "MCHC": {"min": 26.0, "max": 35.0, "unit": "g/dL"},
        "WBC": {"min": 12.0, "max": 30.0, "unit": "x10^3/µL"},
        "PLT": {"min": 20.0, "max": 40.0, "unit": "x10^3/µL"},
        "Neutrophils": {"min": 25.0, "max": 45.0, "unit": "%"},
        "Lymphocytes": {"min": 45.0, "max": 70.0, "unit": "%"},
        "Eosinophils": {"min": 0.0, "max": 4.0, "unit": "%"},
        "Basophils": {"min": 0.0, "max": 2.0, "unit": "%"},
        "Monocytes": {"min": 1.0, "max": 5.0, "unit": "%"}
    }
}

st.set_page_config(
    page_title="Al-Hay Veterinary Clinic", 
    page_icon="🐾",
    layout="wide"
)

st.title("🐾 Al-Hay Veterinary Clinic")
st.subheader("Professional Automated CBC Interpretation System")

st.sidebar.header("📋 Case Information / بيانات الحالة")
owner_name = st.sidebar.text_input("Owner Name / اسم المربّي:", "Client")
animal_id = st.sidebar.text_input("Animal ID / رقم الحيوان:", "None")
species = st.sidebar.selectbox("Species / الفصيلة:", list(VET_REFERENCE_RANGES.keys()))

def extract_param_value_robust(text_lines, param_name):
    aliases = PARAM_ALIASES.get(param_name, [param_name])
    for i, line in enumerate(text_lines):
        if any(re.search(r'\b' + re.escape(alias) + r'\b', line, re.IGNORECASE) for alias in aliases):
            # البحث عن أي رقم عشري أو صحيح داخل السطر أو الأسطر الثلاثة التالية
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

# تهيئة حقول البيانات المستخرجة
extracted_data = {param: 0.0 for param in VET_REFERENCE_RANGES[species].keys()}

st.markdown("### 📥 Select Input Method / اختر طريقة الإدخال:")

tab_gallery, tab_camera = st.tabs([
    "📁 Upload from Gallery (رفع من الاستوديو)", 
    "📸 Use Live Camera (استخدام الكاميرا)"
])

uploaded_file = None

with tab_gallery:
    gallery_file = st.file_uploader(
        "Choose an image from your device / اختر صورة التقرير", 
        type=["jpg", "jpeg", "png"],
        key="gallery_uploader"
    )
    if gallery_file is not None:
        uploaded_file = gallery_file

with tab_camera:
    camera_file = st.camera_input(
        "Capture a photo of the CBC Report / التقط صورة للتقرير",
        key="camera_capturer"
    )
    if camera_file is not None:
        uploaded_file = camera_file

# معالجة الصورة باستخدام Tesseract OCR عالي الكفاءة
if uploaded_file is not None:
    try:
        image = Image.open(uploaded_file)
        st.image(image, caption="Active Image for Analysis", width=350)
        
        with st.spinner("Processing image and scanning data..."):
            # تحسين جودة الصورة لزيادة دقة التعرف على الأرقام
            img_np = np.array(image)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            ocr_text = pytesseract.image_to_string(gray, config='--psm 6')
            ocr_lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
            
            ranges = VET_REFERENCE_RANGES[species]
            for param in ranges.keys():
                val = extract_param_value_robust(ocr_lines, param)
                if val is not None:
                    extracted_data[param] = val
                else:
                    extracted_data[param] = 0.0
        st.success("Data scanned successfully! Review or edit the parameters below:")
    except Exception as img_err:
        st.error(f"Error processing image: {img_err}")

st.markdown("### ✏️ Verify and Edit Parameters / مراجعة وتعديل القيم")
final_data = {}
col1, col2, col3 = st.columns(3)
ranges = VET_REFERENCE_RANGES[species]

for idx, param in enumerate(ranges.keys()):
    current_val = extracted_data.get(param, 0.0)
    with col1 if idx % 3 == 0 else col2 if idx % 3 == 1 else col3:
        final_data[param] = st.number_input(
            f"{param} ({ranges[param]['unit']}):", 
            value=float(current_val),
            step=0.01,
            key=f"input_{param}"
        )

if st.button("🧬 Run Deep Clinical Interpretation & Generate PDF"):
    status = {}
    insights_ar = []  # تظهر على الشاشة بالعربية
    insights_pdf_ar = []  # سيتم معالجتها بالخط العربي المعتمد Amiri داخل الـ PDF
    
    for param, val in final_data.items():
        r = ranges[param]
        if val < r["min"]:
            status[param] = "LOW"
        elif val > r["max"]:
            status[param] = "HIGH"
        else:
            status[param] = "NORMAL"
            
    # تطبيق التحليلات والجايد الطبي العربي والترجمة الخاصة بـ PDF
    # RBC
    if status.get("RBC") == "HIGH":
        insights_ar.append("• ارتفاع RBC: قد يشير إلى الجفاف، الاستسقاء، أو أمراض الكلى.")
        insights_pdf_ar.append("• ارتفاع RBC: قد يشير إلى الجفاف، الاستسقاء، أو أمراض الكلى.")
    elif status.get("RBC") == "LOW":
        insights_ar.append("• انخفاض RBC: يشير إلى فقر الدم (Anemia)؛ قد يكون بسبب نقص B12، نقص الحديد، أو إصابة مزمنة.")
        insights_pdf_ar.append("• انخفاض RBC: يشير إلى فقر الدم (Anemia)؛ قد يكون بسبب نقص B12، نقص الحديد، أو إصابة مزمنة.")
        
    # Hb
    if status.get("Hb") == "HIGH":
        insights_ar.append("• ارتفاع Hb: قد يشير إلى وجود جفاف، سموم الكبد، أو تضخم في الكلى.")
        insights_pdf_ar.append("• ارتفاع Hb: قد يشير إلى وجود جفاف، سموم الكبد، أو تضخم في الكلى.")
    elif status.get("Hb") == "LOW":
        insights_ar.append("• انخفاض Hb: يشير إلى فقر الدم (Anemia) الناتج عن سوء التغذية أو نقص الحديد في الجسم.")
        insights_pdf_ar.append("• انخفاض Hb: يشير إلى فقر الدم (Anemia) الناتج عن سوء التغذية أو نقص الحديد في الجسم.")
        
    # MCV & MCHC
    if final_data.get("MCV", 0) > 0 and status.get("MCV") == "LOW":
        insights_ar.append("• انخفاض MCV: مؤشر على نقص الحديد في الجسم أو تسمم بالرصاص.")
        insights_pdf_ar.append("• انخفاض MCV: مؤشر على نقص الحديد في الجسم أو تسمم بالرصاص.")
    if status.get("MCV") == "HIGH" and status.get("MCHC") == "LOW":
        insights_ar.append("• ارتفاع MCV مع انخفاض MCHC: يشير سريرياً إلى احتمالية الإصابة بالأنيميا الخبيثة.")
        insights_pdf_ar.append("• ارتفاع MCV مع انخفاض MCHC: يشير سريرياً إلى احتمالية الإصابة بالأنيميا الخبيثة.")
    elif status.get("MCHC") == "LOW":
        insights_ar.append("• انخفاض MCHC: يشير إلى أنيميا نقص الحديد.")
        insights_pdf_ar.append("• انخفاض MCHC: يشير إلى أنيميا نقص الحديد.")

    # PLT
    if status.get("PLT") == "HIGH":
        insights_ar.append("• ارتفاع PLT: قد يشير إلى ورم دموي، التهابات نشطة، أو نزيف حاد.")
        insights_pdf_ar.append("• ارتفاع PLT: قد يشير إلى ورم دموي، التهابات نشطة، أو نزيف حاد.")
    elif status.get("PLT") == "LOW":
        insights_ar.append("• انخفاض PLT: يشير إلى خطر النزيف، نقص اليود، أو الإصابة بأمراض مناعية.")
        insights_pdf_ar.append("• انخفاض PLT: يشير إلى خطر النزيف، نقص اليود، أو الإصابة بأمراض مناعية.")

    # WBC
    if status.get("WBC") == "HIGH":
        if final_data.get("WBC", 0) > (ranges["WBC"]["max"] * 2):
            insights_ar.append("• ارتفاع شديد جداً في WBC: مؤشر قوي يستدعي فحص خطر الإصابة سرطان الدم (Leukemia).")
            insights_pdf_ar.append("• ارتفاع شديد جداً في WBC: مؤشر قوي يستدعي فحص خطر الإصابة سرطان الدم (Leukemia).")
        else:
            insights_ar.append("• ارتفاع WBC: يشير إلى وجود التهابات في الجسم أو عدوى بكتيرية.")
            insights_pdf_ar.append("• ارتفاع WBC: يشير إلى وجود التهابات في الجسم أو عدوى بكتيرية.")
    elif status.get("WBC") == "LOW":
        insights_ar.append("• انخفاض WBC: يشير إلى ضعف المناعة العام أو التعرض لعدوى فيروسية.")
        insights_pdf_ar.append("• انخفاض WBC: يشير إلى ضعف المناعة العام أو التعرض لعدوى فيروسية.")

    # Neutrophils
    if status.get("Neutrophils") == "HIGH":
        insights_ar.append("• ارتفاع Neutrophils: قد يرجع إلى التهاب بكتيري، جهد بدني شاق، أو تعرض الأنسجة لإصابات.")
        insights_pdf_ar.append("• ارتفاع Neutrophils: قد يرجع إلى التهاب بكتيري، جهد بدني شاق، أو تعرض الأنسجة لإصابات.")
    elif status.get("Neutrophils") == "LOW":
        insights_ar.append("• انخفاض Neutrophils: قد يشير إلى عدوى فيروسية، تسمم دموي، أو تسمم دوائي.")
        insights_pdf_ar.append("• انخفاض Neutrophils: قد يشير إلى عدوى فيروسية، تسمم دموي، أو تسمم دوائي.")

    # Lymphocytes
    if status.get("Lymphocytes") == "HIGH":
        insights_ar.append("• ارتفاع Lymphocytes: مؤشر لعدوى فيروسية أو التهاب الكبد.")
        insights_pdf_ar.append("• ارتفاع Lymphocytes: مؤشر لعدوى فيروسية أو التهاب الكبد.")
    elif status.get("Lymphocytes") == "LOW":
        insights_ar.append("• انخفاض Lymphocytes: يشير إلى ضعف الجهاز المناعي أو تأثير علاج الكورتيزون.")
        insights_pdf_ar.append("• انخفاض Lymphocytes: يشير إلى ضعف الجهاز المناعي أو تأثير علاج الكورتيزون.")

    # Eosinophils, Basophils, Monocytes
    if status.get("Eosinophils") == "HIGH":
        insights_ar.append("• ارتفاع Eosinophils: دليل على رد فعل تحسسي أو إصابة بالطفيليات.")
        insights_pdf_ar.append("• ارتفاع Eosinophils: دليل على رد فعل تحسسي أو إصابة بالطفيليات.")
    if status.get("Basophils") == "HIGH":
        insights_ar.append("• ارتفاع Basophils: يشير إلى حالات الحساسية المفرطة.")
        insights_pdf_ar.append("• ارتفاع Basophils: يشير إلى حالات الحساسية المفرطة.")
    if status.get("Monocytes") == "HIGH":
        insights_ar.append("• ارتفاع Monocytes: يشير إلى وجود التهاب مزمن في الجسم.")
        insights_pdf_ar.append("• ارتفاع Monocytes: يشير إلى وجود التهاب مزمن في الجسم.")

    if not insights_ar:
        insights_ar.append("• كافة المؤشرات تقع ضمن الحدود الطبيعية للفصيلة المحددة.")
        insights_pdf_ar.append("• كافة المؤشرات تقع ضمن الحدود الطبيعية للفصيلة المحددة.")

    st.write("---")
    st.markdown("### 📄 Clinical Interpretation / التفسير السريري المعتمد:")
    for ins in insights_ar:
        st.markdown(f"⭐ **{ins}**")

    # إنشاء ملف الـ PDF مع الحماية من المربعات وتنسيق الخطوط العربية
    try:
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        
        title_color = colors.HexColor('#c0392b')
        green_color = colors.HexColor('#27ae60')
        dark_color = colors.HexColor('#2c3e50')
        border_color = colors.HexColor('#bdc3c7')
        bg_light = colors.HexColor('#f8f9fa')
        bg_alt = colors.HexColor('#f2f4f4')
        
        # استخدام خط Amiri للغة العربية وتعديل خصائص ParagraphStyle
        arabic_style_title = ParagraphStyle(
            'ArabicTitle',
            fontName='Amiri',
            fontSize=22,
            textColor=title_color,
            alignment=1, # وسط الصفحة
            spaceAfter=15
        )
        
        arabic_style_sub = ParagraphStyle(
            'ArabicSub',
            fontName='Amiri',
            fontSize=11,
            textColor=dark_color,
            alignment=2, # يمين الصفحة
            leading=14,
            spaceAfter=6
        )
        
        arabic_style_body = ParagraphStyle(
            'ArabicBody',
            fontName='Amiri',
            fontSize=12,
            textColor=dark_color,
            alignment=2, # يمين الصفحة
            leading=16,
            spaceAfter=6
        )
        
        arabic_style_header = ParagraphStyle(
            'ArabicHeader',
            fontName='Amiri',
            fontSize=14,
            textColor=green_color,
            alignment=2, # يمين الصفحة
            spaceBefore=12,
            spaceAfter=6
        )
        
        story = []
        
        # العنوان والبيانات مفروسة باللغة العربية الصحيحة
        story.append(Paragraph(format_arabic("عيادة الحي البيطرية - AL-HAY VETERINARY CLINIC"), arabic_style_title))
        
        meta_info = f"<b>التاريخ:</b> {datetime.date.today().strftime('%Y-%m-%d')} | <b>اسم المربي:</b> {owner_name} | <b>رقم الحيوان:</b> {animal_id}"
        story.append(Paragraph(format_arabic(meta_info), arabic_style_sub))
        
        species_info = f"<b>الفصيلة التي تم تحليلها:</b> {species}"
        story.append(Paragraph(format_arabic(species_info), arabic_style_sub))
        story.append(Spacer(1, 15))
        
        # الجدول الطبي في ملف الـ PDF
        table_data = [
            ["Parameter", "Result", "Unit", "Status", "Reference Range"]
        ]
        for p, v in final_data.items():
            r = ranges[p]
            table_data.append(
                [p, f"{v:.2f}", r['unit'], status[p], f"{r['min']} - {r['max']}"]
            )
            
        t = Table(table_data, colWidths=[120, 90, 80, 90, 120])
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
        
        story.append(Paragraph(format_arabic("الملاحظات والتفسيرات الطبية:"), arabic_style_header))
        story.append(Spacer(1, 5))
        
        for ins in insights_pdf_ar:
            story.append(Paragraph(format_arabic(ins), arabic_style_body))
            
        doc.build(story)
        pdf_data = pdf_buffer.getvalue()
        
        st.download_button(
            label="⬇️ Download PDF Report / تحميل التقرير الطبي",
            data=pdf_data,
            file_name=f"AlHay_CBC_Report_{animal_id}.pdf",
            mime="application/pdf"
        )
    except Exception as pdf_err:
        st.error(f"Error generating PDF: {pdf_err}")
