import urllib3
import zipfile
import os
import datetime
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO
import requests

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

fiberCopPage = 'https://www.fibercop.it/chi-siamo/verifica-la-tua-copertura/'
stringHtml = 'Elenco CRO/CNO attivi'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
}

def fetch_data():
    try:
        print('Downloading started')
        reqHtml = requests.get(fiberCopPage, headers=headers, verify=False)
        reqHtml.raise_for_status()

        soup = BeautifulSoup(reqHtml.content, 'html.parser')

        # Find the link to the ZIP file
        for a in soup.find_all('a', href=True, string=stringHtml):
            urlZip = a['href']
            break  # Assuming there's only one link matching the criteria
        
        if urlZip is not None:
            print('Downloading from URL: ' + urlZip)
            # Fetch the ZIP file content
            req = requests.get(urlZip, headers=headers, verify=False)
            return req.content
        
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None

def process_data(zip_content):
    tempFolder = '/tmp'
    if not os.path.exists(tempFolder):
        os.makedirs(tempFolder)

    with zipfile.ZipFile(BytesIO(zip_content)) as zipObj:
        zipObj.extractall(tempFolder)
        for file in os.listdir(tempFolder):
            if file.endswith(".csv"):
                csvpath = os.path.join(tempFolder, file)
                cTime = os.path.getctime(csvpath)
                cTimeFormatted = datetime.datetime.fromtimestamp(cTime)

                print("CSV Creation Date: ", cTimeFormatted)
                break

    if not csvpath:
        raise Exception("No CSV Found!")
        
    # Load only necessary columns
    columns = ['PROVINCIA', 'COMUNE', 'LATITUDINE', 'LONGITUDINE', 'CENTRALE_TX_DI_RIF', 'ID_ELEMENTO',
               'TIPO', 'TIPOLOGIA_CRO', 'STATO', 'INDIRIZZO', 'DATA_PUBBLICAZIONE']
    list_cantieri = pd.read_csv(csvpath, delimiter=';', usecols=columns).dropna()
    list_cantieri = list_cantieri.sort_values(by=['PROVINCIA', 'COMUNE', 'INDIRIZZO'])

    return list_cantieri.to_dict(orient='records')

if __name__ == "__main__":
    zip_content = fetch_data()
    
    if zip_content is not None:
        data = process_data(zip_content)
        # Save data to a JSON file
        with open('data.json', 'w') as f:
            import json
            json.dump({"data": data}, f)
