from flask import Flask, jsonify
from flask_cors import CORS
#import json
app = Flask(__name__)
#CORS(app, resources={r"/": {"origins":"*"}})
CORS(app)
@app.route('/api/vision-mission', methods=['GET'])
def vision_mission():
    return jsonify({
            "vision": "To be recognized as a premier institution in engineering education, research and innovation.",
  "mission": [
    "To impart quality technical education with strong fundamentals.",
    "To nurture creativity, innovation and entrepreneurship.",
    "To instill ethical values and leadership qualities in students.",
    "To promote research and development for societal needs."
  ]


        })

if __name__ == "__main__":
    app.run(debug=True,port=5000)