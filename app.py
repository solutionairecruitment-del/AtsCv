import io
import json
import os
from datetime import datetime

import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from flask import Flask, request, jsonify, g

from db import db, DATABASE_URL
from jwt_auth import require_auth
from models import CandidateProfile as User, Resume
from flask_cors import CORS
from sqlalchemy import text

# Load environment
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "your-shared-secret-with-node")

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 20
}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db.init_app(app)
frontend_url = os.getenv("ALLOWED_ORIGINS")

if frontend_url:
    # Production / deployed: allow only the frontend URL
    CORS(app, resources={
        r"/api/*": {
            "origins": [frontend_url],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    print(f"✅ CORS restricted to frontend: {frontend_url}")
else:
    # Development / local testing: allow all origins
    CORS(app, resources={
        r"/api/*": {
            "origins": ["*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    print("⚠️ CORS unrestricted (local/dev)")
# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)


# Helper functions for text extraction
def extract_text_from_pdf_gemini(pdf_bytes):
    try:
        # Load PDF from bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Convert first page to image (as PNG)
        page = doc.load_page(0)  # First page
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")

        # Send to Gemini Vision
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        prompt = "Extract all resume text from this image (converted from PDF)."
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content([
            prompt,
            image
        ])
        return response.text.strip()

    except Exception as e:
        print("❌ Error processing PDF with Gemini:", e)
        return ""


def extract_text_from_image_gemini(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_prompt = "Extract all resume text from this image."
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content([
            img_prompt,
            image
        ])
        return response.text.strip()
    except Exception as e:
        print("❌ Error processing image with Gemini:", e)
        return ""


# def get_structured_resume_with_feedback(resume_text, job_description):
#     prompt = f"""
# You are an expert resume writing assistant. Based on the following user resume and the job description, provide a structured, ATS-friendly resume and feedback.
#
# Analyze the resume and job description, then return the data in this EXACT JSON format:
#
# {{
#     "name": "Full Name (if found, otherwise empty string)",
#     "email": "email@example.com (if found, otherwise empty string)",
#     "phone": "Phone number (if found, otherwise empty string)",
#     "location": "City, State (if found, otherwise empty string)",
#     "professional_summary": "2-3 sentence professional summary tailored to the job",
#     "skills": [
#         "Skill 1",
#         "Skill 2",
#         "Skill 3"
#     ],
#     "work_experience": [
#         {{
#             "company": "Company Name",
#             "position": "Job Title",
#             "duration": "Start Date - End Date",
#             "location": "City, State",
#             "responsibilities": [
#                 "Responsibility 1 with metrics if available",
#                 "Responsibility 2 with metrics if available"
#             ]
#         }}
#     ],
#     "projects": [
#         {{
#             "title": "Project Name",
#             "technologies": ["Tech1", "Tech2"],
#             "description": "Project description with impact",
#             "link": "github.com/link (if available)"
#         }}
#     ],
#     "education": [
#         {{
#             "degree": "Degree Name",
#             "institution": "School Name",
#             "graduation_year": "Year",
#             "location": "City, State",
#             "relevant_coursework": ["Course1", "Course2"]
#         }}
#     ],
#     "certifications": [
#         {{
#             "name": "Certification Name",
#             "issuer": "Issuing Organization",
#             "date": "Date obtained",
#             "expiry": "Expiry date (if applicable)"
#         }}
#     ],
#     "ats_score": 85,
#     "feedback": [
#         "Feedback point 1: What was improved",
#         "Feedback point 2: What was added",
#         "Feedback point 3: What was missing"
#     ]
# }}
#
# Make sure to:
# 1. Extract and enhance information from the original resume
# 2. Tailor skills and experience to match the job description
# 3. Use action verbs and quantify achievements where possible
# 4. Include relevant keywords from the job description
# 5. Provide constructive feedback on improvements made
# 6. Calculate ATS score (0-100) based on resume's compatibility with the job description
#
# Original Resume:
# {resume_text}
#
# Job Description:
# {job_description}
#
# Return ONLY the JSON response, no additional text.
# """
#
#     try:
#         model_text = genai.GenerativeModel("gemini-2.0-flash-exp")
#         response = model_text.generate_content(prompt)
#         content = response.text.strip()
#
#         # Clean up the response to extract JSON
#         if content.startswith("```json"):
#             content = content[7:-3]
#         elif content.startswith("```"):
#             content = content[3:-3]
#
#         structured_data = json.loads(content)
#         return structured_data
#     except Exception as e:
#         print("❌ Error generating structured resume with Gemini:", e)
#         return {
#             "name": "",
#             "email": "",
#             "phone": "",
#             "location": "",
#             "professional_summary": "",
#             "skills": [],
#             "work_experience": [],
#             "projects": [],
#             "education": [],
#             "certifications": [],
#             "ats_score": 0,
#             "feedback": ["Error generating structured resume"]
#         }


def get_structured_resume_with_feedback(resume_text, job_description):
    prompt = f"""
You are an expert resume writing assistant specializing in creating concise, impactful, ATS-friendly one-page resumes. 

CRITICAL REQUIREMENTS:
- The resume MUST fit on ONE PAGE when formatted
- Prioritize quality over quantity - be selective and impactful
- Each bullet point should be concise yet powerful (1-2 lines max)
- Limit entries to most recent/relevant items only
- Focus on achievements with metrics, not duties

Based on the user's resume and job description, provide a structured resume optimized for ONE PAGE layout.

Return data in this EXACT JSON format:

{{
    "name": "Full Name (if found, otherwise empty string)",
    "email": "email@example.com (if found, otherwise empty string)",
    "phone": "Phone number (if found, otherwise empty string)",
    "location": "City, State (if found, otherwise empty string)",
    "professional_summary": "2-3 impactful sentences (40-60 words max) tailored to the job, highlighting key value proposition",
    "skills": [
        "Skill 1",
        "Skill 2",
        "Skill 3",
        "Skill 4",
        "Skill 5",
        "Skill 6"
    ],
    "work_experience": [
        {{
            "company": "Company Name",
            "position": "Job Title",
            "duration": "Start Date - End Date",
            "location": "City, State",
            "responsibilities": [
                "Achievement-focused bullet with quantifiable impact (1-2 lines)",
                "Another impactful achievement with metrics (1-2 lines)",
                "Third key accomplishment if highly relevant (1-2 lines)"
            ]
        }}
    ],
    "projects": [
        {{
            "title": "Project Name",
            "technologies": ["Tech1", "Tech2", "Tech3"],
            "description": "Concise description focusing on impact and results (1-2 lines max)",
            "link": "github.com/link (if available)"
        }}
    ],
    "education": [
        {{
            "degree": "Degree Name",
            "institution": "School Name",
            "graduation_year": "Year",
            "location": "City, State",
            "relevant_coursework": ["Course1", "Course2", "Course3"]
        }}
    ],
    "certifications": [
        {{
            "name": "Certification Name",
            "issuer": "Issuing Organization",
            "date": "Date obtained",
            "expiry": "Expiry date (if applicable)"
        }}
    ],
    "ats_score": 85,
    "feedback": [
        "Feedback point 1: What was improved or optimized for one-page format",
        "Feedback point 2: What was prioritized/removed and why",
        "Feedback point 3: How content was tailored to job requirements"
    ]
}}

ONE-PAGE OPTIMIZATION GUIDELINES:
1. **Skills**: Include 6-10 most relevant skills only (matching job description keywords)
2. **Work Experience**: 
   - Include only 2-3 most recent/relevant positions
   - 2-3 bullet points per position maximum
   - Each bullet: action verb + achievement + quantifiable result (keep under 2 lines)
3. **Projects**: Include 2-3 most impressive projects only (prioritize those matching job requirements)
4. **Education**: 1-2 entries max; omit irrelevant coursework if space is tight
5. **Certifications**: Include only current, relevant certifications (2-4 max)
6. **Professional Summary**: Must be impactful yet brief (40-60 words)

CONTENT QUALITY RULES:
- Every bullet point must demonstrate impact with metrics when possible
- Use strong action verbs (Led, Architected, Increased, Reduced, Implemented)
- Remove generic responsibilities; focus on achievements
- Tailor content specifically to job description requirements
- Remove outdated or irrelevant information ruthlessly

ATS SCORE CALCULATION:
- Keyword match with job description: 40%
- Quantifiable achievements: 25%
- Relevant skills coverage: 20%
- Format and structure: 15%

Original Resume:
{resume_text}

Job Description:
{job_description}

Return ONLY the JSON response, no additional text. Remember: ONE PAGE is mandatory - be selective and impactful!
"""

    try:
        model_text = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model_text.generate_content(prompt)
        content = response.text.strip()

        # Clean up the response to extract JSON
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]

        structured_data = json.loads(content)
        return structured_data
    except Exception as e:
        print("❌ Error generating structured resume with Gemini:", e)
        return {
            "name": "",
            "email": "",
            "phone": "",
            "location": "",
            "professional_summary": "",
            "skills": [],
            "work_experience": [],
            "projects": [],
            "education": [],
            "certifications": [],
            "ats_score": 0,
            "feedback": ["Error generating structured resume"]
        }

def get_or_create_user(email, username):
    """Get existing user or create new one"""
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, username=username, github_username="")
        db.session.add(user)
        db.session.commit()
    return user


def handle_json_data(data):
    """Handle JSON data for both PostgreSQL and SQLite"""
    if isinstance(data, str) and 'postgresql' not in DATABASE_URL:
        try:
            return json.loads(data)
        except:
            return data
    return data


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413


# Routes
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "status": "healthy",
        "service": "Resume Generator API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return jsonify({
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route('/api/generate-resume', methods=['POST'])
@require_auth
def generate_resume():
    try:
        # Check if file is present
        if 'resume_file' not in request.files:
            return jsonify({"error": "No resume file provided"}), 400

        file = request.files['resume_file']
        job_description = request.form.get('job_description')

        if not file or file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if not job_description:
            return jsonify({"error": "Job description is required"}), 400

        # Validate file type
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({"error": "Invalid file type. Only PDF, PNG, JPG, JPEG allowed"}), 400

        # Read file content
        file_bytes = file.read()
        file_type = file.content_type

        # Extract text from file
        if file_type == "application/pdf":
            resume_text = extract_text_from_pdf_gemini(file_bytes)
        else:
            resume_text = extract_text_from_image_gemini(file_bytes)

        if not resume_text:
            return jsonify({"error": "No text found in the uploaded file"}), 400

        # Generate structured resume data with ATS score (FULL DATA - store everything)
        structured_data = get_structured_resume_with_feedback(resume_text, job_description)

        if not structured_data or "feedback" not in structured_data:
            return jsonify({"error": "Failed to generate structured resume"}), 500

        # Get or create user
        user = get_or_create_user(g.user_email, g.user_name)

        # Prepare data for storage (convert to JSON string for SQLite)
        resume_data = structured_data
        if 'postgresql' not in DATABASE_URL:
            resume_data = json.dumps(structured_data)

        # Save resume to database (FULL DATA)
        resume = Resume(
            profile_id=user.id,
            original_resume_text=resume_text,
            structured_resume_data=resume_data,
            job_description=job_description
        )

        db.session.add(resume)
        db.session.commit()

        # Return basic response with resume_id for frontend to fetch with payment status
        return jsonify({
            "success": True,
            "message": "Resume generated successfully",
            "resume_id": resume.id,
            "preview": {
                "name": structured_data.get("name", ""),
                "ats_score": structured_data.get("ats_score", 0)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error in generate_resume: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# Modified get resume route with payment toggle
@app.route('/api/resume/<int:resume_id>', methods=['POST'])
@require_auth
def get_resume(resume_id):
    try:
        # Get payment status from query parameter
        payment_status = request.form.get('payment', '0')
        payment_made = payment_status == '1'

        # Get user
        user = User.query.filter_by(email=g.user_email).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get resume belonging to the user
        resume = Resume.query.filter_by(id=resume_id, profile_id=user.id).first()
        if not resume:
            return jsonify({"error": "Resume not found"}), 404

        # Handle JSON data
        full_resume_data = handle_json_data(resume.structured_resume_data)

        # Apply payment logic to response
        if payment_made:
            # Full response for paid users
            response_data = full_resume_data
        else:
            # Limited response for non-paid users (40% of fields)
            response_data = {
                "notice": "You have not made payment. Please pay to view the full response.",
                "name": full_resume_data.get("name", ""),
                "email": full_resume_data.get("email", ""),
                "professional_summary": full_resume_data.get("professional_summary", ""),
                "skills": full_resume_data.get("skills", [])[:3] if full_resume_data.get("skills") else [],
                "ats_score": full_resume_data.get("ats_score", 0),
                "work_experience": "🔒 Upgrade to view work experience details",
                "projects": "🔒 Upgrade to view projects details",
                "education": "🔒 Upgrade to view education details",
                "certifications": "🔒 Upgrade to view certifications details",
                "feedback": ["🔒 Upgrade to view detailed feedback and suggestions"]
            }

        return jsonify({
            "success": True,
            "resume_id": resume.id,
            "created_at": resume.created_at.isoformat(),
            "data": response_data,
            "job_description": resume.job_description,
            "payment_status": payment_made,
            "full_access": payment_made
        }), 200

    except Exception as e:
        print(f"Error in get_resume: {str(e)}")
        return jsonify({"error": f"Error fetching resume: {str(e)}"}), 500


@app.route('/api/user-resumes', methods=['GET'])
@require_auth
def get_user_resumes():
    try:
        # Get user
        user = User.query.filter_by(email=g.user_email).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get all resumes for the user
        resumes = Resume.query.filter_by(profile_id=user.id).order_by(Resume.created_at.desc()).all()

        resume_list = []
        for resume in resumes:
            # Handle JSON data
            resume_data = handle_json_data(resume.structured_resume_data)

            resume_list.append({
                "id": resume.id,
                "created_at": resume.created_at.isoformat(),
                "job_description": resume.job_description[:100] + "..." if len(
                    resume.job_description) > 100 else resume.job_description,
                "feedback_count": len(resume_data.get("feedback", [])) if resume_data else 0,
                "has_data": bool(resume_data)
            })

        return jsonify({
            "success": True,
            "resumes": resume_list
        }), 200

    except Exception as e:
        print(f"Error in get_user_resumes: {str(e)}")
        return jsonify({"error": f"Error fetching resumes: {str(e)}"}), 500


# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully")


if __name__ == '__main__':
    init_db()
    # Use environment variable PORT for Render
    port = int(os.environ.get('PORT', 5008))
    app.run(host='0.0.0.0', port=port, debug=False)