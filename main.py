from fpdf import FPDF

def generate_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Hello from GitHub Actions!", ln=True)
    pdf.output("output.pdf")

if __name__ == "__main__":
    generate_pdf()
