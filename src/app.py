import calendar
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
from database import get_connection


st.set_page_config(page_title="Household Task Manager", layout="wide")

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Users", "Schedule", "Tasks", "Assign Tasks"])

# Load Data Function
def fetch_data(query):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    data = cursor.fetchall()
    conn.close()
    return pd.DataFrame(data)

# Home Page
if page == "Home":
    st.title("🏡 Household Task Manager")
    st.write("Manage and distribute household chores efficiently!")

    # Select Users (allow multiple selection)
    users = fetch_data("SELECT UserID, UserName FROM User")
    user_options = dict(zip(users["UserName"], users["UserID"]))
    selected_users = st.multiselect("Select Users", users["UserName"])

    if selected_users:
        # Generate 7-day calendar starting from today
        today = datetime.today()
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Calculate the upcoming 7 days starting from today
        start_date = today - timedelta(days=today.weekday())  # Start from Monday
        week_dates = [start_date + timedelta(days=i) for i in range(7)]  # Get 7 days

        # Create a dictionary for schedules by day
        schedules_by_day = {day: [] for day in days_of_week}

        # Fetch the schedules for the selected users within the 7 days
        user_ids = [user_options[user] for user in selected_users]
        user_ids_str = ', '.join(map(str, user_ids))  # Prepare the user IDs for the SQL query

        schedule_query = f"""
        SELECT u.UserName, TIME_FORMAT(t.TaskTime,'%H:%i:%s')  as TaskTime,TIME_FORMAT(DATE_ADD(t.TaskTime, INTERVAL TaskDuration MINUTE),'%H:%i:%s') as EndTaskTime, a.AssignmentDay, t.TaskName
        FROM assignment a
        JOIN user u ON a.UserID = u.UserID
        JOIN task t ON t.TaskID = a.TaskID
        WHERE a.UserID IN ({user_ids_str}) AND a.AssignmentDay IN ({', '.join(f"'{day}'" for day in days_of_week)})
        """
        schedules = fetch_data(schedule_query)

        # Group schedules by day
        for _, row in schedules.iterrows():
            schedules_by_day[row["AssignmentDay"]].append({
                "TaskTime": row["TaskTime"],
                "EndTaskTime": row["EndTaskTime"],
                "TaskName": row["TaskName"]
            })

        # Display the calendar grid (7 days)
        st.subheader(f"7-Day Schedule for Selected Users")

        # Create a calendar grid layout
        calendar_layout = st.container()  # Container for calendar layout

        # Generate the grid for the 7 days
        with calendar_layout:
            cols = st.columns(7)  # Create 7 columns for each day

            # Loop through each day and its schedules
            for i, day_name in enumerate(days_of_week):
                with cols[i]:
                    st.subheader(day_name)  # Display the day of the week
                    day_schedules = schedules_by_day.get(day_name, [])
                    if not day_schedules:
                        st.write("No schedules for this day.")
                    else:
                        # Display schedules for the day
                        for schedule in day_schedules:
                            st.write(f"{schedule['TaskTime']} - {schedule['EndTaskTime']} ({schedule['TaskName']}) ")
    else:
        st.write("Please select at least one user.")
# View Users
elif page == "Users":
    st.title("👥 Users")

    users = fetch_data("SELECT * FROM User")
    st.dataframe(users)

    st.subheader("➕ Add a New User")
    new_username = st.text_input("Enter Name")
    new_userrole = st.selectbox("Select Role", ["Parents", "Child", "Help"])

    if st.button("Create User"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO User (UserName, UserRole) VALUES (%s, %s)",
            (new_username, new_userrole)
        )
        conn.commit()
        conn.close()
        st.success(f"User '{new_username}' added successfully!")



# Schedule Tasks
elif page == "Schedule":
    st.title("📅 Schedule Tasks")

    users = fetch_data("SELECT UserID, UserName FROM User")

    if users.empty:
        st.warning("⚠️ No users found! Please add a user first.")
    else:
        user_options = dict(zip(users["UserName"], users["UserID"]))

        st.subheader("📌 Existing Schedules")
        schedules = fetch_data("SELECT ScheduleID, UserID, TIME_FORMAT(StartTime,'%H:%i:%s') as StartTime, TIME_FORMAT(EndTime,'%H:%i:%s') as EndTime, Day, ActiveStatus FROM Schedule")
        st.dataframe(schedules)

        st.subheader("➕ Add New Schedule")
        user = st.selectbox("Select User", users["UserName"])

        # Multi-day selection
        days = st.multiselect("Select Days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])

        start_time = st.time_input("Start Time")
        end_time = st.time_input("End Time")

        if st.button("Add Schedule"):
            if not days:
                st.warning("⚠️ Please select at least one day!")
            else:
                conn = get_connection()
                cursor = conn.cursor()

                for day in days:
                    cursor.execute(
                        "INSERT INTO Schedule (UserID, StartTime, EndTime, Day) VALUES (%s, %s, %s, %s)",
                        (user_options[user], start_time, end_time, day)
                    )

                conn.commit()
                conn.close()
                st.success(f"✅ Schedule added for {user} on {', '.join(days)} from {start_time} to {end_time}")

        # Manage Schedule Activation Status
        st.subheader("🔄 Manage Schedule Status")
        schedule_id = st.selectbox("Select Schedule ID", schedules["ScheduleID"])

        # Fetch current activation status of the selected schedule
        current_status = \
        fetch_data(f"SELECT activestatus FROM Schedule WHERE ScheduleID = {schedule_id}")["activestatus"].iloc[0]

        # Convert boolean to displayable status
        status_options = ["Active", "Inactive"]
        new_status = st.selectbox("Select New Status", status_options,
                                  index=status_options.index("Active" if current_status else "Inactive"))

        if st.button("Update Status"):
            new_status_boolean = True if new_status == "Active" else False
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Schedule SET activestatus = %s WHERE ScheduleID = %s",
                (new_status_boolean, schedule_id)
            )
            conn.commit()
            conn.close()
            st.success(f"✅ Schedule status updated to {new_status}!")


# Assignments
elif page == "Assign Tasks":
    st.title("✅ Assign Tasks")

    # Fetch Users and Tasks
    users = fetch_data("SELECT UserID, UserName FROM User")
    tasks = fetch_data("SELECT TaskID, TaskName FROM Task")

    if users.empty:
        st.warning("⚠️ No users found! Please add a user first.")
    elif tasks.empty:
        st.warning("⚠️ No tasks found! Please add a task first.")
    else:
        user_options = dict(zip(users["UserName"], users["UserID"]))
        task_options = dict(zip(tasks["TaskName"], tasks["TaskID"]))

        # Select Task
        task_name = st.selectbox("Select Task", tasks["TaskName"])

        # Select Available Users based on the Task Time
        selected_task = fetch_data(f"SELECT TIME_FORMAT(TaskTime,'%H:%i:%s') as TaskTime FROM Task WHERE TaskName = '{task_name}'")
        task_time = selected_task["TaskTime"].iloc[0]



        st.write(f"Task Time: {task_time}")

        # Fetch Users Available During Task Time
        day = st.selectbox("Select Day for Assignment", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])


        # Get available users based on selected time and day
        available_users_query = f"""
        SELECT u.UserName, s.UserID 
        FROM Schedule s 
        JOIN User u ON s.UserID = u.UserID
        WHERE s.Day = '{day}' AND s.StartTime <= '{task_time}' AND s.EndTime >= '{task_time}' AND s.activestatus = TRUE
        """

        available_users = fetch_data(available_users_query)

        if available_users.empty:
            st.write("⚠️ No users available at this time.")
        else:
            user_for_assignment = st.multiselect("Select Users for Task Assignment", available_users["UserName"])

            # Multi-day selection for assignment
            days_for_assignment = st.multiselect("Select Days for Assignment", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])

            if st.button("Assign Task"):
                if not user_for_assignment or not days_for_assignment:
                    st.warning("⚠️ Please select at least one user and one day.")
                else:
                    # Assign task to selected users for selected days
                    conn = get_connection()
                    cursor = conn.cursor()

                    task_id = task_options[task_name]

                    for user_name in user_for_assignment:
                        user_id = int(available_users[available_users["UserName"] == user_name]["UserID"].iloc[0])

                        for day in days_for_assignment:

                            cursor.execute(
                                "INSERT INTO Assignment (TaskID, UserID, AssignmentDay) VALUES (%s, %s, %s)",
                                (task_id, user_id, day)
                            )

                    conn.commit()
                    conn.close()
                    st.success("✅ Task successfully assigned to selected users on selected days!")




elif page == "Tasks":
    st.title("📝 Manage Tasks")

    # Fetch and display existing tasks
    tasks = fetch_data("SELECT TaskID, TaskName, TIME_FORMAT(TaskTime,'%H:%i:%s') as TaskTime, TaskPriority, TaskDuration FROM Task")
    st.subheader("📌 Existing Tasks")
    st.dataframe(tasks)

    # Add New Task
    st.subheader("➕ Add a New Task")
    task_name = st.text_input("Enter Task Name")
    task_time = st.time_input("Task Time")
    task_priority = st.selectbox("Task Priority", [1, 2, 3, 4, 5])  # Example: 1 = Low, 5 = High
    task_duration = st.number_input("Task Duration (minutes)", min_value=1, step=1)

    if st.button("Add Task"):
        if task_name and task_time:
            # Insert task into the database
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Task (TaskName, TaskTime, TaskPriority, TaskDuration) VALUES (%s, %s, %s, %s)",
                (task_name, task_time, task_priority, task_duration)
            )
            conn.commit()
            conn.close()
            st.success(f"✅ Task '{task_name}' added successfully!")

        else:
            st.warning("⚠️ Please fill in all fields.")




