from flask import Flask, request, render_template, redirect, url_for, jsonify, make_response, current_app
from pymongo import MongoClient
import requests
import hashlib
from datetime import datetime
from bson import ObjectId
import jwt
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os

from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['PENGINAPAN_IMAGES_FOLDER'] = './static/penginapan_images'
app.config['PROFILE_IMAGES_FOLDER'] = './static/profile_images'
app.config['BANNER_IMAGES_FOLDER'] = './static/banner_images'

SECRET_KEY = os.environ.get("SECRET_KEY")
TOKEN_KEY = os.environ.get("TOKEN_KEY")


# HOME
@app.route('/')
def home():
    token_receive = request.cookies.get(TOKEN_KEY)

    # Mengambil data penginapan dari database
    penginapan = list(db.penginapan.find())

    # Jika belum login
    if token_receive is None:
        logged_in=False
        return render_template('index.html', logged_in=logged_in, penginapan=penginapan)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        # Pastikan payload memiliki username sebelum mencari data customer
        if 'username' in payload:
            user_info = db.customer.find_one({"username": payload['username']})
            logged_in = True
            return render_template('index.html', user_info=user_info, logged_in=logged_in, penginapan=penginapan)
        else:
            logged_in = False
            return render_template('index.html', logged_in=logged_in, penginapan=penginapan)
        
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
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        # Pengecekan ID di payload
        if 'id' in payload:
            user_info = db.admin.find_one({"id": payload["id"]})
            penginapan = list(db.penginapan.find()) # Mengambil data penginapan dari database
            return render_template("dasboard_admin.html", user_info=user_info, penginapan=penginapan)
   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login_admin", msg="Token login anda sudah kedaluarsa!"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login_admin", msg="Terdapat masalah saat anda login!"))


@app.route('/tambah/penginapan', methods=['GET', 'POST'])
def tambah_penginapan():
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        # Pengecekan ID di payload
        if 'id' in payload:
            # Jika method POST
            if request.method == 'POST':
                # Mengambil data dari form
                nama_penginapan = request.form.get('namaPenginapan')
                lokasi = request.form.get('lokasi')
                jumlah_kamar = int(request.form.get('jumlahKamar'))
                harga = int(request.form.get('harga'))
                deskripsi = request.form.get('deskripsi')
                tempat_wisata_terdekat = request.form.get('tempatWisata').split(',')

                file_path = None 

                if "gambar" in request.files:
                    file = request.files.get('gambar')  # Mengambil data dari file yang diupload
                    filename = secure_filename(file.filename) # Bersihkan nama file
                    extension = filename.split(".")[-1]
                    # Simpan pada folder
                    new_filename = f"{nama_penginapan.replace(' ', '_').lower()}_penginapan.{extension}"
                    file_path = new_filename 
                    file.save(os.path.join(app.config['PENGINAPAN_IMAGES_FOLDER'], new_filename))
                
                # Tambahkan penginapan pada databse
                db.penginapan.insert_one({
                    'gambar': file_path,
                    'nama': nama_penginapan,
                    'lokasi': lokasi,
                    'jumlah_kamar': jumlah_kamar,
                    'harga': harga,
                    'deskripsi': deskripsi,
                    'tempat_wisata_terdekat': tempat_wisata_terdekat,
                })

                # Kembali ke halaman dashboard admin
                return redirect('/admin')
            # Jika method GET maka akan dibawa ke halaman tambah penginapan
            else:
                return render_template('tambah_penginapan.html')

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('admin'))


@app.route('/delete/penginapan/<penginapan_id>', methods=['DELETE'])
def hapus_penginapan(penginapan_id):
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        # Pengecekan ID di payload
        if 'id' in payload:
            # Dapatkan nama file gambar sebelum menghapus penginapan
            penginapan = db.penginapan.find_one({"_id": ObjectId(penginapan_id)})
            gambar_filename = penginapan.get('gambar', None)

            # Hapus penginapan dari database
            result = db.penginapan.delete_one({"_id": ObjectId(penginapan_id)})

            if result.deleted_count > 0:
                # Jika penginapan berhasil dihapus, hapus juga file gambar
                if gambar_filename:
                    gambar_path = os.path.join(app.config['PENGINAPAN_IMAGES_FOLDER'], gambar_filename)
                    if os.path.exists(gambar_path):
                        os.remove(gambar_path)
                return jsonify({"result": "success"})

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('admin'))


@app.route('/penginapan/<penginapan_id>')
def penginapan_detail_admin(penginapan_id):
    # Mengambil data penginapan dari database
    penginapan = db.penginapan.find_one({"_id": ObjectId(penginapan_id)})
    return render_template('detail_penginapan_admin.html', penginapan=penginapan)


@app.route('/edit_penginapan/<penginapan_id>', methods=['GET', 'POST'])
def edit_penginapan(penginapan_id):
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        # Pengecekan ID di payload
        if 'id' in payload:
            # Ambil data penginapan berdasarkan ID
            penginapan = db.penginapan.find_one({'_id': ObjectId(penginapan_id)})

            if request.method == 'POST':
                # Mengambil data dari form
                nama_penginapan = request.form.get('namaPenginapan')
                lokasi = request.form.get('lokasi')
                jumlah_kamar = int(request.form.get('jumlahKamar'))
                harga = int(request.form.get('harga'))
                deskripsi = request.form.get('deskripsi')
                tempat_wisata_terdekat = request.form.get('tempatWisata').split(',')

                file_path = penginapan['gambar']  # Gunakan gambar lama secara default

                # Jika gambar diubah
                if "gambar" in request.files:
                    file = request.files.get('gambar')
                    
                    # Jika file tidak kosong
                    if file.filename:
                        filename = secure_filename(file.filename)
                        extension = filename.split(".")[-1]
                        new_filename = f"{nama_penginapan.replace(' ', '_').lower()}_penginapan.{extension}"
                        file_path = new_filename
                        file.save(os.path.join(app.config['PENGINAPAN_IMAGES_FOLDER'], new_filename))

                        # Hapus gambar lama jika ada
                        if penginapan['gambar']:
                            os.remove(os.path.join(app.config['PENGINAPAN_IMAGES_FOLDER'], penginapan['gambar']))

                # Update penginapan pada database
                db.penginapan.update_one(
                    {'_id': ObjectId(penginapan_id)},
                    {
                        '$set': {
                            'gambar': file_path,
                            'nama': nama_penginapan,
                            'lokasi': lokasi,
                            'jumlah_kamar': jumlah_kamar,
                            'harga': harga,
                            'deskripsi': deskripsi,
                            'tempat_wisata_terdekat': tempat_wisata_terdekat,
                        }
                    }
                )

                # Kembali ke halaman dashboard admin setelah berhasil edit
                return redirect('/admin')

            # Jika method GET, tampilkan halaman edit dengan data penginapan
            else:
                return render_template('edit_penginapan_admin.html', penginapan=penginapan)

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('admin'))


@app.route('/pencarian/admin', methods=['GET'])
def cari_penginapan_admin():
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        # Pengecekan ID di payload
        if 'id' in payload:
            # Ambil kata kunci pencarian dari URL parameter
            keyword = request.args.get('pencarian')

            # Lakukan pencarian penginapan berdasarkan nama
            penginapan = list(db.penginapan.find({
                'nama': {'$regex': f'.*{keyword}.*', '$options': 'i'}
            }))

            return render_template('dasboard_admin.html', penginapan=penginapan, keyword=keyword)

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('admin'))


@app.route('/cekpesanan/admin')
def cek_pesanan_admin():
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        # Pengecekan ID di payload
        if 'id' in payload:
            user_info = db.admin.find_one({"id": payload["id"]})
            orders = list(db.pesanan.find())
            return render_template('cek_pesanan_admin.html', orders=orders)
      
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login_admin", msg="Token login anda sudah kedaluarsa!"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login_admin", msg="Terdapat masalah saat anda login!"))




# USER CUSTOMER

# Login Customer
@app.route('/login/user', methods=['GET', 'POST'])
def login_customer():
    # Jika methods POST
    if request.method == 'POST':
        username_receive = request.form.get('username_give')
        password_receive = request.form.get('password_give')

        password_hash = hashlib.sha256(
            password_receive.encode("utf-8")).hexdigest()

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
                "msg": "Terdapat kesalahan pada Username atau Password anda!"
            })

    # Jika method GET
    msg = request.args.get('msg')
    return render_template('login_customer.html', msg=msg)


# Register Customer
@app.route('/register/user', methods=['GET', 'POST'])
def register_user():
    # Jika methods POST
    if request.method == 'POST':
        username_receive = request.form.get('username_give')
        email_receive = request.form.get('email_give')
        password_receive = request.form.get('password_give')

        # Hashing password
        password_hash = hashlib.sha256(
            password_receive.encode("utf-8")).hexdigest()

        # Data yang akan disimpan
        doc = {
            'username': username_receive,
            'email': email_receive,
            'password': password_hash,
            'nama': username_receive,
            'profile_pic': '',
            'profile_pic_real': 'profile_images/default_profile.jpg',
            'banner_pic': '',
            'banner_pic_real': 'banner_images/default_banner.jpg',
        }

        # Masukkan data ke database
        db.customer.insert_one(doc)

        return jsonify({'result': 'success'})

    # Jika methods GET
    msg = request.args.get('msg')
    return render_template('register_customer.html', msg=msg)


@app.route('/detail_customer/<penginapan_id>')
def penginapan_detail_customer(penginapan_id):
    token_receive = request.cookies.get(TOKEN_KEY)

    # Mengambil data penginapan dari database
    penginapan = db.penginapan.find_one({"_id": ObjectId(penginapan_id)})

    # Jika belum login
    if token_receive is None:
        logged_in=False
        return render_template('detail_penginapan_customer.html', logged_in=logged_in, penginapan=penginapan)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        # Pastikan payload memiliki username sebelum mencari data customer
        if 'username' in payload:
            user_info = db.customer.find_one({"username": payload['username']})
            logged_in = True
            return render_template('detail_penginapan_customer.html', user_info=user_info, logged_in=logged_in, penginapan=penginapan)
        else:
            logged_in = False
            return render_template('detail_penginapan_customer.html', logged_in=logged_in, penginapan=penginapan)
        
    except jwt.ExpiredSignatureError:
        msg = 'Token login anda sudah kedaluarsa!'
    except jwt.exceptions.DecodeError:
        msg = 'Terdapat masalah saat anda login!'
        logged_in = False
    return render_template('detail_penginapan_customer.html', msg=msg, logged_in=logged_in)


@app.route('/pencarian', methods=['GET'])
def pencarian():
    token_receive = request.cookies.get(TOKEN_KEY)
    pencarian = request.args.get('pencarian')

    penginapan_per_page = 3

    page = request.args.get('page', 1, type=int)

    start_index = (page - 1) * penginapan_per_page
    end_index = start_index + penginapan_per_page

    if not pencarian:
        all_penginapan = list(db.penginapan.find())
    else:
        all_penginapan = list(db.penginapan.find({
            'tempat_wisata_terdekat': {
                '$regex': f'.*{pencarian}.*',
                '$options': 'i'
            }
        }))

    paginated_penginapan = all_penginapan[start_index:end_index]

    total_pages = (len(all_penginapan) + penginapan_per_page - 1) // penginapan_per_page

    if token_receive:
        try:
            payload = jwt.decode(
                token_receive,
                SECRET_KEY,
                algorithms=['HS256']
            )
            if 'username' in payload:
                login_in = True
                user_info = db.customer.find_one({"username": payload['username']})
                return render_template('pencarian_customer.html', penginapan=paginated_penginapan, current_page=page, total_pages=total_pages, logged_in=login_in, user_info=user_info)

        except jwt.ExpiredSignatureError:
            return jsonify({"result": "fail", "msg": "Token login has expired."})
        except jwt.exceptions.DecodeError:
            return jsonify({"result": "fail", "msg": "Token decoding error."})

    return render_template('pencarian_customer.html', penginapan=paginated_penginapan, current_page=page, total_pages=total_pages, logged_in=False)


@app.route('/check_login')
def check_login():
    token_receive = request.cookies.get(TOKEN_KEY)
    if token_receive:
        try:
            payload = jwt.decode(
                token_receive,
                SECRET_KEY,
                algorithms=['HS256']
            )
            if 'username' in payload:
                return jsonify({'logged_in': True})

        except jwt.ExpiredSignatureError:
            return jsonify({"result": "fail", "msg": "Token login has expired."})
        except jwt.exceptions.DecodeError:
            return jsonify({"result": "fail", "msg": "Token decoding error."})

    return jsonify({'logged_in': False})


@app.route('/pesan/<penginapan_id>', methods=['POST'])
def pesan_accommodation(penginapan_id):
    token_receive = request.cookies.get(TOKEN_KEY)
    if not token_receive:
        return jsonify({"result": "fail", "msg": "Silakan login untuk melakukan pemesanan."})

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        if 'username' not in payload:
            return jsonify({"result": "fail", "msg": "Pengguna tidak valid."})

        jumlah_kamar = int(request.form.get('jumlah_kamar'))
        tgl_pesan = request.form.get('tgl_pesan')
        total_harga = int(request.form.get('total_harga'))

        accommodation = db.penginapan.find_one(
            {"_id": ObjectId(penginapan_id)})
        if accommodation:
            sisa_kamar = accommodation['jumlah_kamar'] - jumlah_kamar
            if sisa_kamar >= 0:
                db.penginapan.update_one(
                    {"_id": ObjectId(penginapan_id)},
                    {"$set": {'jumlah_kamar': sisa_kamar}}
                )

                db.pesanan.insert_one({
                    'penginapan_id': ObjectId(penginapan_id),
                    'status': 'pending',
                    'gambar': accommodation['gambar'],
                    'nama_penginapan': accommodation['nama'],
                    'customer_username': payload['username'],
                    'jumlah_kamar': jumlah_kamar,
                    'tgl_pesan': tgl_pesan,
                    'total_harga': total_harga,
                    'tgl_melakukan_pemesanan': datetime.utcnow().strftime('%Y-%m-%d')
                })

                return jsonify({"result": "success", "msg": "Pemesanan berhasil."})
            else:
                return jsonify({"result": "fail", "msg": "Jumlah kamar tidak mencukupi."})
        else:
            return jsonify({"result": "fail", "msg": "Akomodasi tidak ditemukan."})

    except jwt.ExpiredSignatureError:
        return jsonify({"result": "fail", "msg": "Token login telah kedaluwarsa."})
    except jwt.exceptions.DecodeError:
        return jsonify({"result": "fail", "msg": "Kesalahan pada saat melakukan dekode token."})


@app.route('/cekpesanan/<username>')
def user_orders(username):
    token_receive = request.cookies.get(TOKEN_KEY)
    user_orders = db.pesanan.find({'customer_username': username})
    if token_receive:
        try:
            payload = jwt.decode(
                token_receive,
                SECRET_KEY,
                algorithms=['HS256']
            )
            if 'username' in payload:
                login_in = True
                user_info = db.customer.find_one({"username": payload['username']})
                return render_template('cek_pesanan_customer.html', user_orders=user_orders, user_info=user_info, logged_in=login_in)
        except jwt.ExpiredSignatureError:
            return jsonify({"result": "fail", "msg": "Token login has expired."})
        except jwt.exceptions.DecodeError:
            return jsonify({"result": "fail", "msg": "Token decoding error."})


@app.route('/batal/pesanan/<order_id>', methods=['POST'])
def batalkan_pesanan(order_id):
    token_receive = request.cookies.get(TOKEN_KEY)

    if not token_receive:
        return jsonify({"result": "fail", "msg": "Silakan login untuk membatalkan pesanan."})

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        if 'username' not in payload:
            return jsonify({"result": "fail", "msg": "Pengguna tidak valid."})

        # Cek status pesanan sebelum membatalkan
        order = db.pesanan.find_one({"_id": ObjectId(order_id)})
        if order and order['status'] != 'canceled':
            # Dapatkan jumlah kamar yang dibatalkan
            jumlah_kamar_dibatalkan = order['jumlah_kamar']

            # Dapatkan jumlah kamar yang tersedia saat ini dari akomodasi
            penginapan_id = order['penginapan_id']
            akomodasi = db.penginapan.find_one({"_id": penginapan_id})
            jumlah_kamar_tersedia = akomodasi['jumlah_kamar']

            # Cek apakah sudah H-2 dari tanggal pemesanan
            tgl_pesan = datetime.strptime(order['tgl_pesan'], '%Y-%m-%d')
            batas_pembatalan = tgl_pesan - timedelta(days=2)
            sekarang = datetime.utcnow()

            if sekarang >= batas_pembatalan:
                return jsonify({
                    "result": "fail",
                    "msg": "Tidak dapat membatalkan pesanan kurang dari 2 hari sebelum tanggal pemesanan!",
                    "redirect_url": url_for('user_orders', username=payload['username'])
                })
                # return jsonify({"result": "fail", "msg": "Tidak dapat membatalkan pesanan kurang dari 2 hari sebelum tanggal pemesanan."})

            # Perbarui jumlah kamar pada penginapan
            db.penginapan.update_one(
                {"_id": penginapan_id},
                {"$set": {'jumlah_kamar': jumlah_kamar_tersedia + jumlah_kamar_dibatalkan}}
            )

            # Update status pesanan menjadi 'canceled'
            db.pesanan.update_one(
                {"_id": ObjectId(order_id)},
                {"$set": {'status': 'canceled'}}
            )
            return jsonify({
                "result": "success",
                "msg": "Pembatalan Berhasil!",
                "redirect_url": url_for('user_orders', username=payload['username'])
            })
            # return redirect(url_for('user_orders', username=payload['username']))
        else:
            return jsonify({"result": "fail", "msg": "Pesanan tidak ditemukan atau sudah dibatalkan."})
    except jwt.ExpiredSignatureError:
        return jsonify({"result": "fail", "msg": "Token login telah kedaluwarsa."})
    except jwt.exceptions.DecodeError:
        return jsonify({"result": "fail", "msg": "Kesalahan pada saat melakukan dekode token."})


@app.route('/hapus/pesanan/<order_id>', methods=['POST'])
def hapus_pesanan(order_id):
    token_receive = request.cookies.get(TOKEN_KEY)

    if not token_receive:
        return jsonify({"result": "fail", "msg": "Silakan login untuk menghapus pesanan."})

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        if 'username' not in payload:
            return jsonify({"result": "fail", "msg": "Pengguna tidak valid."})

        # Cek status pesanan sebelum menghapus
        order = db.pesanan.find_one({"_id": ObjectId(order_id)})
        if order and order['status'] == 'canceled':
            # Hapus pesanan
            db.pesanan.delete_one({"_id": ObjectId(order_id)})
            return jsonify({
                "result": "success",
                "msg": "Pesanan berhasil dihapus!",
                "redirect_url": url_for('user_orders', username=payload['username'])
            })
            # return redirect(url_for('user_orders', username=payload['username']))
        else:
            return jsonify({"result": "fail", "msg": "Pesanan tidak ditemukan atau sudah dihapus."})
    except jwt.ExpiredSignatureError:
        return jsonify({"result": "fail", "msg": "Token login telah kedaluwarsa."})
    except jwt.exceptions.DecodeError:
        return jsonify({"result": "fail", "msg": "Kesalahan pada saat melakukan dekode token."})


@app.route('/terima/pesanan/<order_id>', methods=['POST'])
def terima_pesanan(order_id):
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        if 'id' not in payload:
            return jsonify({"result": "fail", "msg": "Admin tidak valid."})

        order = db.pesanan.find_one({"_id": ObjectId(order_id)})
        if order and order['status'] == 'pending':
            # Update pesanan
            db.pesanan.update_one(
                {"_id": ObjectId(order_id)},
                {"$set": {'status': 'accepted'}}
            )
            return redirect(url_for('cek_pesanan_admin'))
        else:
            return jsonify({"result": "fail", "msg": "Pesanan tidak ditemukan atau sudah dihapus."})
    except jwt.ExpiredSignatureError:
        return jsonify({"result": "fail", "msg": "Token login telah kedaluwarsa."})
    except jwt.exceptions.DecodeError:
        return jsonify({"result": "fail", "msg": "Kesalahan pada saat melakukan dekode token."})


@app.route('/profile/<username>')
def view_profile(username):
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        # Pengecekan username di payload
        if 'username' in payload and payload['username'] == username:
            # Find username pada database
            user_info = db.customer.find_one({"username": username})

            return render_template('profile_customer.html', user_info=user_info)

    except jwt.ExpiredSignatureError:
        return redirect(url_for("login_customer", msg="Token login anda sudah kedaluarsa!"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login_customer", msg="Terdapat masalah saat anda login!"))



@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    token_receive = request.cookies.get(TOKEN_KEY)
    if token_receive:
        try:
            payload = jwt.decode(
                token_receive,
                SECRET_KEY,
                algorithms=['HS256']
            )

            if 'username' in payload:
                user_info = db.customer.find_one({"username": payload['username']})
                if user_info:
                    if request.method == 'POST':
                        # Mengambil data yang diperbarui dari formulir
                        updated_name = request.form.get('name_give')
                        updated_email = request.form.get('email_give')

                        # Buta penyimpanan baru untuk data
                        new_doc = {
                            "nama": updated_name,
                            "email": updated_email
                        }

                        if "profile_give" in request.files:    
                            file = request.files.get('profile_give')
                            filename = secure_filename(file.filename)
                            extension = filename.split(".")[-1]
                            file_path = os.path.join(app.config['PROFILE_IMAGES_FOLDER'], f"{payload['username']}_profile.{extension}")
                            file.save(file_path)
                            new_doc["profile_pic"] = filename
                            new_doc["profile_pic_real"] =  file_path.replace(app.config['PROFILE_IMAGES_FOLDER'], 'profile_images').replace("\\", "/")

                        if "banner_give" in request.files:
                            file = request.files.get('banner_give')
                            filename = secure_filename(file.filename)
                            extension = filename.split(".")[-1]
                            file_path = os.path.join(app.config['BANNER_IMAGES_FOLDER'], f"{payload['username']}_banner.{extension}")
                            file.save(file_path)
                            new_doc["banner_pic"] = filename

                            # Ubah path sebelum disimpan ke database
                            new_doc["banner_pic_real"] = file_path.replace(app.config['BANNER_IMAGES_FOLDER'], 'banner_images').replace("\\", "/")

                        # Update data pengguna di database
                        db.customer.update_one(
                            {"username": payload['username']},
                            {"$set": new_doc}
                        )
                        # Redirect ke halaman profil setelah pembaruan
                        return redirect(url_for('view_profile', username=payload['username']))
                    else:
                        # Tampilkan halaman edit profile jika request method adalah GET
                        return render_template('edit_profile_customer.html', user_info=user_info)
                else:
                    return render_template('edit_profile_customer.html', msg='Pengguna tidak ditemukan.')
        
        except jwt.ExpiredSignatureError:
            return redirect(url_for("login_customer", msg="Token login anda sudah kedaluarsa!"))
        except jwt.exceptions.DecodeError:
            return redirect(url_for("login_customer", msg="Terdapat masalah saat anda login!"))
            
    else:
        # Redirect ke halaman login jika tidak ada token
        return redirect(url_for('login_user'))


# Ganti Password Customer
@app.route('/ganti_password', methods=['GET', 'POST'])
def ganti_password():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        # Pengecekan username di payload
        if 'username' in payload:
            user_info = db.customer.find_one({"username": payload['username']})

            # Jika method POST
            if request.method == 'POST':
                # Mengambil data yang diperbarui dari form
                old_password = request.form.get('oldPass_give')
                new_password = request.form.get('newPass_give')

                # Cek apakah password lama yang di database sama dengan yang diinputkan
                if hashlib.sha256(old_password.encode('utf-8')).hexdigest() == user_info['password']:
                    # Hashing password baru
                    hash_password = hashlib.sha256(new_password.encode('utf-8')).hexdigest()

                    # Update data pada database
                    db.customer.update_one(
                        {"username": payload['username']},
                        {"$set": {'password': hash_password}}
                    )

                    return jsonify({'status': 'success', 'msg': 'Password berhasil diperbarui!'})
                else:
                    return jsonify({'status': 'error', 'msg': 'Password lama tidak sesuai.'})

             # Jika method GET maka tampilkan halaman ganti password 
            else:
                return render_template('ganti_password.html', user_info=user_info)

    except jwt.ExpiredSignatureError:
        return redirect(url_for("login_customer", msg="Token login anda sudah kedaluarsa!"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login_customer", msg="Terdapat masalah saat anda login!"))


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
