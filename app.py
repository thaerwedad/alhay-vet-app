import streamlit as st
import cv2
import numpy as np
import re
import datetime
from PIL import Image
import easyocr
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

# إعداد قارئ النصوص الذكي من الصورة
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

# قاعدة بيانات النطاقات الطبيعية الكاملة والمحدثة (بما فيها الدواجن)
VET_REFERENCE_RANGES = {
    "Dog (كلب)": {
        "RBC": {"min": 5.5, "max": 8.5, "unit": "x10^6/µL"},
        "Hb": {"min": 12.0, "max": 18.0, "unit": "g/dL"},
        "PCV": {"min": 37.0, "max": 55.0, "unit": "%"},
        "WBC": {"min": 6.0, "max": 17.0, "unit": "x10^3/µL"},
        "PLT": {"min": 200, "max": 500, "unit": "x10^3/µL"}
    },
    "Cat (قط)": {
        "RBC": {"min": 6.0, "max": 10.0, "unit": "x10^6/µL"},
        "Hb": {"min": 8.0, "max": 15.0, "unit": "g/dL"},
        "PCV": {"min": 24.0, "max": 45.0, "unit": "%"},
        "WBC": {"min": 5.5, "max": 19.5, "unit": "x10^3/µL"},
        "PLT": {"min": 300, "max": 800, "unit": "x10^3/µL"}
    },
    "Poultry (دواجن/دجاج)": {
        "RBC": {"min": 2.5, "max": 3.5, "unit": "x10^6/µL"},
        "Hb": {"min": 7.0, "max": 13.0, "unit": "g/dL"},
        "PCV": {"min": 22.0, "max": 35.0, "unit": "%"},
        "WBC": {"min": 12.0, "max": 30.0, "unit": "x10^3/µL"},
        "PLT": {"min": 20.0, "max": 40.0, "unit": "x10^3/µL"}
    }
}

# إعدادات واجهة الموبايل عبر Streamlit
st.set_page_config(page_title="عيادة الحي البيطرية", page_icon="🐾")
st.title("🐾 عيادة الحي البيطرية")
st.subheader("نظام المسح الضوئي والتفسير التلقائي لـ CBC")

# القائمة الجانبية لإدخال بيانات التقرير المطبوع
st.sidebar.header("📋 بيانات المراجع والحالة")
owner_name = st.sidebar.text_input("اسم المربي:", "عميل محترم")
animal_id = st.sidebar.text_input("اسم/رقم الحيوان:", "غير محدد")
species = st.sidebar.selectbox("الفصيلة المستهدفة:", list(VET_REFERENCE_RANGES.keys()))

# التقاط الصورة مباشرة بكاميرا الموبايل
uploaded_file = st.camera_input("التقط صورة واضحة ومستقيمة لورقة تحليل الـ CBC")

def extract_param_value(text_list, param_name):
    for i, text in enumerate(text_list):
        if re.search(r'\b' + param_name + r'\b', text, re.IGNORECASE):
            for j in range(i+1, min(i+4, len(text_list))):
                next_text = text_list[j].replace(' ', '')
                match = re.search(r'[-+]?\d*\.\d+|\d+', next_text)
                if match:
                    return float(match.group())
    return None

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    
    with st.spinner("جاري معالجة الصورة وقراءة الأرقام الطبية بالطريقة الذكية..."):
        img_np = np.array(image)
        ocr_results = reader.readtext(img_np, detail=0)
        
        ranges = VET_REFERENCE_RANGES[species]
        extracted_data = {}
        for param in ranges.keys():
            extracted_data[param] = extract_param_value(ocr_results, param)
            
    st.success("تمت قراءة البيانات بنجاح! راجع القيم أدناه قبل الطباعة:")
    
    # مراجعة وتعديل القيم لتلافي أخطاء الاهتزاز أثناء التصوير
    final_data = {}
    col1, col2 = st.columns(2)
    for idx, param in enumerate(ranges.keys()):
        current_val = extracted_data[param] if extracted_data[param] is not None else 0.0
        with col1 if idx % 2 == 0 else col2:
            final_data[param] = st.number_input(f"معامل {param}:", value=float(current_val))

    if st.button("🧬 تشغيل التفسير وتجهيز تقرير الطباعة الفاخر"):
        status = {}
        insights = []
        
        for param, val in final_data.items():
            r = ranges[param]
            if val < r["min"]: status[param] = "LOW"
import streamlit as st
import cv2
import numpy as np
import re
import datetime
from PIL import Image
import easyocr
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

# إعداد قارئ النصوص الذكي من الصورة
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

# قاعدة بيانات النطاقات الطبيعية الكاملة والمحدثة (بما فيها الدواجن)
VET_REFERENCE_RANGES = {
    "Dog (كلب)": {
        "RBC": {"min": 5.5, "max": 8.5, "unit": "x10^6/µL"},
        "Hb": {"min": 12.0, "max": 18.0, "unit": "g/dL"},
        "PCV": {"min": 37.0, "max": 55.0, "unit": "%"},
        "WBC": {"min": 6.0, "max": 17.0, "unit": "x10^3/µL"},
        "PLT": {"min": 200, "max": 500, "unit": "x10^3/µL"}
    },
    "Cat (قط)": {
        "RBC": {"min": 6.0, "max": 10.0, "unit": "x10^6/µL"},
        "Hb": {"min": 8.0, "max": 15.0, "unit": "g/dL"},
        "PCV": {"min": 24.0, "max": 45.0, "unit": "%"},
        "WBC": {"min": 5.5, "max": 19.5, "unit": "x10^3/µL"},
        "PLT": {"min": 300, "max": 800, "unit": "x10^3/µL"}
    },
    "Poultry (دواجن/دجاج)": {
        "RBC": {"min": 2.5, "max": 3.5, "unit": "x10^6/µL"},
        "Hb": {"min": 7.0, "max": 13.0, "unit": "g/dL"},
        "PCV": {"min": 22.0, "max": 35.0, "unit": "%"},
        "WBC": {"min": 12.0, "max": 30.0, "unit": "x10^3/µL"},
        "PLT": {"min": 20.0, "max": 40.0, "unit": "x10^3/µL"}
    }
}

# إعدادات واجهة الموبايل عبر Streamlit
st.set_page_config(page_title="عيادة الحي البيطرية", page_icon="🐾")
st.title("🐾 عيادة الحي البيطرية")
st.subheader("نظام المسح الضوئي والتفسير التلقائي لـ CBC")

# القائمة الجانبية لإدخال بيانات التقرير المطبوع
st.sidebar.header("📋 بيانات المراجع والحالة")
owner_name = st.sidebar.text_input("اسم المربي:", "عميل محترم")
animal_id = st.sidebar.text_input("اسم/رقم الحيوان:", "غير محدد")
species = st.sidebar.selectbox("الفصيلة المستهدفة:", list(VET_REFERENCE_RANGES.keys()))

# التقاط الصورة مباشرة بكاميرا الموبايل
uploaded_file = st.camera_input("التقط صورة واضحة ومستقيمة لورقة تحليل الـ CBC")

def extract_param_value(text_list, param_name):
    for i, text in enumerate(text_list):
        if re.search(r'\b' + param_name + r'\b', text, re.IGNORECASE):
            for j in range(i+1, min(i+4, len(text_list))):
                next_text = text_list[j].replace(' ', '')
                match = re.search(r'[-+]?\d*\.\d+|\d+', next_text)
                if match:
                    return float(match.group())
    return None

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    
    with st.spinner("جاري معالجة الصورة وقراءة الأرقام الطبية بالطريقة الذكية..."):
        img_np = np.array(image)
        ocr_results = reader.readtext(img_np, detail=0)
        
        ranges = VET_REFERENCE_RANGES[species]
        extracted_data = {}
        for param in ranges.keys():
            extracted_data[param] = extract_param_value(ocr_results, param)
            
    st.success("تمت قراءة البيانات بنجاح! راجع القيم أدناه قبل الطباعة:")
    
    # مراجعة وتعديل القيم لتلافي أخطاء الاهتزاز أثناء التصوير
    final_data = {}
    col1, col2 = st.columns(2)
    for idx, param in enumerate(ranges.keys()):
        current_val = extracted_data[param] if extracted_data[param] is not None else 0.0
        with col1 if idx % 2 == 0 else col2:
            final_data[param] = st.number_input(f"معامل {param}:", value=float(current_val))

    if st.button("🧬 تشغيل التفسير وتجهيز تقرير الطباعة الفاخر"):
        status = {}
        insights = []
        
        for param, val in final_data.items():
            r = ranges[param]
            if val < r["min"]: status[param] = "LOW"
import streamlit as st
import cv2
import numpy as np
import re
import datetime
from PIL import Image
import easyocr
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

# إعداد قارئ النصوص الذكي من الصورة
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

# قاعدة بيانات النطاقات الطبيعية الكاملة والمحدثة (بما فيها الدواجن)
VET_REFERENCE_RANGES = {
    "Dog (كلب)": {
        "RBC": {"min": 5.5, "max": 8.5, "unit": "x10^6/µL"},
        "Hb": {"min": 12.0, "max": 18.0, "unit": "g/dL"},
        "PCV": {"min": 37.0, "max": 55.0, "unit": "%"},
        "WBC": {"min": 6.0, "max": 17.0, "unit": "x10^3/µL"},
        "PLT": {"min": 200, "max": 500, "unit": "x10^3/µL"}
    },
    "Cat (قط)": {
        "RBC": {"min": 6.0, "max": 10.0, "unit": "x10^6/µL"},
        "Hb": {"min": 8.0, "max": 15.0, "unit": "g/dL"},
        "PCV": {"min": 24.0, "max": 45.0, "unit": "%"},
        "WBC": {"min": 5.5, "max": 19.5, "unit": "x10^3/µL"},
        "PLT": {"min": 300, "max": 800, "unit": "x10^3/µL"}
    },
    "Poultry (دواجن/دجاج)": {
        "RBC": {"min": 2.5, "max": 3.5, "unit": "x10^6/µL"},
        "Hb": {"min": 7.0, "max": 13.0, "unit": "g/dL"},
        "PCV": {"min": 22.0, "max": 35.0, "unit": "%"},
        "WBC": {"min": 12.0, "max": 30.0, "unit": "x10^3/µL"},
        "PLT": {"min": 20.0, "max": 40.0, "unit": "x10^3/µL"}
    }
}

# إعدادات واجهة الموبايل عبر Streamlit
st.set_page_config(page_title="عيادة الحي البيطرية", page_icon="🐾")
st.title("🐾 عيادة الحي البيطرية")
st.subheader("نظام المسح الضوئي والتفسير التلقائي لـ CBC")

# القائمة الجانبية لإدخال بيانات التقرير المطبوع
st.sidebar.header("📋 بيانات المراجع والحالة")
owner_name = st.sidebar.text_input("اسم المربي:", "عميل محترم")
animal_id = st.sidebar.text_input("اسم/رقم الحيوان:", "غير محدد")
species = st.sidebar.selectbox("الفصيلة المستهدفة:", list(VET_REFERENCE_RANGES.keys()))

# التقاط الصورة مباشرة بكاميرا الموبايل
uploaded_file = st.camera_input("التقط صورة واضحة ومستقيمة لورقة تحليل الـ CBC")

def extract_param_value(text_list, param_name):
    for i, text in enumerate(text_list):
        if re.search(r'\b' + param_name + r'\b', text, re.IGNORECASE):
            for j in range(i+1, min(i+4, len(text_list))):
                next_text = text_list[j].replace(' ', '')
                match = re.search(r'[-+]?\d*\.\d+|\d+', next_text)
                if match:
                    return float(match.group())
    return None

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    
    with st.spinner("جاري معالجة الصورة وقراءة الأرقام الطبية بالطريقة الذكية..."):
        img_np = np.array(image)
        ocr_results = reader.readtext(img_np, detail=0)
        
        ranges = VET_REFERENCE_RANGES[species]
        extracted_data = {}
        for param in ranges.keys():
            extracted_data[param] = extract_param_value(ocr_results, param)
            
    st.success("تمت قراءة البيانات بنجاح! راجع القيم أدناه قبل الطباعة:")
    
    # مراجعة وتعديل القيم لتلافي أخطاء الاهتزاز أثناء التصوير
    final_data = {}
    col1, col2 = st.columns(2)
    for idx, param in enumerate(ranges.keys()):
        current_val = extracted_data[param] if extracted_data[param] is not None else 0.0
        with col1 if idx % 2 == 0 else col2:
            final_data[param] = st.number_input(f"معامل {param}:", value=float(current_val))

    if st.button("🧬 تشغيل التفسير وتجهيز تقرير الطباعة الفاخر"):
        status = {}
        insights = []
        
        for param, val in final_data.items():
            r = ranges[param]
            if val < r["min"]: status[param] = "LOW"
elif val > r["max"]: status[param] = "HIGH"
else: status[param] = "NORMAL"            
        # خوارزمية التفسير الإكلينيكي الذكي لعيادة الحي (حسب الفصيلة ثدييات أم طيور)
        if species == "Poultry (دواجن/دجاج)":
            if status.get("RBC") == "LOW" or status.get("PCV") == "LOW":
                insights.append("• فقر دم في الدواجن (Avian Anemia): قد يشير إلى فيروس فقر دم الدجاج (CAV)، أو إصابة طفيلية حادة كـ (الكوكسيديا الشديدة أو الفاش الأحمر).")
            if status.get("WBC") == "HIGH":
                insights.append("• ارتفاع خلايا الدم البيضاء: مؤشر استجابة مناعية قوية لعدوى بكتيرية حادة (مثل كوليرا الطيور أو السالمونيلا) أو أمراض فيروسية تنفسية.")
        else:
            # تفسير الثدييات (الكلاب والقطط)
            if status.get("RBC") == "LOW" or status.get("Hb") == "LOW":
                insights.append("• مؤشر فقر دم (Anemia): انخفاض في السلسلة الحمراء، يرجى مطابقة الثوابت الخلوية لمعرفة السبب.")
            elif status.get("RBC") == "HIGH" or status.get("PCV") == "HIGH":
                insights.append("• اشتباه تجفاف (Dehydration): ارتفاع مؤشرات الكريات الحمراء غالباً نتيجة نقص السوائل الشديد.")
                
            if status.get("WBC") == "HIGH":
                insights.append("• استجابة التهابية (Leukocytosis): ارتفاع البيضاء يشير إلى عدوى بكتيرية أو التهاب نسيجي نشط.")
            elif status.get("WBC") == "LOW":
                insights.append("• نقص مناعي حاد (Leukopenia): خطر إصابة فيروسية حادة تستدعي العزل الفوري مثل (بارفو الكلاب أو طاعون القطط).")
                
            if status.get("PLT") == "LOW":
                insights.append("• نقص صفائح (Thrombocytopenia): خطر نزف، قد يرجع لأمراض الدم المنقولة بالقراد كـ (الإيرليخيا) أو تدمير مناعي ذاتي.")

        if not insights:
            insights.append("• جميع المؤشرات تقع ضمن الحدود الطبيعية لهذه الفصيلة.")

        # عرض التقرير الفوري على الشاشة
        st.write("---")
        st.markdown("### 📄 المعاينة قبل الطباعة (Al-Hay Clinic)")
        for ins in insights:
            st.write(ins)
            
        # إنشاء ملف الـ PDF في الذاكرة للتحميل المباشر
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('T1', fontName='Helvetica-Bold', fontSize=20, textColor=colors.HexColor('#c0392b'), spaceAfter=12, alignment=1)
        sub_style = ParagraphStyle('S1', fontName='Helvetica', fontSize=11, spaceAfter=6)
        ins_style = ParagraphStyle('I1', fontName='Helvetica', fontSize=11, textColor=colors.HexColor('#2c3e50'), spaceAfter=5, leading=14)
        
        story = []
        story.append(Paragraph("AL-HAY VETERINARY CLINIC", title_style))
        story.append(Paragraph(f"<b>Date:</b> {datetime.date.today().strftime('%Y-%m-%d')} | <b>Owner:</b> {owner_name} | <b>Animal ID:</b> {animal_id}", sub_style))
        story.append(Paragraph(f"<b>Species:</b> {species}", sub_style))
        story.append(Spacer(1, 15))
        
        table_data = [["Parameter", "Result", "Unit", "Status", "Reference Interval"]]
        for p, v in final_data.items():
            r = ranges[p]
            table_data.append([p, str(v), r['unit'], status[p], f"{r['min']} - {r['max']}"])
            
        t = Table(table_data, colWidths=[90, 95, 90, 85, 120])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#c0392b')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f9fa')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
[7/13/2026 10:11 PM] ثائر وداد: import streamlit as st
import cv2
import numpy as np
import re
import datetime
from PIL import Image
import easyocr
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

# إعداد قارئ النصوص الذكي من الصورة
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

# قاعدة بيانات النطاقات الطبيعية الكاملة والمحدثة (بما فيها الدواجن)
VET_REFERENCE_RANGES = {
    "Dog (كلب)": {
        "RBC": {"min": 5.5, "max": 8.5, "unit": "x10^6/µL"},
        "Hb": {"min": 12.0, "max": 18.0, "unit": "g/dL"},
        "PCV": {"min": 37.0, "max": 55.0, "unit": "%"},
        "WBC": {"min": 6.0, "max": 17.0, "unit": "x10^3/µL"},
        "PLT": {"min": 200, "max": 500, "unit": "x10^3/µL"}
    },
    "Cat (قط)": {
        "RBC": {"min": 6.0, "max": 10.0, "unit": "x10^6/µL"},
        "Hb": {"min": 8.0, "max": 15.0, "unit": "g/dL"},
        "PCV": {"min": 24.0, "max": 45.0, "unit": "%"},
        "WBC": {"min": 5.5, "max": 19.5, "unit": "x10^3/µL"},
        "PLT": {"min": 300, "max": 800, "unit": "x10^3/µL"}
    },
    "Poultry (دواجن/دجاج)": {
        "RBC": {"min": 2.5, "max": 3.5, "unit": "x10^6/µL"},
        "Hb": {"min": 7.0, "max": 13.0, "unit": "g/dL"},
        "PCV": {"min": 22.0, "max": 35.0, "unit": "%"},
        "WBC": {"min": 12.0, "max": 30.0, "unit": "x10^3/µL"},
        "PLT": {"min": 20.0, "max": 40.0, "unit": "x10^3/µL"}
    }
}

# إعدادات واجهة الموبايل عبر Streamlit
st.set_page_config(page_title="عيادة الحي البيطرية", page_icon="🐾")
st.title("🐾 عيادة الحي البيطرية")
st.subheader("نظام المسح الضوئي والتفسير التلقائي لـ CBC")

# القائمة الجانبية لإدخال بيانات التقرير المطبوع
st.sidebar.header("📋 بيانات المراجع والحالة")
owner_name = st.sidebar.text_input("اسم المربي:", "عميل محترم")
animal_id = st.sidebar.text_input("اسم/رقم الحيوان:", "غير محدد")
species = st.sidebar.selectbox("الفصيلة المستهدفة:", list(VET_REFERENCE_RANGES.keys()))

# التقاط الصورة مباشرة بكاميرا الموبايل
uploaded_file = st.camera_input("التقط صورة واضحة ومستقيمة لورقة تحليل الـ CBC")

def extract_param_value(text_list, param_name):
    for i, text in enumerate(text_list):
        if re.search(r'\b' + param_name + r'\b', text, re.IGNORECASE):
            for j in range(i+1, min(i+4, len(text_list))):
                next_text = text_list[j].replace(' ', '')
                match = re.search(r'[-+]?\d*\.\d+|\d+', next_text)
                if match:
                    return float(match.group())
    return None

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    
    with st.spinner("جاري معالجة الصورة وقراءة الأرقام الطبية بالطريقة الذكية..."):
        img_np = np.array(image)
        ocr_results = reader.readtext(img_np, detail=0)
        
        ranges = VET_REFERENCE_RANGES[species]
        extracted_data = {}
        for param in ranges.keys():
            extracted_data[param] = extract_param_value(ocr_results, param)
            
    st.success("تمت قراءة البيانات بنجاح! راجع القيم أدناه قبل الطباعة:")
    
    # مراجعة وتعديل القيم لتلافي أخطاء الاهتزاز أثناء التصوير
    final_data = {}
    col1, col2 = st.columns(2)
    for idx, param in enumerate(ranges.keys()):
        current_val = extracted_data[param] if extracted_data[param] is not None else 0.0
        with col1 if idx % 2 == 0 else col2:
            final_data[param] = st.number_input(f"معامل {param}:", value=float(current_val))

    if st.button("🧬 تشغيل التفسير وتجهيز تقرير الطباعة الفاخر"):
        status = {}
        insights = []
        
        for param, val in final_data.items():
            r = ranges[param]
            if val < r["min"]: status[param] = "LOW"
[7/13/2026 10:11 PM] ثائر وداد: story.append(Paragraph("<b>CLINICAL INTERPRETATION:</b>", ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#27ae60'))))
        for ins in insights:
            story.append(Paragraph(ins, ins_style))
            
        doc.build(story)
        pdf_data = pdf_buffer.getvalue()
        
        st.download_button(
            label="⬇️ تحميل ملف PDF جاهز للطباعة بدقة عالية",
            data=pdf_data,
            file_name=f"AlHay_Clinic_Report_{animal_id}.pdf",
            mime="application/pdf"
        )
