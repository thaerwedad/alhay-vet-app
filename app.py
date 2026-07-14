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

# المسميات البديلة الشائعة في المختبرات الطبية لضمان دقة القراءة 100%
PARAM_ALIASES = {
    "RBC": ["RBC", "Red Blood", "R.B.C", "Erythrocytes", "Erythrocyte"],
    "Hb": ["Hb", "Hgb", "Hemoglobin", "HGB", "HEMOGLOBIN", "HGB (g/dL)"],
    "PCV": ["PCV", "Hct", "Hematocrit", "Packed Cell", "HCT", "Hematocrit (PCV)"],
    "WBC": ["WBC", "White Blood", "W.B.C", "Leukocytes", "Leukocyte"],
    "PLT": ["PLT", "Platelet", "Platelets", "Thrombocytes", "Thrombocyte"]
}

VET_REFERENCE_RANGES = {
    "Dog": {
        "RBC": {"min": 5.5, "max": 8.5, "unit": "x10^6/µL"},
        "Hb": {"min": 12.0, "max": 18.0, "unit": "g/dL"},
        "PCV": {"min": 37.0, "max": 55.0, "unit": "%"},
        "WBC": {"min": 6.0, "max": 17.0, "unit": "x10^3/µL"},
        "PLT": {"min": 200, "max": 500, "unit": "x10^3/µL"}
    },
    "Cat": {
        "RBC": {"min": 6.0, "max": 10.0, "unit": "x10^6/µL"},
        "Hb": {"min": 8.0, "max": 15.0, "unit": "g/dL"},
        "PCV": {"min": 24.0, "max": 45.0, "unit": "%"},
        "WBC": {"min": 5.5, "max": 19.5, "unit": "x10^3/µL"},
        "PLT": {"min": 300, "max": 800, "unit": "x10^3/µL"}
    },
    "Poultry": {
        "RBC": {"min": 2.5, "max": 3.5, "unit": "x10^6/µL"},
        "Hb": {"min": 7.0, "max": 13.0, "unit": "g/dL"},
        "PCV": {"min": 22.0, "max": 35.0, "unit": "%"},
        "WBC": {"min": 12.0, "max": 30.0, "unit": "x10^3/µL"},
        "PLT": {"min": 20.0, "max": 40.0, "unit": "x10^3/µL"}
    }
}

st.set_page_config(
    page_title="Al-Hay Veterinary Clinic", 
    page_icon="🐾",
    layout="wide"
)
st.title("🐾 Al-Hay Veterinary Clinic")
st.subheader("Professional Automated CBC Interpretation System")

st.sidebar.header("📋 Case Information")
owner_name = st.sidebar.text_input("Owner Name / اسم المربّي:", "Client")
animal_id = st.sidebar.text_input("Animal ID / رقم الحيوان:", "None")
species = st.sidebar.selectbox(
    "Species / الفصيلة:", 
    list(VET_REFERENCE_RANGES.keys())
)

input_method = st.radio(
    "Choose Input Method / اختر طريقة الإدخال:",
    ["📸 Use Camera (استخدام الكاميرا)", "📁 Upload from Gallery (رفع من الألبوم)"]
)

uploaded_file = None
if "Camera" in input_method:
    uploaded_file = st.camera_input("Capture CBC Report Image")
else:
    uploaded_file = st.file_uploader(
        "Upload CBC Image", 
        type=["jpg", "jpeg", "png"]
    )

def extract_param_value_robust(text_list, param_name):
    aliases = PARAM_ALIASES.get(param_name, [param_name])
    for i, text in enumerate(text_list):
        cleaned_text = text.replace(':', '').replace('-', '').strip()
        # البحث عن الاسم أو أي من مرادفاته الطبية المعتمدة
        if any(re.search(r'\b' + re.escape(alias) + r'\b', cleaned_text, re.IGNORECASE) for alias in aliases):
            # البحث في النصوص الـ 4 التالية للعثور على أقرب رقم عشري أو صحيح
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

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Selected CBC Report", width=400)
    
    with st.spinner("Processing image and scanning data..."):
        img_np = np.array(image)
        ocr_results = reader.readtext(img_np, detail=0)
        
        ranges = VET_REFERENCE_RANGES[species]
        extracted_data = {}
        for param in ranges.keys():
            extracted_data[param] = extract_param_value_robust(ocr_results, param)
            
    st.info("💡 نصيحة: إذا لم يتم قراءة أي قيمة بشكل صحيح، يمكنك تعديلها بيدك من الحقول أدناه مباشرة قبل إصدار التقرير!")
    
    final_data = {}
    col1, col2 = st.columns(2)
    for idx, param in enumerate(ranges.keys()):
        current_val = (
            extracted_data[param] 
            if extracted_data[param] is not None 
            else 0.0
        )
        with col1 if idx % 2 == 0 else col2:
            final_data[param] = st.number_input(
                f"{param} ({ranges[param]['unit']}):", 
                value=float(current_val),
                step=0.1
            )

    if st.button("🧬 Run Deep Clinical Interpretation & Generate PDF"):
        status = {}
        insights = []
        
        for param, val in final_data.items():
            r = ranges[param]
            if val < r["min"]:
                status[param] = "LOW"
            elif val > r["max"]:
                status[param] = "HIGH"
            else:
                status[param] = "NORMAL"
        
        # تحليلات طبية معقدة ومفصلة تفاعلية بحسب فصيلة الحيوان
        if species == "Dog":
            if status.get("RBC") == "LOW" or status.get("Hb") == "LOW" or status.get("PCV") == "LOW":
                insights.append("• ANEMIA CONFIRMED: Low Erythron parameters detected. Regenerative anemia is suspected if PCV is acutely dropped; consider checking reticulocytes. Rule out hemorrhage, hemolysis (e.g., Babesia Canis/Anaplasma), or chronic organ disease.")
            elif status.get("RBC") == "HIGH" or status.get("PCV") == "HIGH":
                insights.append("• ERYTHROCYTOSIS / DEHYDRATION: High red blood cell parameters. Most commonly relative due to severe dehydration/hemoconcentration. Immediate fluid therapy (IV/SubQ) is recommended to protect renal function.")
            
            if status.get("WBC") == "HIGH":
                insights.append("• LEUKOCYTOSIS / INFLAMMATION: Elevated WBC indicates an active systemic inflammatory response, bacterial infection (e.g., Pyometra, Pneumonia), or severe tissue trauma. Recommended: Perform a differential count (neutrophils/lymphocytes) and broad-spectrum antibiotics.")
            elif status.get("WBC") == "LOW":
                insights.append("• LEUKOPENIA / RISK OF VIRAL INFECTION: Low WBC is highly suggestive of viral bone marrow suppression (e.g., Canine Parvovirus, Distemper) or severe septic shock. Implement immediate isolation protocols and immune support.")
                
            if status.get("PLT") == "LOW":
                insights.append("• THROMBOCYTOPENIA: Bleeding risk identified. High correlation with tick-borne vector diseases (Ehrlichia Canis, Anaplasma platys) or Immune-Mediated Thrombocytopenia (IMTP). Avoid invasive procedures and check clotting times.")

        elif species == "Cat":
            if status.get("RBC") == "LOW" or status.get("Hb") == "LOW" or status.get("PCV") == "LOW":
                insights.append("• FELINE ANEMIA DIAGNOSIS: Marked reduction in oxygen-carrying capacity. Strongly recommend testing for retroviruses (FeLV/FIV) or Mycoplasma hemofelis (Feline Infectious Anemia). Monitor closely for pale mucous membranes and dyspnea.")
            elif status.get("RBC") == "HIGH" or status.get("PCV") == "HIGH":
                insights.append("• FELINE POLYCYTHEMIA: High risk of arterial thromboembolism if blood viscosity is elevated. Check hydration status and cardiovascular health.")
                
            if status.get("WBC") == "HIGH":
                insights.append("• FELINE LEUKOCYTOSIS: Active immune reaction. Could indicate systemic abscesses, FIP (Feline Infectious Peritonitis), or severe dental disease.")
            elif status.get("WBC") == "LOW":
                insights.append("• FELINE LEUKOPENIA: Critically low white blood cells. Frequently associated with Feline Panleukopenia Virus (FPV) or chronic FIV/FeLV infections. Guarded prognosis; require immediate aggressive therapy.")
                
            if status.get("PLT") == "LOW":
                insights.append("• THROMBOCYTOPENIA (FELINE): Note: Feline platelets easily clump during collection. If clinically healthy, rule out 'pseudothrombocytopenia' via blood smear evaluation. Otherwise, suspect infectious or immune etiology.")

        elif species == "Poultry":
            if status.get("RBC") == "LOW" or status.get("PCV") == "LOW":
                insights.append("• AVIAN ANEMIA: Highly suspect Chicken Infectious Anemia (CAV), severe Coccidiosis, or heavy external parasite infestation (Dermanyssus gallinae / Red Mites). Verify flock history and check flock biosecurity.")
            if status.get("WBC") == "HIGH":
                insights.append("• AVIAN LEUKOCYTOSIS: Severe systemic immune response. Often linked to acute bacterial outbreaks (Fowl Cholera, Colibacillosis) or viral infections. Quarantine affected birds immediately.")

        if not insights:
            insights.append("• NORMAL REPORT: All analyzed parameters fall within the physiological reference intervals for this species.")

        st.write("---")
        st.markdown("### 📄 Case Clinical Interpretation Preview:")
        for ins in insights:
            st.markdown(ins)
            
        # إنشاء ملف الـ PDF الاحترافي
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        
        # تجهيز التنسيقات والخطوط
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'T1', 
            fontName='Helvetica-Bold', 
            fontSize=22, 
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
        ins_header_style = ParagraphStyle(
            'H2', 
            fontName='Helvetica-Bold', 
            fontSize=13, 
            textColor=colors.HexColor('#27ae60'),
            spaceBefore=15,
            spaceAfter=10
        )
        ins_style = ParagraphStyle(
            'I1', 
            fontName='Helvetica', 
            fontSize=11, 
            textColor=colors.HexColor('#2c3e50'), 
            spaceAfter=8, 
            leading=15
        )
        
        story = []
        # الهيدر الخاص بالعيادة
        story.append(Paragraph("AL-HAY VETERINARY CLINIC", title_style))
        story.append(
            Paragraph(
                f"<b>Date:</b> {datetime.date.today().strftime('%Y-%m-%d')} | "
                f"<b>Owner Name:</b> {owner_name} | "
                f"<b>Animal ID:</b> {animal_id}", 
                sub_style
            )
        )
        story.append(Paragraph(f"<b>Species Analyzed:</b> {species}", sub_style))
        story.append(Spacer(1, 15))
        
        # جدول النتائج الرئيسي
        table_data = [
            ["Parameter", "Observed Result", "Unit", "Clinical Status", "Reference Range"]
        ]
        for p, v in final_data.items():
            r = ranges[p]
            table_data.append(
                [p, f"{v:.1f}", r['unit'], status[p], f"{r['min']} - {r['max']}"]
            )
            
        t = Table(table_data, colWidths=[110, 110, 80, 100, 120])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#c0392b')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bdc3c7')),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f9fa')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f2f4f4')]),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        
        # قسم التفسير الطبي المطور
        story.append(Paragraph("DETAILED CLINICAL INTERPRETATION & RECOMMENDATIONS:", ins_header_style))
        for ins in insights:
            story.append(Paragraph(ins, ins_style))
            
        doc.build(story)
        pdf_data = pdf_buffer.getvalue()
        
        st.download_button(
            label="⬇️ Download Full Veterinary PDF Report",
            data=pdf_data,
            file_name=f"AlHay_CBC_Report_{animal_id}.pdf",
            mime="application/pdf"
        )
