# app.py
from flask import Flask, jsonify
from flask_cors import CORS
import scraper  # import your scraper.py file

app = Flask(__name__)
CORS(app)  # allow frontend to call API

@app.route("/api/cse-faculty", methods=["GET"])
def get_cse_faculty():
    print("Route hit!")  
    try:
        data = scraper.load_cache()
        if not data:
            print("Cache empty, scraping...")

            data = scraper.scrape_cse()
            scraper.save_cache(data)
        print(f"Returning {len(data)} records")
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        print(f"Error in route: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
