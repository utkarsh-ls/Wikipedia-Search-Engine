import subprocess

if __name__ == "__main__":
    # sudo apt-get install python3-dev
    stemmer = subprocess.run(['pip3', 'install', 'PyStemmer'])
    nltk = subprocess.run(['pip3', 'install', 'nltk'])
    if nltk.returncode==0:
        import nltk
        nltk.download('stopwords')
        # nltk.download('wordnet')
        # nltk.download('omw-1.4')
    # HACK
    else:
        print('reutrn Code: ', nltk.returncode)