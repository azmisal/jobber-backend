import pdfplumber
import io
from fastapi import HTTPException
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts raw text content safely from an uploaded PDF data stream."""
    raw_text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="The uploaded PDF file appears to be blank or unreadable.")
    return raw_text

def generate_pdf_bytes(resume_data: dict) -> bytes:
    """Compiles structured resume data into a clean, professional downloadable PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom simple styling block
    title_style = ParagraphStyle('ResumeTitle', parent=styles['Heading1'], spaceAfter=10, fontSize=24)
    heading_style = ParagraphStyle('ResumeHeading', parent=styles['Heading2'], spaceBefore=12, spaceAfter=6, fontSize=14)
    body_style = ParagraphStyle('ResumeBody', parent=styles['Normal'], spaceAfter=6, fontSize=10, leading=14)
    bullet_style = ParagraphStyle('ResumeBullet', parent=styles['Normal'], leftIndent=15, spaceAfter=4, fontSize=10, leading=14)
    
    story = []
    
    # 1. Summary
    story.append(Paragraph("Professional Summary", title_style))
    story.append(Paragraph(resume_data.get("summary", ""), body_style))
    story.append(Spacer(1, 10))
    
    # 2. Skills
    story.append(Paragraph("Technical Core Skills", heading_style))
    story.append(Paragraph(", ".join(resume_data.get("skills", [])), body_style))
    story.append(Spacer(1, 10))
    
    # 3. Work Experience
    story.append(Paragraph("Professional Experience", heading_style))
    for exp in resume_data.get("experience", []):
        story.append(Paragraph(f"<b>{exp.get('role')}</b> at {exp.get('company')} ({exp.get('duration')})", body_style))
        for bullet in exp.get("bullets", []):
            story.append(Paragraph(f"• {bullet}", bullet_style))
        story.append(Spacer(1, 4))
        
    # 4. Education
    story.append(Paragraph("Education", heading_style))
    for edu in resume_data.get("education", []):
        story.append(Paragraph(f"• {edu}", bullet_style))
        
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()