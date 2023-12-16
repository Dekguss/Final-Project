
                        # if "profile_give" in request.files:
                        #     file = request.files.get('profile_give')
                        #     filename = secure_filename(file.filename)
                        #     extension = filename.split(".")[-1]
                        #     file_path = f"profile_images/{payload['username']}.{extension}"
                        #     file.save(os.path.join(app.config['PROFILE_IMAGES_FOLDER'], file_path))
                        #     new_doc["profile_pic"] = filename
                        #     new_doc["profile_pic_real"] = file_path

                        # if "banner_give" in request.files:
                        #     file = request.files.get('banner_give')
                        #     filename = secure_filename(file.filename)
                        #     extension = filename.split(".")[-1]
                        #     file_path = f"banner_images/{payload['username']}.{extension}"
                        #     file.save(os.path.join(app.config['BANNER_IMAGES_FOLDER'], file_path))
                        #     new_doc["banner_pic"] = filename
                        #     new_doc["banner_pic_real"] = file_path