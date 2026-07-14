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

# المسميات البديلة الشائعة لضمان دقة القراءة التلقائية
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

# خيار إدخال واضح يضمن عدم اختفاء أزرار التحميل
input_method = st.sidebar.selectbox(
    "Choose Input Method / طريقة رفع التقرير:",
    ["📁 Upload Image from Gallery (رفع من الاستوديو)", "📸 Use Device Camera (الكاميرا المباشرة)"]
)

uploaded_file = None
if "Gallery" in input_method:
    uploaded_file = st.file_uploader("Upload CBC Image / اختر صورة التقرير", type=["jpg", "jpeg", "png"])
else:
    uploaded_file = st.camera_input("Capture CBC Report Image / التقط صورة للتقرير")

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

# تهيئة حقول البيانات
extracted_data = {param: 0.0 for param in VET_REFERENCE_RANGES[species].keys()}

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Current Report Image", width=350)
    
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
    insights_ar = []  # تظهر على الشاشة أمام الطبيب بالعربية الفصحى
    insights_en = []  # تدرج في ملف الـ PDF كرموز ومصطلحات طبية واضحة بدون مشاكل تشوه الحروف
    
    for param, val in final_data.items():
        r = ranges[param]
        if val < r["min"]:
            status[param] = "LOW"
        elif val > r["max"]:
            status[param] = "HIGH"
        else:
            status[param] = "NORMAL"
            
    # تطبيق الگايد الطبي بالكامل
    # RBC
    if status.get("RBC") == "HIGH":
        insights_ar.append("• ارتفاع RBC: قد يشير إلى الجفاف، الاستسقاء، أو أمراض الكلى.")
        insights_en.append("- High RBC: Dehydration, Polycythemia or renal issues suspected.")
    elif status.get("RBC") == "LOW":
        insights_ar.append("• انخفاض RBC: يشير إلى فقر الدم (Anemia)؛ قد يكون بسبب نقص B12، نقص الحديد، أو إصابة مزمنة.")
        insights_en.append("- Low RBC: Indicates Anemia (B12 deficiency, Iron deficiency, or chronic disease).")
        
    # Hb
    if status.get("Hb") == "HIGH":
        insights_ar.append("• ارتفاع Hb: قد يشير إلى وجود جفاف، سموم الكبد، أو تضخم في الكلى.")
        insights_en.append("- High Hb: Dehydration or hepatic/renal issues suspected.")
    elif status.get("Hb") == "LOW":
        insights_ar.append("• انخفاض Hb: يشير إلى فقر الدم (Anemia) الناتج عن سوء التغذية أو نقص الحديد في الجسم.")
        insights_en.append("- Low Hb: Microcytic/Normocytic anemia (malnutrition or iron deficiency).")
        
    # MCV & MCHC
    if final_data.get("MCV", 0) > 0 and status.get("MCV") == "LOW":
        insights_ar.append("• انخفاض MCV: مؤشر على نقص الحديد في الجسم أو تسمم بالرصاص.")
        insights_en.append("- Low MCV: Microcytosis (highly indicative of Iron deficiency or Lead poisoning).")
    if status.get("MCV") == "HIGH" and status.get("MCHC") == "LOW":
        insights_ar.append("• ارتفاع MCV مع انخفاض MCHC: يشير سريرياً إلى احتمالية الإصابة بالأنيميا الخبيثة.")
        insights_en.append("- High MCV + Low MCHC: Macrocytic Hypochromic Anemia suspected (Pernicious Anemia).")
    elif status.get("MCHC") == "LOW":
        insights_ar.append("• انخفاض MCHC: يشير إلى أنيميا نقص الحديد.")
        insights_en.append("- Low MCHC: Hypochromic anemia (Iron deficiency).")

    # PLT
    if status.get("PLT") == "HIGH":
        insights_ar.append("• ارتفاع PLT: قد يشير إلى ورم دموي، التهابات نشطة، أو نزيف حاد.")
        insights_en.append("- High PLT: Thrombocytosis (inflammation, acute hemorrhage, or bone marrow response).")
    elif status.get("PLT") == "LOW":
        insights_ar.append("• انخفاض PLT: يشير إلى خطر النزيف، نقص اليود، أو الإصابة بأمراض مناعية.")
        insights_en.append("- Low PLT: Thrombocytopenia (increased bleeding risk, viral or immune-mediated).")

    # WBC
    if status.get("WBC") == "HIGH":
        if final_data.get("WBC", 0) > (ranges["WBC"]["max"] * 2):
            insights_ar.append("• ارتفاع شديد جداً في WBC: مؤشر قوي يستدعي فحص خطر الإصابة بسرطان الدم (Leukemia).")
            insights_en.append("- Critical High WBC: Strong leukocytosis (highly raises Leukemia/severe sepsis suspicion).")
        else:
            insights_ar.append("• ارتفاع WBC: يشير إلى وجود التهابات في الجسم أو عدوى بكتيرية.")
            insights_en.append("- High WBC: Leukocytosis (indicates systemic inflammation or bacterial infection).")
    elif status.get("WBC") == "LOW":
        insights_ar.append("• انخفاض WBC: يشير إلى ضعف المناعة العام أو التعرض لعدوى فيروسية.")
        insights_en.append("- Low WBC: Leukopenia (viral infection or immunosuppression risks).")

    # Neutrophils
    if status.get("Neutrophils") == "HIGH":
        insights_ar.append("• ارتفاع Neutrophils: قد يرجع إلى التهاب بكتيري، جهد بدني شاق، أو تعرض الأنسجة لإصابات.")
        insights_en.append("- High Neutrophils: Bacterial infection, tissue damage, or physiological stress.")
    elif status.get("Neutrophils") == "LOW":
        insights_ar.append("• انخفاض Neutrophils: قد يشير إلى عدوى فيروسية، تسمم دموي، أو تسمم دوائي.")
        insights_en.append("- Low Neutrophils: Viral infection, severe toxemia, or drug-induced.")

    # Lymphocytes
    if status.get("Lymphocytes") == "HIGH":
        insights_ar.append("• ارتفاع Lymphocytes: مؤشر لعدوى فيروسية أو التهاب الكبد.")
        insights_en.append("- High Lymphocytes: Viral infection or chronic antigenic stimulation.")
    elif status.get("Lymphocytes") == "LOW":
        insights_ar.append("• انخفاض Lymphocytes: يشير إلى ضعف الجهاز المناعي أو تأثير علاج الكورتيزون.")
        insights_en.append("- Low Lymphocytes: Stress leukogram or corticosteroid effect.")

    # Eosinophils, Basophils, Monocytes
    if status.get("Eosinophils") == "HIGH":
        insights_ar.append("• ارتفاع Eosinophils: دليل على رد فعل تحسسي أو إصابة بالطفيليات.")
        insights_en.append("- High Eosinophils: Allergic response or parasitic infestation.")
    if status.get("Basophils") == "HIGH":
        insights_ar.append("• ارتفاع Basophils: يشير إلى حالات الحساسية المفرطة.")
        insights_en.append("- High Basophils: Hypersensitivity reactions.")
    if status.get("Monocytes") == "HIGH":
        insights_ar.append("• ارتفاع Monocytes: يشير إلى وجود التهاب مزمن في الجسم.")
        insights_en.append("- High Monocytes: Chronic inflammation.")

    if not insights_ar:
        insights_ar.append("• كافة المؤشرات تقع ضمن الحدود الطبيعية للفصيلة المحددة.")
        insights_en.append("- All parameters are within normal reference ranges.")

    st.write("---")
    st.markdown("### 📄 Clinical Interpretation / التفسير السريري المعتمد:")
    for ins in insights_ar:
        st.markdown(f"⭐ **{ins}**")

    # بناء الـ PDF وتفادي مشكلة المربعات السوداء تماماً
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    
    title_color = colors.HexColor('#c0392b')
    green_color = colors.HexColor('#27ae60')
    dark_color = colors.HexColor('#2c3e50')
    border_color = colors.HexColor('#bdc3c7')
    bg_light = colors.HexColor('#f8f9fa')
    bg_alt = colors.HexColor('#f2f4f4')
    
    title_style = ParagraphStyle(
        'TitleStyle', 
        fontName='Helvetica-Bold', 
        fontSize=20, 
        textColor=title_color, 
        spaceAfter=15, 
        alignment=1
    )
    
    sub_style = ParagraphStyle(
        'SubStyle', 
        fontName='Helvetica', 
        fontSize=11, 
        spaceAfter=6,
        leading=14
    )
    
    ins_header_style = ParagraphStyle(
        'InsHeaderStyle',
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=green_color,
        spaceBefore=12,
        spaceAfter=6
    )
    
    ins_style = ParagraphStyle(
        'InsStyle', 
        fontName='Helvetica', 
        fontSize=11, 
        textColor=dark_color, 
        spaceAfter=6, 
        leading=15
    )
    
    story = []
    story.append(Paragraph("AL-HAY VETERINARY CLINIC", title_style))
    
    meta_info = f"<b>Date:</b> {datetime.date.today().strftime('%Y-%m-%d')} | <b>Owner Name:</b> {owner_name} | <b>Animal ID:</b> {animal_id}"
    story.append(Paragraph(meta_info, sub_style))
    
    species_info = f"<b>Species Analyzed:</b> {species}"
    story.append(Paragraph(species_info, sub_style))
    story.append(Spacer(1, 15))
    
    # الجدول الطبي
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
    
    # إدراج التفسير الطبي المعتمد بالإنجليزية في التقرير لحل مشكلة المربعات نهائياً
    story.append(Paragraph("CLINICAL NOTES & INTERPRETATION (ENGLISH):", ins_header_style))
    story.append(Spacer(1, 5))
    
    for ins in insights_en:
        story.append(Paragraph(ins, ins_style))
        
    doc.build(story)
    pdf_data = pdf_buffer.getvalue()
    
    st.download_button(
        label="⬇️ Download PDF Report / تحميل التقرير الطبي",
        data=pdf_data,
        file_name=f"AlHay_CBC_Report_{animal_id}.pdf",
        mime="application/pdf"
    )
