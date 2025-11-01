from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import requests
import os
from werkzeug.utils import secure_filename
from datetime import date

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- ✅ Connection Pool (prevents “Unread result found”) ---
connection_pool = pooling.MySQLConnectionPool(
    pool_name="college_pool",
    pool_size=5,
    pool_reset_session=True,
    
    host="localhost",
    user="root",
    password="Root*19470",
    database="college9_notices",
    auth_plugin='mysql_native_password'
   # ssl_disabled=True
)

def get_db_connection():
    """Get a fresh connection from the pool"""
    return connection_pool.get_connection()

def get_cursor(conn):
    """Get a dictionary cursor for JSON responses"""
    return conn.cursor(dictionary=True, buffered=True)

# --- File Upload Setup ---
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Serve Uploaded Files ---
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    uploads_dir = os.path.join(app.root_path, "uploads")
    return send_from_directory(uploads_dir, filename)

# --- Categorize Notice using AI ---
@app.route("/api/categorize", methods=["POST"])
def categorize():
    data = request.get_json()
    title = data.get("title", "")
    description = data.get("description", "")
    semester = data.get("semester", "").strip().lower()

    try:
        ai_response = requests.post(
            "http://127.0.0.1:8000/predict",
            json={"title": title, "description": description, "semester": semester}
        )
        category = ai_response.json().get("category", "general")
    except Exception as e:
        print("AI service error:", e)
        category = "general"

    return jsonify({"category": category})

# --- Add or Update Notice ---
@app.route("/api/notices", methods=["POST"])
def add_notice():
    conn = get_db_connection()
    cursor = get_cursor(conn)
    try:
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        expiry_date = request.form.get("expiry_date", None)
        semester = request.form.get("semester", None)

        if not title or not description:
            return jsonify({"success": False, "error": "Title and description are required"}), 400

        # --- AI Category Detection ---
        try:
            ai_response = requests.post(
                "http://127.0.0.1:8000/predict",
                json={"title": title, "description": description, "semester": semester}
            )
            category = ai_response.json().get("category", "general")
        except Exception as e:
            print("AI service error:", e)
            category = "general"

        # --- Rule-based overrides ---
        combined_text = (title + " " + description).lower()
        placement_keywords = ["placement", "recruitment", "campus drive", "company visit", "hiring", "offer"]
        if any(word in combined_text for word in placement_keywords):
            category = "placement"
        if category == "general":
            category = "achievements"

        # --- Save Uploaded File ---
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

        # # --- Check for existing notice ---
        # cursor.execute(
        #     "SELECT id, image_url FROM notices WHERE category = %s AND semester = %s",
        #     (category, semester)
        # )
        # existing = cursor.fetchone()

        # if existing:
        #     # --- Update existing notice ---
        #     update_query = """
        #         UPDATE notices
        #         SET title = %s, description = %s, expiry_date = %s, image_url = %s
        #         WHERE id = %s
        #     """
        #     cursor.execute(update_query, (
        #         title, description, expiry_date,
        #         image_url or existing["image_url"], existing["id"]
        #     ))
        #     conn.commit()
        #     notice_id = existing["id"]
        #     message = f"Notice updated successfully for category: {category}"
        # else:
        #     # --- Insert new notice ---
        #     cursor.execute(
        #         "INSERT INTO notices (title, description, category, semester, image_url, expiry_date) VALUES (%s, %s, %s, %s, %s, %s)",
        #         (title, description, category, semester, image_url, expiry_date)
        #     )
        #     conn.commit()
        #     notice_id = cursor.lastrowid
        #     message = f"Notice added successfully under category: {category}"
        # --- Check for existing notice ---
        cursor.execute(
            "SELECT id, image_url, category FROM notices WHERE semester = %s AND category LIKE 'exam%%'",
            (semester,)
        )
        existing = cursor.fetchone()

        if existing:
        # Only replace if existing category is 'exam' related
           if existing["category"].startswith("exam"):
              update_query = """
                 UPDATE notices
                 SET title = %s, description = %s, expiry_date = %s, image_url = %s, category = %s
                 WHERE id = %s
             """
              cursor.execute(update_query, (
                 title, description, expiry_date,
                 image_url or existing["image_url"], category, existing["id"]
              ))
              conn.commit()
              notice_id = existing["id"]
              message = f"Exam notice updated successfully for semester: {semester}"
           else:
        # Don’t overwrite non-exam categories
              message = f"Notice already exists for semester {semester} (category: {existing['category']}); not replaced."
              notice_id = existing["id"]
        else:
       # --- Insert new notice ---
           cursor.execute(
               "INSERT INTO notices (title, description, category, semester, image_url, expiry_date) VALUES (%s, %s, %s, %s, %s, %s)",
               (title, description, category, semester, image_url, expiry_date)
           )
        conn.commit()
        notice_id = cursor.lastrowid
        message = f"New notice added under category: {category}"

        

        notice = {
            "id": notice_id,
            "title": title,
            "description": description,
            "category": category,
            "image_url": image_url,
            "semester": semester,
            "expiry_date": expiry_date
        }

        return jsonify({"success": True, "message": message, "notice": notice})

    except Exception as e:
        conn.rollback()
        print("Error adding notice:", e)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- Get notices by category ---
@app.route("/api/notices/<category>", methods=["GET"])
def get_notices_by_category(category):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    try:
        if category.startswith("exam"):
            cursor.execute("SELECT * FROM notices WHERE category LIKE %s", (f"{category}%",))
        else:
            cursor.execute("SELECT * FROM notices WHERE category = %s", (category,))
        notices = cursor.fetchall()
        return jsonify(notices)
    except Exception as e:
        print("Error fetching notices:", e)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ✅ DELETE expired notices
@app.route("/api/cleanup_expired", methods=["DELETE"])
def cleanup_expired_notices():
    conn = get_db_connection()
    cursor = get_cursor(conn)
    try:
        today = date.today()
        query = "DELETE FROM notices WHERE expiry_date IS NOT NULL AND expiry_date < %s"
        cursor.execute(query, (today,))
        conn.commit()
        deleted_count = cursor.rowcount
        return jsonify({"success": True, "deleted": deleted_count})
    except Exception as e:
        conn.rollback()
        print("Cleanup error:", e)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ✅ GET all current (non-expired) notices
@app.route("/api/notices", methods=["GET"])
def get_notices():
    conn = get_db_connection()
    cursor = get_cursor(conn)
    try:
        today = date.today()
        query = """
            SELECT id, title, description, category, semester, image_url, expiry_date
            FROM notices
            WHERE expiry_date IS NULL OR expiry_date >= %s
            ORDER BY id DESC
        """
        cursor.execute(query, (today,))
        results = cursor.fetchall()

        for row in results:
            if row["expiry_date"]:
                row["expiry_date"] = row["expiry_date"].strftime("%Y-%m-%d")

        return jsonify(results)
    except Exception as e:
        print("Error fetching notices:", e)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- Get recent notices (for marquee) ---
@app.route("/api/notices/recent", methods=["GET"])
def get_recent_notices():
    conn = get_db_connection()
    cursor = get_cursor(conn)
    try:
        cursor.execute("SELECT id, title, category FROM notices ORDER BY id DESC LIMIT 15")
        notices = cursor.fetchall()
        return jsonify(notices)
    except Exception as e:
        print("Error fetching recent notices:", e)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- Run Flask server ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)
