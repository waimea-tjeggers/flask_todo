#===========================================================
# App Creation and Launch
#===========================================================

from flask import Flask, render_template, request, flash, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import html

from app.helpers.session import init_session
from app.helpers.db import connect_db
from app.helpers.errors import init_error, not_found_error
from app.helpers.logging import init_logging
from app.helpers.auth import login_required


# Create the app
app = Flask(__name__)

# Configure app
init_session(app)   # Setup a session for messages, etc.
init_logging(app)   # Log requests
init_error(app)     # Handle errors and exceptions


#-----------------------------------------------------------
# Home page route
#-----------------------------------------------------------
@app.get("/")
def index():

    with connect_db() as client:
        sql = """
              SELECT id,
                     name,
                     priority,
                     completed

              FROM tasks
            
              ORDER BY priority DESC
              """
        values = []
        result = client.execute(sql, values)
        tasks = result.rows

    return render_template("pages/home.jinja", tasks=tasks)


#-----------------------------------------------------------
# User registration form route
#-----------------------------------------------------------
@app.get("/register")
def register_form():
    return render_template("pages/register.jinja")


#-----------------------------------------------------------
# User login form route
#-----------------------------------------------------------
@app.get("/login")
def login_form():
    return render_template("pages/login.jinja")



#-----------------------------------------------------------
# Route for adding a task, using data posted from a form
# - Restricted to logged in users
#-----------------------------------------------------------
@app.post("/add")
@login_required
def add_a_thing():
    # Get the data from the form
    name  = request.form.get("name")
    priority = request.form.get("priority")

    # Sanitise the inputs
    name = html.escape(name)

    # Get the user id from the session
    user_id = session["user_id"]

    with connect_db() as client:
        # Add the thing to the DB
        sql = "INSERT INTO tasks (name, priority, user_id) VALUES (?, ?, ?)"
        values = [name, priority, user_id]
        client.execute(sql, values)

        # Go back to the home page
        flash(f"task '{name}' added", "success")
        return redirect("/")



#-----------------------------------------------------------
# Route for deleting a task, Id given in the route
# - Restricted to logged in users
#-----------------------------------------------------------
@app.get("/complete/<int:id>")
@login_required
def complete_a_task(id):
    # Get the user id from the session
    user_id = session["user_id"]

    with connect_db() as client:
        # update the status of the task from the DB only if we own it
        sql = "UPDATE tasks SET tasks.completed = 1 WHERE id=? AND user_id=?"
        values = [id, user_id]
        client.execute(sql, values)

        # Go back to the home page
        return redirect("/")


#-----------------------------------------------------------
# Route for deleting a task, Id given in the route
# - Restricted to logged in users
#-----------------------------------------------------------
@app.get("/incomplete/<int:id>")
@login_required
def incomplete_a_task(id):
    # Get the user id from the session
    user_id = session["user_id"]

    with connect_db() as client:
        # update the status of the task from the DB only if we own it
        sql = "UPDATE tasks SET tasks.completed = 0 WHERE id=? AND user_id=?"
        values = [id, user_id]
        client.execute(sql, values)

        # Go back to the home page
        return redirect("/")


#-----------------------------------------------------------
# Route for deleting a task, Id given in the route
# - Restricted to logged in users
#-----------------------------------------------------------
@app.get("/delete/<int:id>")
@login_required
def delete_a_task(id):
    # Get the user id from the session
    user_id = session["user_id"]

    with connect_db() as client:
        # Delete the thing from the DB only if we own it
        sql = "DELETE FROM tasks WHERE id=? AND user_id=?"
        values = [id, user_id]
        client.execute(sql, values)

        # Go back to the home page
        flash("task deleted", "success")
        return redirect("/")


#-----------------------------------------------------------
# Route for adding a user when registration form submitted
#-----------------------------------------------------------
@app.post("/add-user")
def add_user():
    # Get the data from the form
    name = request.form.get("name")
    username = request.form.get("username")
    password = request.form.get("password")

    with connect_db() as client:
        # Attempt to find an existing record for that user
        sql = "SELECT * FROM users WHERE username = ?"
        values = [username]
        result = client.execute(sql, values)

        # No existing record found, so safe to add the user
        if not result.rows:
            # Sanitise the name
            name = html.escape(name)

            # Salt and hash the password
            hash = generate_password_hash(password)

            # Add the user to the users table
            sql = "INSERT INTO users (name, username, password_hash) VALUES (?, ?, ?)"
            values = [name, username, hash]
            client.execute(sql, values)

            # And let them know it was successful and they can login
            flash("Registration successful", "success")
            return redirect("/login")

        # Found an existing record, so prompt to try again
        flash("Username already exists. Try again...", "error")
        return redirect("/register")


#-----------------------------------------------------------
# Route for processing a user login
#-----------------------------------------------------------
@app.post("/login-user")
def login_user():
    # Get the login form data
    username = request.form.get("username")
    password = request.form.get("password")

    with connect_db() as client:
        # Attempt to find a record for that user
        sql = "SELECT * FROM users WHERE username = ?"
        values = [username]
        result = client.execute(sql, values)

        # Did we find a record?
        if result.rows:
            # Yes, so check password
            user = result.rows[0]
            hash = user["password_hash"]

            # Hash matches?
            if check_password_hash(hash, password):
                # Yes, so save info in the session
                session["user_id"]   = user["id"]
                session["user_name"] = user["name"]
                session["logged_in"] = True

                # And head back to the home page
                flash("Login successful", "success")
                return redirect("/")

        # Either username not found, or password was wrong
        flash("Invalid credentials", "error")
        return redirect("/login")


#-----------------------------------------------------------
# Route for processing a user logout
#-----------------------------------------------------------
@app.get("/logout")
def logout():
    # Clear the details from the session
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("logged_in", None)

    # And head back to the home page
    flash("Logged out successfully", "success")
    return redirect("/")

