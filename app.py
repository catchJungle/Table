from flask import Flask, render_template, request, jsonify
import jwt
import hashlib
from pymongo import MongoClient
import datetime
from datetime import datetime, timedelta

app = Flask(__name__)

client = MongoClient("localhost", 27017)
db = client.jungle


@app.route("/")
def home():
    return render_template("signin.html")


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
    db.myusers.insert_one(doc)

    return jsonify({"result": "success"})


@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]

    print(username_receive)
    print(password_receive)

    password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.myusers.find_one(
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
