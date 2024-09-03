from flask import Flask, render_template, request, jsonify
import jwt
import hashlib
from pymongo import MongoClient
import datetime
from datetime import datetime, timedelta
import os
import secrets

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(32)
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/mydatabase")
client = MongoClient(mongo_uri)
db = client["mydatabase"]
collection_user = db["user"]
collection_table = db["table"]

# tables = [
#     {"tableNum": 1, "user_name": "user_1", "occupied": False},
#     {"tableNum": 2, "user_name": "user_2", "occupied": True},
#     {"tableNum": 3, "user_name": "user_3", "occupied": False},
#     {"tableNum": 4, "user_name": "user_4", "occupied": True},
#     {"tableNum": 5, "user_name": "user_5", "occupied": False},
#     {"tableNum": 6, "user_name": "user_6", "occupied": True},
#     {"tableNum": 7, "user_name": "user_7", "occupied": False},
#     {"tableNum": 8, "user_name": "user_8", "occupied": True},
#     {"tableNum": 9, "user_name": "user_9", "occupied": False},
#     {"tableNum": 10, "user_name": "user_10", "occupied": True},
#     {"tableNum": 11, "user_name": "user_11", "occupied": False},
#     {"tableNum": 12, "user_name": "user_12", "occupied": True},
#     {"tableNum": 13, "user_name": "user_13", "occupied": False},
#     {"tableNum": 14, "user_name": "user_14", "occupied": True},
#     {"tableNum": 15, "user_name": "user_15", "occupied": False},
#     {"tableNum": 16, "user_name": "user_16", "occupied": True},
#     {"tableNum": 17, "user_name": "user_17", "occupied": False},
#     {"tableNum": 18, "user_name": "user_18", "occupied": True},
# ]

# collection_table.insert_many(tables)


@app.route("/")
def home():
    return render_template("signin.html")


@app.route("/main")
def main():
    return render_template("main.html")


@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/main/show")
def show():
    return jsonify({"result": "success"})


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


def is_occupied(tableNum):
    seat = collection_table.find_one({"tableNum": tableNum})
    return seat.get("occupied")


@app.route("/room", methods=["GET"])
def room_info():
    tables = list(collection_table.find({}, {"_id": 0}))

    return jsonify({"result": "success", "tables": tables})


@app.route("/table/info", methods=["GET"])
def table_info():
    tableNum = request.args.get("tableNum")
    if not is_occupied(tableNum):
        return jsonify({"result": "failure", "message": "taken seat info request"})

    table = collection_table.find_one({"tableNum": tableNum})
    return jsonify({"result": "success", "table": table})


# @app.route("/table", methods=['POST'])
# def request_table():
#    tableNum = request.args.get("tableNum")
#    if is_occupied(tableNum):
#        return jsonify({'result':'failure', 'message':'already taken seat'})
#
#    table = collection_table.find_one({"tableNum": tableNum})
#    # jwt 를 받아와서 유저 정보 table collection에 입력


@app.route("/reserve", methods=["POST"])
def reserve_table():
    token = request.headers.get("Authorization")
    print(token)
    # payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    tableNum_receive = request.form["tableNum_give"]
    print(tableNum_receive)
    return jsonify({"result": "success"})


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
