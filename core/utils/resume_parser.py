import re

import docx
import pypdf


def extract_text_from_pdf(file_obj):
    text = ""
    try:
        reader = pypdf.PdfReader(file_obj)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text


def extract_text_from_docx(file_obj):
    text = ""
    try:
        doc = docx.Document(file_obj)
        for paragraph in doc.paragraphs:
            if paragraph.text:
                text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX: {e}")
    return text


def clean_resume_text(text):
    if not text:
        return ""

    # 1. Fix letter-spaced fonts (e.g. "A L I C E" -> "ALICE", "L o r e m" -> "Lorem")
    # Finds single isolated letters separated by spaces and merges them
    text = re.sub(r"(?<=\b[A-Za-z]) (?=[A-Za-z]\b)", "", text)

    # 2. Replace tabs, carriage returns, and control characters
    text = re.sub(r"[\r\t]", " ", text)

    # 3. Collapse multiple newlines into single line breaks
    text = re.sub(r"\n+", "\n", text)

    # 4. Filter non-ASCII characters / noise
    text = re.sub(r"[^\x00-\x7F]+", " ", text)

    # 5. Collapse duplicate spaces
    text = re.sub(r" +", " ", text)

    return text.strip()


def parse_resume_file(file_obj):
    filename = file_obj.name.lower()
    raw_text = ""

    if filename.endswith(".pdf"):
        raw_text = extract_text_from_pdf(file_obj)
    elif filename.endswith(".docx") or filename.endswith(".doc"):
        raw_text = extract_text_from_docx(file_obj)
    else:
        raise ValueError("Unsupported file format. Please upload a PDF or DOCX file.")

    return clean_resume_text(raw_text)
