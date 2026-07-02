import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_pdf(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    c.drawString(100, height - 80, "Niharika Sen")
    c.drawString(100, height - 100, "Email: niharika.sen@example.com")
    c.drawString(100, height - 120, "Phone: +91 9876543210")
    c.drawString(100, height - 140, "Location: Bangalore, India")
    
    c.drawString(100, height - 180, "Objective:")
    c.drawString(100, height - 200, "To obtain a challenging role as a Software Engineer where I can apply my skills.")
    
    c.drawString(100, height - 240, "Education:")
    c.drawString(100, height - 260, "B.Tech in Computer Science and Engineering - XYZ University (CGPA: 8.5/10)")
    
    c.drawString(100, height - 300, "Experience & Projects:")
    c.drawString(100, height - 320, "- Full Stack Web Application (React, Node.js): Built a responsive online bookstore.")
    c.drawString(100, height - 340, "  Implemented user authentication, search functionality, and a shopping cart.")
    
    c.drawString(100, height - 380, "Skills:")
    c.drawString(100, height - 400, "Java, Python, Javascript, React, SQL, HTML/CSS, Git")
    
    c.save()

if __name__ == "__main__":
    create_pdf(filename="test_resume.pdf")
    print("test_resume.pdf generated successfully.")
