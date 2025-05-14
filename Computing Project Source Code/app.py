from flask import Flask, render_template, request, redirect, session, g
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'accounts.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        ''')
        conn.commit()

# Call it once to initialize
init_db()


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/advice')
def advice(): 
    return render_template('advice.html')

@app.route('/register_login')
def register_login():
    return render_template('register_login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            return "Username already exists."
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':  # ✅ not request.method['POST']
        username = request.form.get('username')  # ✅ get(), not []
        password = request.form.get('password')

        if not username or not password:
            return "Missing credentials", 400

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect('/')
        else:
            return "Invalid login credentials", 401
    else:
        return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/forum', methods=['GET', 'POST'])
def forum():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST' and 'user_id' in session:
        content = request.form['content']
        parent_post_id = request.form.get('parent_post_id')  # Get parent post ID if it's a reply
        cursor.execute("INSERT INTO posts (user_id, content, parent_post_id) VALUES (?, ?, ?)", 
                       (session['user_id'], content, parent_post_id))
        db.commit()
        
        

    # Fetch posts along with replies (if any)
    cursor.execute("""
        SELECT posts.id, posts.content, posts.timestamp, users.username, posts.parent_post_id
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.timestamp DESC
    """)
    posts = cursor.fetchall()

    # Organize posts and replies into a nested structure
    post_dict = {}
    for post in posts:
        post_dict[post[0]] = {"id": post[0], "content": post[1], "timestamp": post[2], 
                              "username": post[3], "parent_post_id": post[4], "replies": []}

    # Create a hierarchy of posts and their replies
    for post in posts:
        parent_id = post[4]  # Assuming index 4 is parent_id
        if parent_id in post_dict:
            post_dict[parent_id]["replies"].append(post_dict[post[0]])
        else:
            # Orphaned reply — no parent found
            print(f"Warning: Parent post {parent_id} not found for post {post[0]}")

    # Filter out top-level posts (i.e., posts that don't have a parent_post_id)
    top_level_posts = [post for post in post_dict.values() if post["parent_post_id"] is None]

    return render_template('forum.html', posts=top_level_posts, username=session.get('username'))



if __name__ == '__main__':
    app.run(debug=True)