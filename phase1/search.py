import sys
import os
import glob
import re
import time
import numpy as np
import heapq

from nltk.corpus import stopwords
import Stemmer

from index import DOC_BLOCK_SIZE

NUM_RESULTS = [100, 10]
TOT_DOCS = 50000000

# For storing docs and tfs, given query
class QDoc():
    def __init__(self, doc_id, is_field_query, num_words=-1):
        self.doc_id = doc_id
        self.is_field_query = is_field_query
        self.terms = []
        # Term format { 'token', 'tf', 'fields', 'posting_list_size' }
        self.num_words = num_words
    
    # Add a query word in the document
    def addQuerryWord(self, token, tf, fields, pl_size):
        term = [token, tf, fields, pl_size]
        self.terms.append(term)
    
    # Calculate the TF-IDF score for the document
    def calculateScore(self, field_weights):
        score = 0
        # print(self.terms)
        for term in self.terms:
            pl_size = term[3]
            idf = np.log(TOT_DOCS/pl_size)
            fields = term[2]
            
            # Add Body frequency
            tf = 0
            if self.is_field_query:
                if 'b' in fields:
                    tf = int(term[1])
            else:
                tf = int(term[1])
            
            # Add frequency for other fields (t, i, c, l, r)
            for field in fields:
                field = field+':'
                tf += field_weights[field]
            # For the 100 docs, divide tf by num_words
            # (to improve the relevance by penalizing long docs)
            if self.num_words != -1:
                tf /= self.num_words

            score += idf * tf
        
        score = np.log(score)
        return score

class QueryParser():
    def __init__(self, argv):
        # Location of the query file
        self.query_file = argv[0]
        
        # Directory path for the index files
        self.index_path = './index/'
        # Directory path for the doc-title files
        self.doc_path = './doc/'
        # Directory for secondary index
        self.sec_dir = './secondary/'
        # Filename for secondary file index
        self.sec_file_path = os.path.join(self.sec_dir, 'secondary.txt')
        
        # Query results file
        self.query_results_file = os.path.join('./queries_op.txt')
        if os.path.exists(self.query_results_file):
            os.remove(self.query_results_file)
        
        # stemmer
        self.stemmer = Stemmer.Stemmer('english')
        # stopwords
        self.stopwords = set(stopwords.words('english'))

        self.fields = ['t:','b:','i:','c:','l:','r:']

        self.field_weights = {
            't:': 100,
            'b:': 1,
            'i:': 40,
            'c:': 40,
            'l:': 10,
            'r:': 10
        }

        # REGEX
        self.categories_regex = re.compile(r"\[\[category:(.*)\]\]")
        self.external_regex = re.compile(r"=+external links=+")
        self.infobox_regex = re.compile(r"{{infobox((.|\n)*)}}\n")
        self.links_regex = re.compile(r"(https?://\S+)")
        self.references_regex = re.compile(r"\{\{cite(.*?)\}\}")
        self.token_regex = re.compile(r"[^a-z0-9]+")
        self.field_regex = re.compile(r"([tbiclr]:)")
        self.ignore_regex = [
            # Alphanumeric
            re.compile(
                r"\b((\w*[0-9]\w*)(\w*[a-z]\w*))|((\w*[a-z]\w*)(\w*[0-9]\w*))\b"),
            # Numbers <= 3 digits
            re.compile(r"\b[0-9]{1,3}\b"),
            # Numbers 4 digits, greater than 2022, less than 1000
            re.compile(r"\b(?:0(?:[0-9]{3})|20[3-9][0-9]|202[3-9]|[3-9][0-9]{3})\b"),
            # Numbers >= 5 digits
            re.compile(r"\b[0-9]{5,}\b"),
            # Letters = 1 char
            re.compile(r"\b[a-z]{1}\b"),
            # Letters >= 15 chars
            re.compile(r"\b[a-z]{15,}\b")
        ]

        self.is_field_query = False
        self.doc_count = 0
        self.docs = []
        self.doc_titles = []
        self.pl = {}

    # Parse Queries in the query file
    def parse_queries(self):
        self.queries = []
        with open(self.query_file, 'r') as f:
            queries = f.readlines()
            for query in queries:
                self.queries.append(query[:-1].lower())

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

    # Retrieve the index file name from secondary index
    def getIndexFileName(self, token_list):
        n = len(token_list)
        tokens_found = 0
        with open(self.sec_file_path, 'r') as f:
            line = f.readline()
            prev_filename, prev_token = line[:-1].split(';')
            line = f.readline()
            if line == '':
                for tok in token_list:
                    token_list[tok] = prev_filename
                tokens_found = n
            else:
                while line != '' and tokens_found < n:
                    cur_filename, cur_token = line[:-1].split(';')
                    for tok in token_list:
                        if prev_token<=tok and cur_token>tok and token_list[tok]=='':
                            token_list[tok] = prev_filename
                            tokens_found += 1
                    prev_filename, prev_token = cur_filename, cur_token
                    line = f.readline()
                for tok in token_list:
                    if token_list[tok]=='':
                        tokens_found += 1
                        token_list[tok] = prev_filename
        
        return token_list

    # Find the set of documents in posting list
    # and their corresponding term freq.
    def findDocumentSet(self):
        self.doc_set = set()
        self.doc_id_set = set()
        for tok, pl in self.pl.items():
            terms = pl.split(';')
            pl_size = len(terms[1:])
            for term in terms[1:]:
                doc_id, tf, fields = term.split(':')
                if self.is_field_query is True:
                    fields = self.token_queries[tok]
                if doc_id in self.doc_id_set:
                    doc = next(filter(lambda x: x.doc_id == doc_id, self.doc_set))
                    doc.addQuerryWord(tok, tf, fields, pl_size)
                else:
                    doc = QDoc(doc_id, self.is_field_query)
                    doc.addQuerryWord(tok, tf, fields, pl_size)
                    self.doc_set.add(doc)
                    self.doc_id_set.add(doc_id)

    def addWordCount(self):
        # Reduce the set of documents to the top NUM_RESULTS[0] = 100
        top_doc_set = set()
        for doc_id in self.docs:
            doc = next(filter(lambda x: x.doc_id == doc_id, self.doc_set))
            top_doc_set.add(doc)
        self.doc_set = top_doc_set
        
        # Now retrieve the num_words for each doc
        itr = 0
        while itr < len(self.docs):
            doc_id = self.docs[itr]
            doc_file = self.findDocFile(doc_id)
            doc_file_name = os.path.join(self.doc_path, doc_file)
            curr_doc_file = doc_file

            with open(doc_file_name, 'r') as f:
                line = f.readline()
                while line != '':
                    terms = line[:-1].split(';')
                    id = terms[0]
                    if id == doc_id:
                        doc = next(filter(lambda x: x.doc_id == doc_id, self.doc_set))
                        wc = int(terms[1])
                        doc.num_words = wc

                        # Get info of next doc
                        itr += 1
                        if itr >= len(self.docs):
                            break
                        # Break if need to read diff. file (self.docs is sorted)
                        doc_id = self.docs[itr]
                        doc_file = self.findDocFile(doc_id)
                        doc_file_name = os.path.join(self.doc_path, doc_file)
                        if doc_file != curr_doc_file:
                            break
                        
                    line = f.readline()
            
            if itr >= len(self.docs):
                break

    # Retrieve NUM_RESULTS[level=>0/1] most relevant documents
    # based in their score
    def ranker(self, level):
        heap = []
        self.docs = []
        for doc in self.doc_set:
            score = doc.calculateScore(self.field_weights)
            heap.append([score, doc.doc_id])
        heapq._heapify_max(heap)
        
        # Get the top NUM_RESULTS[level] results
        while len(heap)>0 and len(self.docs)<NUM_RESULTS[level]:
            score, doc = heap[0]
            self.docs.append(doc)
            heapq._heappop_max(heap)
        self.docs = sorted(self.docs)

    # Function to find in which doc file the document is located
    def findDocFile(self, doc_id):
        doc_id = int(doc_id, 36)
        filename = 'doc'+str(doc_id//DOC_BLOCK_SIZE).zfill(6)
        return filename

    # Find the titles for the docuements (using id)
    def findDocTitles(self):
        # Find which pages (doc-title files) are relevant
        self.doc_pages = {}
        for doc_id in self.docs:
            doc_file = self.findDocFile(doc_id)
            if doc_file not in self.doc_pages:
                self.doc_pages[doc_file] = [doc_id]
            else:
                self.doc_pages[doc_file].append(doc_id)
        
        # Get the titles from the relevant pages
        for doc_file in self.doc_pages:
            doc_file_name = os.path.join(self.doc_path, doc_file)
            with open(doc_file_name, 'r') as f:
                line = f.readline()
                while line != '':
                    terms = line[:-1].split(';')
                    id = terms[0]
                    wc = terms[1]
                    title = ';'.join(terms[2:])
                    if id in self.doc_pages[doc_file]:
                        self.doc_titles.append([id, title])
                    line = f.readline()
        
    def run(self):
        for query in self.queries:
            print('Parsing Query:',query,'...')
            start_time = time.time()
            self.doc_count = 0
            self.doc_titles = []
            self.is_field_query = False
            self.pl = {}
            
            if query[:2] in self.fields:
                self.is_field_query = True
            if self.is_field_query == True:
                format_data = {
                    't': set(),
                    'b': set(),
                    'i': set(),
                    'c': set(),
                    'l': set(),
                    'r': set()
                }
                field = ''
                for tok in self.field_regex.split(query):
                    if tok != '':
                        if tok in self.fields:
                            field = tok[0]
                        elif field!='':
                            for _tok in self.token_regex.split(tok):
                                if _tok != '':
                                    format_data[field].add(_tok)
                            field=''
                
                # Stores mapping of tokens => query field
                self.token_queries = {}
                # Stores the index file name of each token
                token_list = {}
                for key in format_data:
                    if len(format_data[key]) != 0:
                        toks = self.tokenizer(format_data[key])
                        for tok in toks:
                            token_list[tok] = ''
                            if tok in self.token_queries:
                                self.token_queries[tok]+=key
                            else:
                                self.token_queries[tok] = key
                
                # Retrieve the Index File Name
                index_file_map = self.getIndexFileName(token_list)
                # print(index_file_map)
                
            else:
                format_data = set()
                for tok in self.token_regex.split(query):
                    if tok != '':
                        format_data.add(tok)
                tokens = self.tokenizer(format_data)
                
                # Stores the index file name of each token
                token_list = {}
                for tok in tokens:
                    token_list[tok] = ''
                index_file_map = self.getIndexFileName(token_list)
                # print(index_file_map)

            # Store set of index files to be opened
            # for retrieving the posting_list/word
            index_files = set()
            for tok, file in index_file_map.items():
                index_files.add(file)
            # print(index_files)

            # Store which tokens to look for in each index file
            tok_in_index = {}
            for tok, file in index_file_map.items():
                if file in tok_in_index:
                    tok_in_index[file].append(tok)
                else:
                    tok_in_index[file] = [tok]
            # print(tok_in_index)

            # Retrieve the posting list for each token
            for i_file in index_files:
                filepath = self.index_path + i_file
                with open(filepath, 'r') as f:
                    line = f.readline()
                    while line != '':
                        tok = line[:-1].split(';')[0]
                        if tok in tok_in_index[i_file]:
                            self.pl[tok] = line[:-1]
                        line = f.readline()
            # print(self.pl)

            # Get the set of documents given the posting list
            self.findDocumentSet()

            # Score the documents
            self.ranker(0)
            self.addWordCount()
            self.ranker(1)

            # Find the titles for the documents
            self.findDocTitles()
            print(self.doc_titles, '\n')

            end_time = time.time()
            with open(self.query_results_file, 'a') as f:
                for doc in self.doc_titles:
                    string = ', '.join(doc)
                    f.write(str(string)+'\n')
                Δt = end_time-start_time
                f.write(str(Δt)+'\n')
                f.write('\n')

if __name__ == "__main__":
    query_handler = QueryParser(argv=sys.argv[1:])
    query_handler.parse_queries()
    query_handler.run()
