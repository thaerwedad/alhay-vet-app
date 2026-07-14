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
    page_icon="🐾"
)
st.title("🐾 Al-Hay Veterinary Clinic")
st.subheader("Automated CBC Interpretation System")

st.sidebar.header("📋 Case Information")
owner_name = st.sidebar.text_input("Owner Name:", "Client")
animal_id = st.sidebar.text_input("Animal ID:", "None")
species = st.sidebar.selectbox(
    "Species:", 
    list(VET_REFERENCE_RANGES.keys())
)

# زر موحد لالتقاط صورة بالكاميرا أو اختيارها من الاستوديو
uploaded_file = st.file_uploader(
    "📸 Take a Photo or Upload CBC Image", 
    type=["jpg", "jpeg", "png"]
)

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
    st.image(
        image, 
        caption="Selected CBC Report", 
        use_container_width=True
    )
    
    with st.spinner("Processing image and scanning data..."):
        img_np = np.array(image)
        ocr_results = reader.readtext(img_np, detail=0)
        
        ranges = VET_REFERENCE_RANGES[species]
        extracted_data = {}
        for param in ranges.keys():
            extracted_data[param] = extract_param_value(
                ocr_results, 
                param
            )
            
    st.success("Data read successfully! Please verify values:")
    
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
                f"{param}:", 
                value=float(current_val)
            )

    if st.button("🧬 Run Clinical Interpretation & Generate PDF"):
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
            
        if species == "Poultry":
            if status.get("RBC") == "LOW" or status.get("PCV") == "LOW":
                insights.append(
                    "- Suspect Avian Anemia (CAV, Coccidiosis, Mites)."
                )
            if status.get("WBC") == "HIGH":
                insights.append(
                    "- Leukocytosis: Severe immune response."
                )
        else:
            if status.get("RBC") == "LOW" or status.get("Hb") == "LOW":
                insights.append("- Anemia Indicated: Low RBC parameters.")
            elif status.get("RBC") == "HIGH" or status.get("PCV") == "HIGH":
                insights.append("- Suspect Dehydration: Elevated erythron.")
                
            if status.get("WBC") == "HIGH":
                insights.append("- Leukocytosis: Active inflammation/infection.")
            elif status.get("WBC") == "LOW":
                insights.append("- Leukopenia: High risk of viral infection.")
                
            if status.get("PLT") == "LOW":
                insights.append("- Thrombocytopenia: Bleeding risk.")

        if not insights:
            insights.append("- All parameters are within normal intervals.")

        st.write("---")
        st.markdown("### 📄 Preview (Al-Hay Clinic)")
        for ins in insights:
            st.write(ins)
            
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'T1', 
            fontName='Helvetica-Bold', 
            fontSize=20, 
            textColor=colors.HexColor('#c0392b'), 
            spaceAfter=12, 
            alignment=1
        )
        sub_style = ParagraphStyle(
            'S1', 
            fontName='Helvetica', 
            fontSize=11, 
            spaceAfter=6
        )
        ins_style = ParagraphStyle(
            'I1', 
            fontName='Helvetica', 
            fontSize=11, 
            textColor=colors.HexColor('#2c3e50'), 
            spaceAfter=5, 
            leading=14
        )
        
        story = []
        story.append(Paragraph("AL-HAY VETERINARY CLINIC", title_style))
        story.append(
            Paragraph(
                f"<b>Date:</b> {datetime.date.today().strftime('%Y-%m-%d')} | "
                f"<b>Owner:</b> {owner_name} | "
                f"<b>Animal ID:</b> {animal_id}", 
                sub_style
            )
        )
        story.append(Paragraph(f"<b>Species:</b> {species}", sub_style))
        story.append(Spacer(1, 15))
        
        table_data = [
            ["Parameter", "Result", "Unit", "Status", "Reference Interval"]
        ]
        for p, v in final_data.items():
            r = ranges[p]
            table_data.append(
                [p, str(v), r['unit'], status[p], f"{r['min']} - {r['max']}"]
            )
            
        t = Table(table_data, colWidths=[100, 90, 90, 80, 130])
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
        
        story.append(
            Paragraph(
                "<b>CLINICAL INTERPRETATION:</b>", 
                ParagraphStyle(
                    'H2', 
                    fontName='Helvetica-Bold', 
                    fontSize=12, 
                    textColor=colors.HexColor('#27ae60')
                )
            )
        )
        for ins in insights:
            story.append(Paragraph(ins, ins_style))
            
        doc.build(story)
        pdf_data = pdf_buffer.getvalue()
        
        st.download_button(
            label="⬇️ Download High-Quality Printable PDF",
            data=pdf_data,
            file_name=f"AlHay_Clinic_Report_{animal_id}.pdf",
            mime="application/pdf"
        )
