from flask import Flask, jsonify, render_template
from pymongo import MongoClient
import os

app = Flask(__name__)

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/mydatabase")
client = MongoClient(mongo_uri)
db = client["mydatabase"]


collection = db["user"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mongo')
def mongo():
    collection.insert_one({"status":"opened"})

    users = list(collection.find({}))
    return jsonify(users)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)