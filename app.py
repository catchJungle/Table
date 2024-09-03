from flask import Flask, jsonify, render_template
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient("mongodb://43.202.55.187:27017/")
db = client["mydatabase"]
collection = db["user"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mongo')
def mongo():
    collection.insert_one({"status":"opened"})

    users = collection.find({})
    return jsonify(users)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)