import os
import sqlite3
import time
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this'
app.config['TEMPLATES_AUTO_RELOAD'] = True

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
  return (
      '.' in filename
      and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
  )


def init_db():
  conn = sqlite3.connect('database.db')
  cursor = conn.cursor()
  cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            message TEXT NOT NULL,
            image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
  cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            name TEXT,
            comment TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
        )
    ''')
  conn.commit()
  conn.close()


init_db()


@app.route('/', methods=['GET', 'POST'])
def index():
  if request.method == 'POST':
    form_type = request.form.get('form_type')

    if form_type == 'post':
      name = request.form.get('name').strip()
      message = request.form.get('message').strip()
      file = request.files.get('image')

      if not message:
        flash('กรุณาใส่ข้อความที่ต้องการโพสต์!', 'danger')
        return redirect(url_for('index'))

      if not name:
        name = 'ไม่ระบุตัวตน'

      image_filename = None
      if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        image_filename = f'{int(time.time())}_{filename}'
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

      conn = sqlite3.connect('database.db')
      cursor = conn.cursor()
      cursor.execute(
          'INSERT INTO posts (name, message, image) VALUES (?, ?, ?)',
          (name, message, image_filename),
      )
      conn.commit()
      conn.close()

      flash('โพสต์ข้อความของคุณเรียบร้อยแล้ว!', 'success')
      return redirect(url_for('index'))

    elif form_type == 'comment':
      post_id = request.form.get('post_id')
      name = request.form.get('comment_name').strip()
      comment = request.form.get('comment_message').strip()

      if not comment:
        flash('กรุณาใส่ข้อความคอมเมนต์!', 'danger')
        return redirect(url_for('index'))

      if not name:
        name = 'ไม่ระบุตัวตน'

      conn = sqlite3.connect('database.db')
      cursor = conn.cursor()
      cursor.execute(
          'INSERT INTO comments (post_id, name, comment) VALUES (?, ?, ?)',
          (post_id, name, comment),
      )
      conn.commit()
      conn.close()

      flash('ตอบกลับคอมเมนต์เรียบร้อยแล้ว!', 'success')
      return redirect(url_for('index'))

  conn = sqlite3.connect('database.db')
  conn.row_factory = sqlite3.Row
  cursor = conn.cursor()
  cursor.execute('SELECT * FROM posts ORDER BY id DESC')
  posts_db = cursor.fetchall()

  posts = []
  for p in posts_db:
    post_dict = dict(p)
    cursor.execute(
        'SELECT * FROM comments WHERE post_id = ? ORDER BY id ASC',
        (post_dict['id'],),
    )
    post_dict['comments'] = cursor.fetchall()
    posts.append(post_dict)

  conn.close()

  return render_template(
      'index.html', posts=posts, is_admin=session.get('is_admin', False)
  )


# ระบบล็อกอินแอดมิน (รหัสผ่านตั้งไว้ว่า admin123 สามารถเปลี่ยนได้ตรงนี้)
@app.route('/login', methods=['POST'])
def login():
  password = request.form.get('password')
  if password == 'admin123':
    session['is_admin'] = True
    flash('เข้าสู่ระบบแอดมินสำเร็จ!', 'success')
  else:
    flash('รหัสผ่านแอดมินไม่ถูกต้อง!', 'danger')
  return redirect(url_for('index'))


# ระบบออกจากระบบแอดมิน
@app.route('/logout')
def logout():
  session.pop('is_admin', None)
  return redirect(url_for('index'))


# ระบบลบโพสต์ (เฉพาะแอดมิน)
@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
  if not session.get('is_admin'):
    flash('คุณไม่มีสิทธิ์ใช้งานส่วนนี้!', 'danger')
    return redirect(url_for('index'))

  conn = sqlite3.connect('database.db')
  cursor = conn.cursor()
  # ลบรูปภาพประกอบถ้ามี
  cursor.execute('SELECT image FROM posts WHERE id = ?', (post_id,))
  row = cursor.fetchone()
  if row and row[0]:
    img_path = os.path.join(app.config['UPLOAD_FOLDER'], row[0])
    if os.path.exists(img_path):
      os.remove(img_path)

  cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
  cursor.execute('DELETE FROM comments WHERE post_id = ?', (post_id,))
  conn.commit()
  conn.close()

  flash('ลบโพสต์เรียบร้อยแล้ว', 'success')
  return redirect(url_for('index'))


# ระบบลบความคิดเห็น (เฉพาะแอดมิน)
@app.route('/delete_comment/<int:comment_id>')
def delete_comment(comment_id):
  if not session.get('is_admin'):
    flash('คุณไม่มีสิทธิ์ใช้งานส่วนนี้!', 'danger')
    return redirect(url_for('index'))

  conn = sqlite3.connect('database.db')
  cursor = conn.cursor()
  cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
  conn.commit()
  conn.close()

  flash('ลบความคิดเห็นเรียบร้อยแล้ว', 'success')
  return redirect(url_for('index'))


if __name__ == '__main__':
  app.run(debug=True)