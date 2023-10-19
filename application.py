from flask import Flask, redirect, request, render_template

app = Flask(__name__, static_url_path='/static')

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Add code here to handle the login form submission
        # You can check the username and password and redirect to another page on successful login.
        return "Login successful, redirect to another page."
    return render_template("login.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0')
