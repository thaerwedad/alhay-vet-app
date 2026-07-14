import streamlit as st
import cv2
import numpy as np
import re
import datetime
from PIL import Image
import easyocr
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, 
    Paragraph, 
    Spacer, 
    Table, 
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

# المسميات البديلة الشائعة في المختبرات الطبية لضمان دقة القراءة
PARAM_ALIASES = {
    "RBC": ["RBC", "Red Blood", "R.B.C", "Erythrocytes"],
    "Hb": ["Hb", "Hgb", "Hemoglobin", "HGB"],
    "PCV": ["PCV", "Hct", "Hematocrit", "HCT"],
    "MCV": ["MCV", "M.C.V", "Mean Corpuscular Volume"],
    "MCHC": ["MCHC", "M.C.H.C"],
    "WBC": ["WBC", "White Blood", "W.B.C", "Leukocytes"],
    "PLT": ["PLT", "Platelet", "Platelets", "Thrombocytes"],
    "Neutrophils": ["Neutrophils", "NEUT", "Neut", "LYM%", "Neutrophil"],
    "Lymphocytes": ["Lymphocytes", "LYMP", "Lym", "Lymph", "Lymphocyte"],
    "Eosinophils": ["Eosinophils", "EOS", "Eos", "Eosinophil"],
    "Basophils": ["Basophils", "BAS", "Bas", "Basophil"],
    "Monocytes": ["Monocytes", "MON", "Mon", "Monocyte"]
}

# نطاقات المرجعية الشاملة بناءً على الگايد الجديد
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

input_method = st.sidebar.radio(
    "Choose Input Method / طريقة الإدخال:",
    ["📸 Use Camera (الكاميرا)", "📁 Upload (رفع صورة)"]
)

uploaded_file = None
if "Camera" in input_method:
    uploaded_file = st.camera_input("Capture CBC Report Image")
else:
    uploaded_file = st.file_uploader("Upload CBC Image", type=["jpg", "jpeg", "png"])

def extract_param_value_robust(text_list, param_name):
    aliases = PARAM_ALIASES.get(param_name, [param_name])
    for i, text in enumerate(text_list):
        cleaned_text = text.replace(':', '').replace('-', '').strip()
        if any(re.search(r'\b' + re.escape(alias) + r'\b', cleaned_text, re.IGNORECASE) for alias in aliases):
            for j in range(i+1, min(i+5, len(text_list))):
                next_text = text_list[j].replace(' ', '').replace(',', '.')
                match = re.search(r'[-+]?\d*\.\d+|\d+', next_text)
                if match:
                    try:
                        val = float(match.group())
                        if val > 0:
                            return val
                    except ValueError:
                        continue
    return None

# قراءة النتائج
extracted_data = {param: 0.0 for param in VET_REFERENCE_RANGES[species].keys()}

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded CBC Report", width=350)
    
    with st.spinner("Processing image and scanning data..."):
        img_np = np.array(image)
        ocr_results = reader.readtext(img_np, detail=0)
        ranges = VET_REFERENCE_RANGES[species]
        for param in ranges.keys():
            val = extract_param_value_robust(ocr_results, param)
            if val is not None:
                extracted_data[param] = val
            else:
                extracted_data[param] = 0.0
    st.success("Data scanned! Please verify and adjust values below if needed:")

# حقول إدخال القيم لتمكين الطبيب من تعديل الأخطاء يدوياً لضمان دقة التقرير والـ PDF
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
    insights_ar = [] # قائمة لتخزين التفسير باللغة العربية
    
    for param, val in final_data.items():
        r = ranges[param]
        if val < r["min"]:
            status[param] = "LOW"
        elif val > r["max"]:
            status[param] = "HIGH"
        else:
            status[param] = "NORMAL"
            
    # تطبيق الگايد الطبي بالكامل باللغة العربية
    # 1. تحليل كرات الدم الحمراء (RBC)
    if status.get("RBC") == "HIGH":
        insights_ar.append("• ارتفاع RBC: قد يشير إلى الجفاف، الاستسقاء، أو أمراض الكلى.")
    elif status.get("RBC") == "LOW":
        insights_ar.append("• انخفاض RBC: يشير إلى فقر الدم (Anemia)؛ قد يكون بسبب نقص B12، نقص الحديد، أو إصابة مزمنة.")
        
    # 2. تحليل الهيموجلوبين (Hb)
    if status.get("Hb") == "HIGH":
        insights_ar.append("• ارتفاع Hb: قد يشير إلى وجود جفاف، سموم الكبد، أو تضخم في الكلى.")
    elif status.get("Hb") == "LOW":
        insights_ar.append("• انخفاض Hb: يشير إلى فقر الدم (Anemia) الناتج عن سوء التغذية أو نقص الحديد في الجسم.")
        
    # 3. تحليل MCV & MCHC
    if final_data.get("MCV", 0) > 0 and status.get("MCV") == "LOW":
        insights_ar.append("• انخفاض MCV: مؤشر على نقص الحديد في الجسم أو تسمم بالرصاص.")
    if status.get("MCV") == "HIGH" and status.get("MCHC") == "LOW":
        insights_ar.append("• ارتفاع MCV مع انخفاض MCHC: يشير سريرياً إلى احتمالية الإصابة بالأنيميا الخبيثة.")
    elif status.get("MCHC") == "LOW":
        insights_ar.append("• انخفاض MCHC: يشير إلى أنيميا نقص الحديد.")

    # 4. تحليل الصفائح الدموية (PLT)
    if status.get("PLT") == "HIGH":
        insights_ar.append("• ارتفاع PLT: قد يشير إلى ورم دموي، التهابات نشطة، أو نزيف حاد.")
    elif status.get("PLT") == "LOW":
        insights_ar.append("• انخفاض PLT: يشير إلى خطر النزيف، نقص اليود، أو الإصابة بأمراض مناعية.")

    # 5. تحليل خلايا الدم البيضاء (WBC)
    if status.get("WBC") == "HIGH":
        # فحص إذا كان الارتفاع كبيراً جداً (أكبر من ضعف الحد الأقصى كدليل على اللوكيميا)
        if final_data.get("WBC", 0) > (ranges["WBC"]["max"] * 2):
            insights_ar.append("• ارتفاع شديد جداً في WBC: مؤشر قوي جداً يستدعي فحص خطر الإصابة بسرطان الدم (Leukemia).")
        else:
            insights_ar.append("• ارتفاع WBC: يشير إلى وجود التهابات في الجسم أو عدوى بكتيرية.")
    elif status.get("WBC") == "LOW":
        insights_ar.append("• انخفاض WBC: يشير إلى ضعف المناعة العام أو التعرض لعدوى فيروسية.")

    # 6. تحليل الخلايا المتعادلة (Neutrophils)
    if status.get("Neutrophils") == "HIGH":
        insights_ar.append("• ارتفاع Neutrophils: قد يرجع إلى التهاب بكتيري، جهد بدني شاق، أو تعرض الأنسجة لإصابات.")
    elif status.get("Neutrophils") == "LOW":
        insights_ar.append("• انخفاض Neutrophils: قد يشير إلى عدوى فيروسية، تسمم دموي، أو تسمم دوائي.")

    # 7. تحليل الخلايا اللمفاوية (Lymphocytes)
    if status.get("Lymphocytes") == "HIGH":
        insights_ar.append("• ارتفاع Lymphocytes: مؤشر لعدوى فيروسية أو التهاب الكبد.")
    elif status.get("Lymphocytes") == "LOW":
        insights_ar.append("• انخفاض Lymphocytes: يشير إلى ضعف الجهاز المناعي أو تأثير علاج الكورتيزون.")

    # 8. تحليل الخلايا الحامضية والقاعدية والوحيدة (Eosinophils, Basophils, Monocytes)
    if status.get("Eosinophils") == "HIGH":
        insights_ar.append("• ارتفاع Eosinophils: دليل على رد فعل تحسسي أو إصابة بالطفيليات.")
    if status.get("Basophils") == "HIGH":
        insights_ar.append("• ارتفاع Basophils: يشير إلى حالات الحساسية.")
    if status.get("Monocytes") == "HIGH":
        insights_ar.append("• ارتفاع Monocytes: يشير إلى وجود التهاب مزمن في الجسم.")

    # في حال كانت كافة التحاليل طبيعية
    if not insights_ar:
        insights_ar.append("• كافة المؤشرات تقع ضمن الحدود الطبيعية للفصيلة المحددة.")

    # عرض التفسير الطبي المطور باللغة العربية على الشاشة فوراً
    st.write("---")
    st.markdown("### 📄 Clinical Interpretation / التفسير السريري المعتمد:")
    for ins in insights_ar:
        st.markdown(f"⭐ **{ins}**")

    # توليد ملف الـ PDF الاحترافي بالبيانات المعدلة الحقيقية
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'T1', 
        fontName='Helvetica-Bold', 
        fontSize=20, 
        textColor=colors.HexColor('#c0392b'), 
        spaceAfter=15, 
        alignment=1
    )
    sub_style = ParagraphStyle(
        'S1', 
        fontName='Helvetica', 
        fontSize=11, 
        spaceAfter=6,
        leading=14
    )
    ins_style = ParagraphStyle(
        'I1', 
        fontName='Helvetica', 
        fontSize=11, 
        textColor=colors.HexColor('#2c3e50'), 
        spaceAfter=6, 
        leading=15
    )
    
    story = []
    story.append(Paragraph("AL-HAY VETERINARY CLINIC", title_style))
    story.append(
        Paragraph(
            f"<b>Date:</b> {datetime.date.today().strftime('%Y-%m-%d')} | "
            f"<b>Owner Name:</b> {owner_name} | "
            f"<b>Animal ID:</b> {animal_id}", 
            sub
