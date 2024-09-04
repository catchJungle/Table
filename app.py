from flask import Flask, render_template, request, jsonify
import jwt
import hashlib
from pymongo import MongoClient
import datetime
from datetime import datetime, timedelta
import os
import secrets
from functools import wraps

app = Flask(__name__)
SECRET_KEY = "abcd"
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/mydatabase")
client = MongoClient(mongo_uri)
db = client["mydatabase"]
collection_user = db["user"]
collection_table = db["table"]

# tables = [
#     {"tableNum": 1, "user_name": "user_1", "occupied": False},
#     {"tableNum": 2, "user_name": "user_2", "occupied": False},
#     {"tableNum": 3, "user_name": "user_3", "occupied": False},
#     {"tableNum": 4, "user_name": "user_4", "occupied": False},
#     {"tableNum": 5, "user_name": "user_5", "occupied": False},
#     {"tableNum": 6, "user_name": "user_6", "occupied": False},
#     {"tableNum": 7, "user_name": "user_7", "occupied": False},
#     {"tableNum": 8, "user_name": "user_8", "occupied": False},
#     {"tableNum": 9, "user_name": "user_9", "occupied": False},
#     {"tableNum": 10, "user_name": "user_10", "occupied": False},
#     {"tableNum": 11, "user_name": "user_11", "occupied": False},
#     {"tableNum": 12, "user_name": "user_12", "occupied": False},
#     {"tableNum": 13, "user_name": "user_13", "occupied": False},
#     {"tableNum": 14, "user_name": "user_14", "occupied": False},
#     {"tableNum": 15, "user_name": "user_15", "occupied": False},
#     {"tableNum": 16, "user_name": "user_16", "occupied": False},
#     {"tableNum": 17, "user_name": "user_17", "occupied": False},
#     {"tableNum": 18, "user_name": "user_18", "occupied": False},
# ]

# collection_table.insert_many(tables)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return jsonify({"result": "failure", "message": "Token is missing"}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = collection_user.find_one({"username": data["username"]})
        except:
            return jsonify({"result": "failure", "message": "Token is invalid!"}), 401
        return f(current_user, *args, **kwargs)

    return decorated


@app.route("/")
def home():
    token_receive = request.cookies.get("mytoken")
    print("token_receive", token_receive)

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        print("payload", payload)
        user_info = collection_user.find_one({"username": payload["username"]})
        print("cookie checked")
        print(user_info)
        return render_template("main.html")
    except jwt.ExpiredSignatureError:
        print("cookie expired")
        return render_template("signin.html")
    except jwt.exceptions.DecodeError:
        print("cookie undefined")
        return render_template("signin.html")


@app.route("/show_signup")
def show_signup():
    return render_template("signup.html")


@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]

    password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = collection_user.find_one(
        {
            "username": username_receive,
            "password": password_hash,
        }
    )
    if result is not None:
        payload = {
            "username": username_receive,
            "exp": datetime.utcnow()
            + timedelta(seconds=60 * 60 * 24),  # 로그인 24시간 유지
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify({"result": "success", "token": token})
    return jsonify({"result": "failure"})


@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    phone_receive = request.form["phone_give"]
    is_reserved = request.form.get("is_reserved").lower() == "true"

    password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()

    doc = {
        "username": username_receive,
        "password": password_hash,
        "phone": phone_receive,
        "is_reserved": is_reserved,
    }
    collection_user.insert_one(doc)

    return jsonify({"result": "success"})


@app.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"result": "success"})
    response.set_cookie(
        "mytoken", "", expires=0
    )  # 쿠키의 만료 시간을 0으로 설정하여 삭제
    return response


# def is_occupied(tableNum):
#     seat = collection_table.find_one({"tableNum": tableNum})
#     return seat.get("occupied")


@app.route("/person", methods=["GET"])
@token_required
def person_info(current_user):

    user_data = {
        "username": current_user.get("username"),
        "phone": current_user.get("phone"),
        "is_reserved": current_user.get("is_reserved"),
    }

    if int(user_data.get("is_reserved", 0)) > 0:
        return jsonify({"result": "success", "user_data": user_data})
    return jsonify({"result": "fail"})


@app.route("/room", methods=["GET"])
def room_info():
    tables = list(collection_table.find({}, {"_id": 0}))

    return jsonify({"result": "success", "tables": tables})


@app.route("/reserve", methods=["POST"])
@token_required
def reserve_table(current_user):

    is_reserved = int(current_user.get("is_reserved", "0"))
    if is_reserved > 0:
        return jsonify({"result": "fail", "message": "이미 예약하셨습니다."}), 400

    tableNum_receive = request.form["tableNum_give"]

    collection_table.update_one(
        {"tableNum": int(tableNum_receive)},
        {"$set": {"occupied": True, "user_name": current_user["username"]}},
    )

    collection_user.update_one(
        {"_id": current_user["_id"]}, {"$set": {"is_reserved": tableNum_receive}}
    )

    return jsonify({"result": "success", "message": "예약이 완료되었습니다."})


@app.route("/cancel", methods=["POST"])
@token_required
def cancel_table(current_user):
    is_reserved = int(current_user.get("is_reserved", "0"))

    if is_reserved > 0:  # 예약되어있는 경우 DB에서 예약을 False로 바꾼다.
        collection_table.update_one(
            {"tableNum": is_reserved},
            {"$set": {"occupied": False, "user_name": "None"}},
        )
        collection_user.update_one(
            {"_id": current_user["_id"]}, {"$set": {"is_reserved": 0}}
        )
    else:
        return jsonify({"result": "fail", "message": "예약된 내용이 없습니다."})

    return jsonify({"result": "success"})


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)


# @app.route("/table/info", methods=["GET"])
# def table_info():
#     tableNum = request.args.get("tableNum")
#     if not is_occupied(tableNum):
#         return jsonify({"result": "failure", "message": "taken seat info request"})

#     table = collection_table.find_one({"tableNum": tableNum})
#     return jsonify({"result": "success", "table": table})


# @app.route("/table", methods=['POST'])
# def request_table():
#    tableNum = request.args.get("tableNum")
#    if is_occupied(tableNum):
#        return jsonify({'result':'failure', 'message':'already taken seat'})
#
#    table = collection_table.find_one({"tableNum": tableNum})
#    # jwt 를 받아와서 유저 정보 table collection에 입력
