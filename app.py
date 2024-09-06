from flask import Flask, render_template, request, jsonify
import jwt
import hashlib
from pymongo import MongoClient
import datetime
from datetime import datetime, timedelta
import os
import secrets
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

SECRET_KEY = "abcd"
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/mydatabase")
client = MongoClient(mongo_uri)
db = client["mydatabase"]
collection_user = db["user"]
collection_table = db["table"]

scheduler = BackgroundScheduler()
scheduler.start()

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


def emit_db_update():
    socketio.emit('db_update', {'data':'Database update'})

def auto_checkout(table_num):
    table = collection_table.find_one({"tableNum": table_num})
    userName = table.get("user_name")

    collection_table.update_one(
        {"tableNum": table_num},
        {"$set": {"user_name": None, "occupied": False, "time": None}},
    )

    collection_user.update_one({"username": userName}, {"$set": {"is_reserved": 0}})
    emit_db_update()



def logout_all_users():
    collection_user.update_many({}, {"$set": {"is_reserved": 0}})
    collection_table.update_many(
        {}, {"$set": {"user_name": None, "occupied": False, "time": None}}
    )
    emit_db_update()


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
    is_reserved = 0

    existing_user = collection_user.find_one({"username":username_receive})

    if existing_user:
        return jsonify({"result":"duplicated", "message" : "이미 사용 중인 username 입니다."}), 400

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
    scheduler.add_job(logout_all_users, "cron", hour=21, minute=44)

    return jsonify({"result": "success", "tables": tables})


@app.route("/reserve", methods=["POST"])
@token_required
def reserve_table(current_user):

    is_reserved = int(current_user.get("is_reserved", "0"))
    if is_reserved > 0:
        return jsonify({"result": "fail", "message": "이미 예약하셨습니다."}), 400

    tableNum_receive = request.form["tableNum_give"]
    time = datetime.now() + timedelta(minutes=3)
    tableNum = int(tableNum_receive)
    collection_table.update_one(
        {"tableNum": int(tableNum_receive)},
        {
            "$set": {
                "occupied": True,
                "user_name": current_user["username"],
                "time": time,
            }
        },
    )

    collection_user.update_one(
        {"_id": current_user["_id"]}, {"$set": {"is_reserved": tableNum_receive}}
    )
    scheduler.add_job(auto_checkout, "date", run_date=time, args=[tableNum])
    emit_db_update()
    return jsonify({"result": "success", "message": "예약이 완료되었습니다."})


@app.route("/cancel", methods=["POST"])
@token_required
def cancel_table(current_user):
    is_reserved = int(current_user.get("is_reserved", "0"))

    if is_reserved > 0:  # 예약되어있는 경우 DB에서 예약을 False로 바꾼다.
        collection_table.update_one(
            {"tableNum": is_reserved},
            {"$set": {"occupied": False, "user_name": "None", "time": None}},
        )
        collection_user.update_one(
            {"_id": current_user["_id"]}, {"$set": {"is_reserved": 0}}
        )
        emit_db_update()
    else:
        return jsonify({"result": "fail", "message": "예약된 내용이 없습니다."})

    return jsonify({"result": "success"})


@app.route("/time", methods=["GET"])
def timeRecall():
    tableNum = request.args.get("tableNum")
    if tableNum is None:
        return jsonify({"result": "fail", "message": "tableNum is missing"}), 400
    table = collection_table.find_one({"tableNum": int(tableNum)})
    savedTime = table.get("time")
    user = table.get("user_name")

    if savedTime is None:
        return jsonify({"result": "failure", "message": "no time saved"})

    currentTime = datetime.now()
    timeDifference = savedTime - currentTime
    total_seconds = int(timeDifference.total_seconds())

    if total_seconds < 0:
        return jsonify({"result": "failure", "message": "no time saved"})

    minutes = total_seconds // 60
    seconds = total_seconds % 60

    return jsonify({"result": "success", "time": [minutes, seconds], "user": user})


if __name__ == "__main__":
    socketio.run(app.run("0.0.0.0", port=5001, debug=True))
