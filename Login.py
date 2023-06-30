from flask import Flask, render_template, request, redirect
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient("mongodb://localhost:27017/")  # Replace with your MongoDB connection string
db = client["mydatabase"]  # Replace with your database name
users = db["users"]  # Collection for storing users

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user_data = {"username": username, "password": password}
        users.insert_one(user_data)
        return redirect("/login")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user_data = users.find_one({"username": username})
        if user_data and user_data["password"] == password:
            return f"Welcome back, {username}!"
        else:
            return "Invalid username or password"
    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)

