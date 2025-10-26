from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import requests
import os
from werkzeug.utils import secure_filename
from datetime import date


app = Flask(__name__)
CORS(app,resources={r"/*": {"origins": "*"}})


# --- MySQL Connection ---
#def get_db_connection():
 #   return mysql.connector.connect(
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Root*19470",
    database="college9_notices"
)
cursor = db.cursor(dictionary=True)

# --- File Upload Setup ---
UPLOAD_FOLDER = "uploads"
# ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
# ALLOWED_FILE_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif"}
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# if not os.path.exists(UPLOAD_FOLDER):
#     os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Serve Uploaded Files ---
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    uploads_dir = os.path.join(app.root_path, 'uploads')
    return send_from_directory( uploads_dir, filename)


# --- Categorize Notice using AI ---
@app.route("/api/categorize", methods=["POST"])
def categorize():
    data = request.get_json()
    title = data.get("title", "")
    description = data.get("description", "")
    semester = data.get("semester", "").strip().lower()

    

    try:
        ai_response = requests.post("http://127.0.0.1:8000/predict",json={"title": title, "description": description, "semester": semester})
        category = ai_response.json().get("category", "general")

        

    except Exception as e:
        print("AI service error:", e)
        # Fallback logic...
        category = "general"
    return jsonify({"category": category})




# --- Add new notice ---
@app.route("/api/notices", methods=["POST"])
def add_notice():
    try:
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        expiry_date = request.form.get("expiry_date", None)
        semester = request.form.get("semester", None)
        
        if not title or not description:
            return jsonify({"success": False, "error": "Title and description are required"}), 400

        # --- Call AI service to categorize ---
        try:
            ai_response = requests.post(
              #"http://127.0.0.1:8000/predict",
               "http://127.0.0.1:5000/api/categorize",

                json={"title": title ,"description": description, "semester": semester}
            )
            category = ai_response.json().get("category", "general")
            #return jsonify({'message': 'Notice added successfully!'})
            # if category.startswith("exam"):
            #     category = f"exam_{semester}" if semester else "exam_general"
        except Exception as e:
            print("AI service error:", e)
            
            category = "general"
            

        # image_url = ""
        # ia_file_url = ""
        # sem_file_url = ""
        combined_text = (title + " " + description).lower()

        # --- Rule-based overrides ---
        placement_keywords = ["placement", "recruitment", "campus drive", "company visit", "hiring", "offer"]
        if any(word in combined_text for word in placement_keywords):
            category = "placement"

        # Achievement detection (everything else not exam, events, placement)
        if category not in ["placement"] and not category.startswith("exam") and not category.startswith("event"):
            category = "achievements"

        # Helper function to save file
        def save_file(file_field):
            if file_field in request.files:
                file = request.files[file_field]
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(filepath)
                    return f"/{UPLOAD_FOLDER}/{filename}"
            return ""

        image_url = save_file("image_file")
        if category == "placement" and not image_url:
            return jsonify({"success": False, "error": "Placement notice must include an image."}), 400
        


        cursor.execute(
            "INSERT INTO notices (title, description,semester, image_url, expiry_date, category) VALUES (%s, %s, %s, %s, %s, %s)",
            (title, description,semester, image_url, expiry_date, category)
        )
        print("Adding notice with category:", category)

        db.commit()
        notice_id = cursor.lastrowid

        
        notice = {
            "id": notice_id,
            "title": title,
            "description": description,
           
            
            "image_url": image_url,
            # "ia_file_url": ia_file_url,
            # "sem_file_url": sem_file_url,
            "semester": semester,
            "expiry_date": expiry_date,
             "category": category,
        }

        return jsonify({"success": True,"message": f"Notice added successfully under category: {category}", "notice": notice})

    
    except Exception as e:
        print("Error adding notice:", e)
        return jsonify({"success": False, "error": str(e)}), 500

#--- Get notices by category ---
@app.route("/api/notices/<category>", methods=["GET"])
def get_notices_by_category(category):
    try:
        if category.startswith("exam"):
            # For any exam category (exam_5, exam_6, etc.)
            cursor.execute("SELECT * FROM notices WHERE category LIKE %s", (f"{category}%",))
        else:
            cursor.execute("SELECT * FROM notices WHERE category = %s", (category,))
        notices = cursor.fetchall()
        return jsonify(notices)
    except Exception as e:
        print("Error fetching notices:", e)
        return jsonify({"success": False, "error": str(e)}), 500




@app.route("/api/cleanup_expired", methods=["DELETE"])
def cleanup_expired_notices():
    try:
        today = date.today()
        cursor.execute("DELETE FROM notices WHERE expiry_date IS NOT NULL AND expiry_date < %s", (today,))
        db.commit()
        return jsonify({"success": True, "deleted": cursor.rowcount})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- Get recent notices (for marquee) ---
@app.route("/api/notices/recent", methods=["GET"])
def get_recent_notices():
    try:
        cursor.execute("SELECT id, title, category FROM notices ORDER BY id DESC LIMIT 10")
        notices = cursor.fetchall()
        return jsonify(notices)
    except Exception as e:
        print("Error fetching recent notices:", e)
        return jsonify({"success": False, "error": str(e)}), 500



# --- Run Flask server ---
if __name__ == "__main__":
    app.run(debug=True,port=5000)

   