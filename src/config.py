import os 




def load_windows_env():
    os.environ["USERPROFILE"] = r"C:\temp"
    os.environ["HOME"] = r"C:\temp"
    os.environ["TEMP"] = r"C:\temp"
    os.environ["TMP"] = r"C:\temp"
    os.environ["GDAL_DATA"] = r"C:\temp\gdal_data"
    os.makedirs(r"C:\temp", exist_ok=True)


def load_env():
    os.environ["AWS_ACCESS_KEY_ID"] = "CLZN1E05TUXMT25FJCID"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "UpTldRQnVrsx3bgplVfZQKzHgQzxAa9i576BV0oo"
    os.environ["AWS_S3_ENDPOINT"] = "eodata.dataspace.copernicus.eu"
    os.environ["AWS_VIRTUAL_HOSTING"] = "FALSE"
    os.environ["AWS_HTTPS"] = "TRUE"

