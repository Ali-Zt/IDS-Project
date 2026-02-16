import os
import zipfile
from kaggle.api.kaggle_api_extended import KaggleApi

def dawnload_data():
    api = KaggleApi()
    api.authenticate()
    os.makedirs("data/raw",exist_ok=True)
    dataset = "olistbr/brazilian-ecommerce"
    api.dataset_download_files(dataset, path="data/raw", unzip=True)
    print("successfull download")

if __name__ == "__main__":
    dawnload_data()
