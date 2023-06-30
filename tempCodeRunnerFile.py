@app.route("/signup", methods=["POST"])
def signup():
    username = request.json.get("username")
    password = request.json.get("password")
    user_data = {"username": username, "password": password}
    users.insert_one(user_data)
    return jsonify({"message": "Signup successful"})