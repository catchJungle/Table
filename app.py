from flask import Flask, render_template, request, jsonify
import jwt
import hashlib
from pymongo import MongoClient
import datetime
from datetime import datetime, timedelta
import os

app = Flask(__name__)
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/mydatabase")
client = MongoClient(mongo_uri)
db = client["mydatabase"]
collection_user = db["user"]
collection_table = db["table"]


@app.route("/")
def home():
    return render_template("signin.html")


@app.route("/main")
def main():
    return render_template("main.html")


@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    phone_receive = request.form["phone_give"]

    print(username_receive)
    print(password_receive)
    print(phone_receive)

    password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()

    doc = {
        "username": username_receive,
        "password": password_hash,
        "phone": phone_receive,
    }
    collection_user.insert_one(doc)

    return jsonify({"result": "success"})


@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]

    print(username_receive)
    print(password_receive)

    password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = collection_user.find_one(
        {
            "username": username_receive,
            "password": password_hash,
        }
    )
    print(result)
    if result is not None:
        payload = {
            "id": username_receive,
            "exp": datetime.utcnow()
            + timedelta(seconds=60 * 60 * 24),  # 로그인 24시간 유지
        }

        token = jwt.encode(payload, "secret", algorithm="HS256")

        return jsonify({"result": "success", "token": token})
    return jsonify({"result": "failure"})


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
