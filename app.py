import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your_secret_key_change_this_to_something_secure'

# ดึงค่า URL และ Key จาก Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# ตรวจสอบการเชื่อมต่อ Supabase
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: SUPABASE_URL or SUPABASE_KEY is not set.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        # กรณีสร้างโพสต์ใหม่
        if form_type == 'post':
            name = request.form.get('name').strip() or 'นิรนาม'
            message = request.form.get('message').strip()
            
            if message:
                # หมายเหตุ: เรื่องการอัปโหลดรูปบน Vercel/Supabase แนะนำให้ข้ามไปก่อนหรือใช้ URL รูปภาพ
                supabase.table('posts').insert({
                    'name': name,
                    'message': message,
                    'image': None
                }).execute()
                flash('สร้างกระทู้สำเร็จ!', 'success')
            return redirect(url_for('index'))
            
        # กรณีพิมพ์คอมเมนต์
        elif form_type == 'comment':
            post_id = request.form.get('post_id')
            comment_name = request.form.get('comment_name').strip() or 'นิรนาม'
            comment_message = request.form.get('comment_message').strip()
            
            if comment_message and post_id:
                supabase.table('comments').insert({
                    'post_id': int(post_id),
                    'name': comment_name,
                    'comment': comment_message
                }).execute()
                flash('ส่งความคิดเห็นสำเร็จ!', 'success')
            return redirect(url_for('index'))

    # ดึงข้อมูลโพสต์ทั้งหมดเรียงจากใหม่ไปเก่า
    posts_response = supabase.table('posts').select('*').order('id', desc=True).execute()
    posts = posts_response.data if posts_response.data else []

    # ดึงคอมเมนต์ทั้งหมดมาผูกกับแต่ละโพสต์
    comments_response = supabase.table('comments').select('*').execute()
    all_comments = comments_response.data if comments_response.data else []

    # จัดกลุ่มคอมเมนต์ใส่เข้าไปในโพสต์แต่ละอัน
    for post in posts:
        post['comments'] = [c for c in all_comments if c['post_id'] == post['id']]

    is_admin = session.get('is_admin', False)
    return render_template('index.html', posts=posts, is_admin=is_admin)

# ระบบเข้าสู่ระบบแอดมิน
@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password')
    if password == 'admin123':  # รหัสผ่านแอดมินตั้งต้น
        session['is_admin'] = True
        flash('เข้าสู่ระบบแอดมินสำเร็จ', 'success')
    else:
        flash('รหัสผ่านไม่ถูกต้อง!', 'error')
    return redirect(url_for('index'))

# ออกจากระบบแอดมิน
@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    flash('ออกจากระบบแล้ว', 'success')
    return redirect(url_for('index'))

# ลบโพสต์ (เฉพาะแอดมิน)
@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
    if not session.get('is_admin'):
        flash('คุณไม่มีสิทธิ์ใช้งานส่วนนี้', 'error')
        return redirect(url_for('index'))
    
    # ลบโพสต์ (คอมเมนต์จะถูกลบอัตโนมัติหากตั้งค่า Cascade ไว้ หรือสามารถลบแยกได้)
    supabase.table('posts').delete().eq('id', post_id).execute()
    flash('ลบโพสต์เรียบร้อยแล้ว', 'success')
    return redirect(url_for('index'))

# ลบคอมเมนต์ (เฉพาะแอดมิน)
@app.route('/delete_comment/<int:comment_id>')
def delete_comment(comment_id):
    if not session.get('is_admin'):
        flash('คุณไม่มีสิทธิ์ใช้งานส่วนนี้', 'error')
        return redirect(url_for('index'))
    
    supabase.table('comments').delete().eq('id', comment_id).execute()
    flash('ลบคอมเมนต์เรียบร้อยแล้ว', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)