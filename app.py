from flask import Flask, request, render_template, redirect, url_for, jsonify, make_response, current_app
from pymongo import MongoClient
import requests
import hashlib
from datetime import datetime
from bson import ObjectId
import jwt
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = './static/image_penginapan'

SECRET_KEY = 'QWERTY1234'

MONGODB_CONNECTION_STRING = 'mongodb+srv://dwiadnyana:041002Dekgus@cluster0.rv3yldr.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(MONGODB_CONNECTION_STRING)
db = client.Marerep

TOKEN_KEY = 'mytoken'


# HOME
@app.route('/')
def home():
    token_receive = request.cookies.get(TOKEN_KEY)
    accommodations = list(db.penginapan.find())
    if token_receive is None:
        return render_template('index.html', logged_in=False, accommodations=accommodations )

    try:
        # Lanjutkan dengan dekode token dan pengambilan data customer hanya jika token valid
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        
        # Pastikan payload memiliki id sebelum mencari data customer
        if 'username' in payload:
            user_info = db.customer.find_one({"username": payload['username']})
            logged_in = True
            return render_template('index.html', user_info=user_info, logged_in=logged_in, accommodations=accommodations)
        else:
            # Jika payload tidak memiliki id, token tidak valid
            # raise jwt.exceptions.InvalidTokenError('Token tidak valid')
            logged_in = False   
            return render_template('index.html', logged_in=logged_in, accommodations=accommodations)
    except jwt.ExpiredSignatureError:
        msg = 'Token login anda sudah kedaluarsa!'
    except jwt.exceptions.DecodeError:
        msg = 'Terdapat masalah saat anda login!'
        logged_in = False   
    return render_template('index.html', msg=msg, logged_in=logged_in)





# USER ADMIN

# Login Admin
@app.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    # Jika methods POST
    if request.method == 'POST':
        id_receive = request.form.get('id_give')
        password_receive = request.form.get('password_give')

        password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()

        result = db.admin.find_one({
            'id': id_receive,
            'password': password_hash,
        })

        if result is not None:
            payload = {
                "id": id_receive,
                "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
            }
            token = jwt.encode(
                payload, 
                SECRET_KEY, 
                algorithm='HS256'
            )
            return jsonify({
                "result": "success", 
                "token": token
            })
        else:
            return jsonify({
                "result": "fail", 
                "msg": "Terdapat kesalahan pada ID atau Password anda!"
            })

    # Jika methods GET
    msg = request.args.get('msg')
    return render_template('login_admin.html', msg=msg)


# Dasboard Admin
@app.route('/admin')
def admin():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.admin.find_one({"id": payload["id"]})

        accommodations = list(db.penginapan.find())

        return render_template("dasboard_admin.html", user_info=user_info, accommodations=accommodations)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login_admin", msg="Token login anda sudah kedaluarsa!"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login_admin", msg="Terdapat masalah saat anda login!"))


@app.route('/tambah/penginapan', methods=['GET', 'POST'])
def tambah_penginapan():
    if request.method == 'POST':
        token_receive = request.cookies.get(TOKEN_KEY)
        try:     
            payload = jwt.decode(
                token_receive, 
                SECRET_KEY, 
                algorithms=["HS256"]
            )

            user_info = db.admin.find_one({"id": payload["id"]})
            nama_penginapan = request.form.get('namaPenginapan')
            lokasi = request.form.get('lokasi')
            jumlah_kamar = int(request.form.get('jumlahKamar'))
            harga = int(request.form.get('harga'))
            deskripsi = request.form.get('deskripsi')

            tempat_wisata_terdekat = request.form.get('tempatWisata').split(',')

            gambar = request.files['gambar']  
            gambar_filename = secure_filename(gambar.filename)
            gambar.save(os.path.join(app.config['UPLOAD_FOLDER'], gambar_filename))

            db.penginapan.insert_one({
                'gambar': gambar_filename,
                'nama': nama_penginapan,
                'lokasi': lokasi,
                'jumlah_kamar': jumlah_kamar,
                'harga': harga,
                'deskripsi': deskripsi,
                'tempat_wisata_terdekat': tempat_wisata_terdekat,
            })

            return redirect('/admin')

        except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
            return redirect(url_for('admin'))

    token_receive = request.cookies.get(TOKEN_KEY)
    try:     
        payload = jwt.decode(
            token_receive, 
            SECRET_KEY, 
            algorithms=["HS256"]
        )
        return render_template('tambah_penginapan.html')

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('admin'))



@app.route('/delete/penginapan/<accommodation_id>', methods=['DELETE'])
def delete_accommodation(accommodation_id):
    try:
        # Dapatkan nama file gambar sebelum menghapus akomodasi
        accommodation = db.penginapan.find_one({"_id": ObjectId(accommodation_id)})
        gambar_filename = accommodation.get('gambar', None)

        # Hapus akomodasi dari database
        result = db.penginapan.delete_one({"_id": ObjectId(accommodation_id)})

        if result.deleted_count > 0:
            # Jika akomodasi berhasil dihapus, hapus juga file gambar
            if gambar_filename:
                gambar_path = os.path.join(app.config['UPLOAD_FOLDER'], gambar_filename)
                if os.path.exists(gambar_path):
                    os.remove(gambar_path)

            return jsonify({"result": "success"})
        else:
            return jsonify({"result": "fail", "msg": "Accommodation not found"})
    except Exception as e:
        return jsonify({"result": "fail", "msg": str(e)})

@app.route('/accommodation/<accommodation_id>')
def accommodation_detail(accommodation_id):
    accommodation = db.penginapan.find_one({"_id": ObjectId(accommodation_id)})
    return render_template('detail_penginapan_admin.html', accommodation=accommodation)

@app.route('/edit_penginapan/<id>', methods=['GET', 'POST'])
def edit_penginapan(id):
    accommodation = db.penginapan.find_one({"_id": ObjectId(id)})

    if request.method == 'POST':
        nama_penginapan = request.form.get('namaPenginapan')
        lokasi = request.form.get('lokasi')
        jumlah_kamar = int(request.form.get('jumlahKamar'))
        harga = int(request.form.get('harga'))
        deskripsi = request.form.get('deskripsi')
        tempat_wisata_terdekat = request.form.get('tempatWisata')
        tempat_wisata_terdekat_list = tempat_wisata_terdekat.split(',')

        if 'gambar' in request.files:
            gambar_lama_path = os.path.join(app.config['UPLOAD_FOLDER'], accommodation['gambar'])
            os.remove(gambar_lama_path)

            gambar_baru = request.files['gambar']  
            gambar_filename_baru = secure_filename(gambar_baru.filename)
            gambar_baru.save(os.path.join(app.config['UPLOAD_FOLDER'], gambar_filename_baru))

        db.penginapan.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                'gambar': gambar_filename_baru,
                'nama': nama_penginapan,
                'lokasi': lokasi,
                'jumlah_kamar': jumlah_kamar,
                'harga': harga,
                'deskripsi': deskripsi,
                'tempat_wisata_terdekat': tempat_wisata_terdekat_list,
            }}
        )

        return redirect(url_for('accommodation_detail', accommodation_id=id))

    return render_template('edit_penginapan_admin.html', accommodation=accommodation)

# USER CUSTOMER

# Login Customer
@app.route('/login/user', methods=['GET', 'POST'])
def login_user():
    # Jika methods POST
    if request.method == 'POST':
        username_receive = request.form.get('username_give')
        password_receive = request.form.get('password_give')

        password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()

        result = db.customer.find_one({
            'username': username_receive,
            'password': password_hash,
        })

        if result is not None:
            payload = {
                
                "username": username_receive,
                "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
            }
            token = jwt.encode(
                payload,
                SECRET_KEY,
                algorithm='HS256'
            )
            return jsonify({
                "result": "success", 
                "token": token
            })
        else:
            return jsonify({
                "result": "fail", 
                "msg": "Terdapat kesalahan pada username atau Password anda!"
            })

    # GET
    msg = request.args.get('msg')
    return render_template('login_customer.html', msg=msg)


# Register Customer
@app.route('/register/user', methods=['GET', 'POST'])
def register_user():
    # Jika methods POST
    if request.method == 'POST':
        username_receive = request.form.get('username_give')
        password_receive = request.form.get('password_give')
        password2_receive = request.form.get('password2_give')

        # Cek password apakah sudah sama dengan konfirmasi password
        if password_receive != password2_receive:
            return jsonify({'result': 'error', 'msg': 'Kata sandi dan konfirmasi tidak cocok!'})

        # Hashing password
        password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()

        # Tambahkan data lainnya yg diperlukan user
        doc = {
            'username': username_receive,                              
            'password': password_hash,
        }

        # Masukkan data ke database
        db.customer.insert_one(doc)

        return jsonify({'result': 'success'})

    #  Jika methods GET
    msg = request.args.get('msg')
    return render_template('register_customer.html', msg=msg)

# ini Pencarian
@app.route('/pencarian', methods=['GET'])
def pencarian():
    token_receive = request.cookies.get(TOKEN_KEY)
    pencarian = request.args.get('pencarian')

    accommodations_per_page = 3
   
    page = request.args.get('page', 1, type=int)

    start_index = (page - 1) * accommodations_per_page
    end_index = start_index + accommodations_per_page

    if not pencarian:
        all_accommodations = list(db.penginapan.find())
    else:
        all_accommodations = list(db.penginapan.find({
            'tempat_wisata_terdekat': {
                '$regex': f'.*{pencarian}.*',
                '$options': 'i'
            }
        }))

    paginated_accommodations = all_accommodations[start_index:end_index]

    total_pages = (len(all_accommodations) + accommodations_per_page - 1) // accommodations_per_page

    return render_template('pencarian_customer.html', accommodations=paginated_accommodations, current_page=page, total_pages=total_pages)

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)

