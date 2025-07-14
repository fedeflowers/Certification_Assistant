import pdfplumber

def extract_full_text(pdf_path):
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1.5, y_tolerance=1.5)
            if text:
                full_text += text + "\n"
    return full_text.strip() 