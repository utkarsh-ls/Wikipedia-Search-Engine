import sys
import os
import glob
import re
from nltk.corpus import stopwords
import Stemmer
   
class QueryParser():
    def __init__(self, argv):
        self.index_path = argv[0]
        self.query = argv[1]
        
        # stemmer
        self.stemmer = Stemmer.Stemmer('english')
        # stopwords
        self.stopwords = set(stopwords.words('english'))
        # Posting List
        self.pl = {}

        # REGEX
        self.categories_regex = re.compile(r"\[\[category:(.*)\]\]")
        self.external_regex = re.compile(r"=+external links=+")
        self.infobox_regex = re.compile(r"{{infobox((.|\n)*)}}\n")
        self.links_regex = re.compile(r"(https?://\S+)")
        self.references_regex = re.compile(r"\{\{cite(.*?)\}\}")
        self.token_regex = re.compile(r"[^a-zA-Z0-9]+")
        self.ignore_regex = [
            re.compile(r"[0-9]+[a-zA-z]+"),
            re.compile(r"[a-zA-z]+[0-9]+"),
            re.compile(r"[0-9]+.{4,}"),
            re.compile(r"[a-zA-z]+[0-9]+.{4,}")
        ]

        self.doc_count = 0
        self.docs = set()
        self.doc_titles = []

    # Remove stopwords and/or perform stemming
    def tokenizer(self, text, remove_stopwords=True, do_stemming=True):
        text = set(text)

        if remove_stopwords is True:
            text = text - self.stopwords
        
        tokens = []
        for tok in text:
            if do_stemming is not True:
                tokens.append(tok)
                continue
            elif self.links_regex.match(tok):
                tokens.append(tok)
                continue

            # Cleaning
            # token = str(self.lemmatizer.lemmatize(tok))
            token = str(self.stemmer.stemWord(tok))
            to_continue=False
            for ig in self.ignore_regex:
                if ig.match(token):
                    to_continue=True
            if to_continue is True:
                continue
            tokens.append(token)

        return tokens

    def run(self):
        format_data = set()
        for tok in self.token_regex.split(self.query.lower()):
            if tok != '':
                format_data.add(tok)
        tokens = self.tokenizer(format_data)
        for filename in glob.glob(os.path.join(self.index_path, 'ind*')):
            with open(filename, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    words = line.split(';')
                    word = self.stemmer.stemWord(words[0])
                    if word in tokens:
                        self.docs = self.docs.union(set(term.split(':')[0] for term in words[1:]))
                        self.doc_count = len(self.docs)
                        if self.doc_count >= 10:
                            break
            if self.doc_count >= 10:
                            break
        
        for filename in glob.glob(os.path.join(self.index_path, 'doc*')):
            with open(filename, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    words = line.split(';')
                    id = words[0]
                    if id in self.docs:
                        title = words[2]
                        self.doc_titles.append(title[:-1])
                        if len(self.doc_titles)==10:
                            break
            if len(self.doc_titles)==10:
                            break

        return self.doc_titles


if __name__ == "__main__":
    query_handler = QueryParser(argv=sys.argv[1:])
    print(query_handler.run())