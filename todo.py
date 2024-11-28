import streamlit as st
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId  # To handle MongoDB document IDs
from bcrypt import hashpw, gensalt, checkpw
import re
import time
# Load environment variables from the .env file
load_dotenv()

# Singleton connection for MongoDB
def initialize_database():
    if "db_client" not in st.session_state:
        try:
            client = MongoClient(
                os.getenv("MONGO_CONNECTION_STRING"), serverSelectionTimeoutMS=5000
            )
            client.admin.command('ping')  # Test connection
            st.session_state["db_client"] = client
        except Exception as e:
            st.error("Failed to connect to the database. Please try again later.")
            st.stop()
    
    return st.session_state["db_client"].get_database("todo_app")

# Usage
db = initialize_database()
if db is not None:
    users_collection = db["users"]
    tasks_collection = db["tasks"]
else:
    st.stop()  # Stop the app if the database connection fails

# Session state: Initialize user authentication
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

# Function to authenticate users
def authenticate_user(username, password):
    user = users_collection.find_one({"username": username})
    if user and checkpw(password.encode('utf-8'), user["password"]):
        return str(user["_id"])
    return None


# Function to validate the password
def is_valid_password(password):
    """
    Validates a password based on the following criteria:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Minimum length of 8 characters
    """
    pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    return re.match(pattern, password) is not None

# Function to create a new user
def create_user(username, password):
    if users_collection.find_one({"username": username}):
        return False  # Username already exists
    hashed_password = hashpw(password.encode('utf-8'), gensalt())
    users_collection.insert_one({"username": username, "password": hashed_password})
    return True

# Retrieve all tasks for the logged-in user
def get_tasks(user_id):
    return list(tasks_collection.find(
        {"user_id": ObjectId(user_id)},
        {"title": 1, "description": 1, "due_date": 1, "completed": 1}
    ))
    
# Add a new task to the database
def add_task(user_id, title, description, due_date):
    existing_task = tasks_collection.find_one({"user_id": ObjectId(user_id), "title": title})
    if existing_task:
        st.error("Task with this title already exists.")
        return
    tasks_collection.insert_one({
        "user_id": ObjectId(user_id),  # Link task to the logged-in user
        "title": title,
        "description": description,
        "due_date": str(due_date),  # Convert date object to string
        "completed": False,         # Tasks are incomplete by default
    })
    st.success("Task added successfully!")  # Success message after task is added

# Delete a specific task by its ID
def delete_task(task_id):
    tasks_collection.delete_one({"_id": ObjectId(task_id)})
    st.success("Task deleted successfully!")  # Success message after task deletion
    st.rerun()

# Clear all completed tasks for the logged-in user
def clear_completed_tasks(user_id):
    completed_tasks = tasks_collection.count_documents({"user_id": ObjectId(user_id), "completed": True})

    if completed_tasks > 0:
        tasks_collection.delete_many({"user_id": ObjectId(user_id), "completed": True})
        st.success("All completed tasks have been cleared.")
        time.sleep(1)
        st.rerun()
    else:
        st.info("There are no completed tasks to clear.")

def logout():
    st.session_state.clear()
    st.success("You have been logged out.")
    


# App title
st.markdown("<h1 style='text-align: center;'>To-Do List App📄</h1>", unsafe_allow_html=True)

# Authentication (Login and Sign-Up)
if st.session_state["user_id"] is None:
    # Sidebar for authentication
    st.sidebar.header("User Login / Sign Up")
    with st.sidebar.form(key="authentication_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        # Login button
        login_btn = st.form_submit_button(label="Log In")
        if login_btn:
            if not username or not password:
                st.error("Please enter both a username and a password.")
            else: 
                user_id = authenticate_user(username, password)
                if user_id:
                    st.session_state["user_id"] = user_id  # Set session user ID
                    st.success("Logged in successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    
         # Sign-Up button
        signup_btn = st.form_submit_button(label="Sign Up")
        if signup_btn:
            if not username or not password:
                st.error("Please enter both a username and a password.")
                
            elif not is_valid_password(password):
                st.error("Password must include at least 8 characters, one uppercase letter, one lowercase letter, one number, and one special character.")

            else:
                if create_user(username, password):
                    user = users_collection.find_one({"username": username})
                    st.session_state["user_id"] = str(user["_id"])
                    st.success("User created! Log in now.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Username already exists.")

else:
    # Sidebar for adding a new task
    st.sidebar.header("Add a New Task")
    
    # Wrap the task input form with st.form
    with st.sidebar.form(key="task_form"):
        title = st.text_input("Task Title")
        description = st.text_area("Description")
        due_date = st.date_input("Due Date")
        
        # Submit button for the form
        submit_button = st.form_submit_button(label="Add Task📄")
        
        if submit_button:
            if title.strip():  # Ensure title is not empty
                add_task(st.session_state["user_id"], title.strip(), description, due_date)
                
            else:
                st.sidebar.error("Task Title is required!")
    
        # Logout button
        st.sidebar.button("Log Out", on_click=logout)

    # Display user tasks
    st.header("Your Tasks📄")
    

    tasks = get_tasks(st.session_state["user_id"])  # Fetch tasks for the logged-in user


    total_tasks = len(tasks)
    completed_tasks = sum(1 for task in tasks if task["completed"])

    if total_tasks > 0:
        st.markdown("### Task Completion Progress")
        st.progress(completed_tasks / total_tasks)
    else:
        st.info("No tasks found. Start adding tasks to see your progress!")
        


    for task in tasks:
        # Task details and action buttons
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            # Styled task details
            style = "text-decoration: line-through; color: gray;" if task["completed"] else ""
            st.markdown(
                f"<div style='{style}'><b style= 'font-size: 1.2rem'>{task['title']}</b><br>{task['description']}<br>Due: {task['due_date']}</div>",
                unsafe_allow_html=True
            )      

        with col2:
                # Mark task as complete
            is_checked = st.checkbox("Mark Complete", value=task["completed"], key=str(task["_id"]))

            if is_checked != task["completed"]:
                tasks_collection.update_one(
                        {"_id": ObjectId(task["_id"])},
                        {"$set": {"completed": is_checked}},
                    )
                st.rerun()
                
               
                    
        with col3:
            # Delete task
            if st.button("Delete", key=f"delete_{task['_id']}"):
                delete_task(task["_id"])

        # Add space after each task (margin-bottom)
        st.markdown(f"""
    <div style="margin-bottom: 10px;"></div>""", unsafe_allow_html=True)  # Adds space between tasks        
    
    st.markdown("---")
    # Clear completed tasks
    if st.button("Clear Completed Tasks"):
        clear_completed_tasks(st.session_state["user_id"])