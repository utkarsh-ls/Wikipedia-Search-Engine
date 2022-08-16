import sys
import xml.sax
import re
import json
import subprocess
import os

import index


class MyHandler(xml.sax.handler.ContentHandler):

    def __init__(self, stats, path='./index/', save=False):
        # create an XMLReader
        self.parser = xml.sax.make_parser()
        # turn off namepsaces
        self.parser.setFeature(xml.sax.handler.feature_namespaces, 0)
        # override the default ContextHandler
        self.parser.setContentHandler(self)
        # HACK
        self.save = save
        
        self.index_path = path
        self.index = index.InvertedIndex(self.index_path, stats)

        self.current = {
            'doc_id': 0,
            'tokens': 0,
            'tag': '',
            'content': '',
            'title': ''
        }

        self.irrelevant_tokens = ['siteinfo',
                                  'sitename',
                                  'dbname',
                                  'base',
                                  'generator',
                                  'case',
                                  'namespaces',
                                  'namespace']

        # lemmatizer
        # self.lemmatizer = WordNetLemmatizer()
        # Stemmer
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
        # self.reference_regex = re.compile(r"=+references=+|=+notes=+|=+footnotes=+")

        # Total tokens
        self.tot_tokens = 0

    # Function called for parsing input
    def parse(self, f):
        self.parser.parse(f)

    # Call when a character is read
    def characters(self, data):
        if self.current['tag'] == 'title':
            self.current['title'] += data.lower()
        elif self.current['tag'] in self.irrelevant_tokens:
            pass
        else:
            self.current['content'] += data.lower()

    # Call when an element starts
    def startElement(self, name, attrs):
        # HACK
        # print('# Tag: ', name)
        self.current['tag'] = name

    # Call when an elements ends
    def endElement(self, name):
        if name == 'page':
            self.indexer()
            self.current['tokens'] += 0
            self.current['doc_id'] += 1
            self.current['title'] = ''
            self.current['content'] = ''
            if self.save==True:
                with open('posting_list.json', 'a+') as fd:
                    json.dump(self.pl, fd)
                    fd.write('\n')

    def finish_indexing(self):
        # Set token count for BM-25
        self.index.cleanup(self.tot_tokens)

    # Remove stopwords and/or perform stemming+cleaning
    def tokenizer(self, text, remove_stopwords=True, do_stemming=True):
        text = set(text)

        if remove_stopwords is True:
            text = text - self.stopwords
        # print('=================================================')
        # print(text)
        # print('-------------------------------------------------')
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

    # Add tags to terms
    def add_tags(self, tokens, tag, tokenize=True):
        for tok in tokens:
            if tokenize is True:
                format_data = set()
                for _tok in self.token_regex.split(tok):
                    if _tok != '':
                        format_data.add(_tok)
                _tokens = self.tokenizer(format_data)
            else:
                _tokens = [tok]

            for _tok in _tokens:
                if _tok in self.pl:
                    if tag not in self.pl[_tok]:
                        self.pl[_tok] += tag
                else:
                    try:
                        self.pl[_tok] = '1:' + tag
                    except Exception as e:
                        print('LOG ERROR(add_tags): ',e)
                        pass

    # Indexing of parsed content
    def indexer(self):
        self.pl = {}
        
        # create tokens for content
        # Add title thrice to increase TF
        data = self.current['content'] + (' '+self.current['title'].strip())*3
        format_data = set()
        for tok in self.token_regex.split(data):
            if tok != '':
                format_data.add(tok)
        content_tokens = self.tokenizer(format_data)
        self.current['tokens'] += len(content_tokens)
        self.tot_tokens += len(content_tokens)

        for tok in content_tokens:
            if tok in self.pl:
                self.pl[tok] += 1
            else:
                self.pl[tok] = 1

        for tok in self.pl:
            self.pl[tok] = str(self.pl[tok]) + ':'

        # create tokens for title
        data = self.current['title']
        format_data = set()
        for tok in self.token_regex.split(data):
            if tok != '':
                format_data.add(tok)
        title_tokens = self.tokenizer(format_data, do_stemming=False)

        for tok in title_tokens:
            if tok in self.pl:
                self.pl[tok] = str(self.pl[tok]) + 't'
            else:
                self.pl[tok] = '1:t'

        # parse infobox
        infobox = self.infobox_regex.findall(self.current['content'])

        # infoboxes can be recursive, so parse depth
        infobox_data = []
        for cont in infobox:
            dep = 1
            _cont = cont[0]

            try:
                for i in range(len(_cont)):
                    if _cont[i] == '{' and _cont[i + 1] == '{':
                        i += 1
                        dep += 1
                    if _cont[i] == '}' and _cont[i + 1] == '}':
                        i += 1
                        dep -= 1
                        if dep == 0:
                            infobox_data.append(_cont[:i - 1])
                            break
            except:
                continue
        self.add_tags(infobox_data, 'i')

        # parse categories
        categories = self.categories_regex.findall(self.current['content'])
        self.add_tags(categories, 'c')

        # parse references
        references = self.references_regex.findall(self.current['content'])
        self.add_tags(references, 'r')

        # parse external links
        content = self.external_regex.split(self.current['content'])
        links = []
        if len(content) > 1:
            content = content[1].split("\n")
            for l in content:
                # print(l)
                if l and l[0] == "*":
                    _links = self.links_regex.findall(l)
                    # print("11111111111111111111111111111111111111111111111111111111111")
                    # print(_links)
                    # print("22222222222222222222222222222222222222222222222222222222222")
                    for link in _links:
                        links.append(link)
        # Don't tokenize links
        self.add_tags(links, 'l', tokenize=False)

        # print(self.current['content'])
        # print()
        # print(self.pl)
        self.index.addDoc(self.current['doc_id'],
                           self.current['title'].strip(), self.current['tokens'])

        for tok in self.pl:
            fields = self.pl[tok].split(':')
            self.index.addWord(tok, self.current['doc_id'],
                                int(fields[0]), fields[1])
        

if __name__ == "__main__":
    subprocess.run(['python3', 'initializer.py'])
    from nltk.corpus import stopwords
    # from nltk.stem import WordNetLemmatizer
    import Stemmer

    dump_file = sys.argv[1]
    index_fold_path = sys.argv[2]
    stat_file = sys.argv[3]
    handler = MyHandler(path=index_fold_path, stats=stat_file)
    handler.parse(dump_file)
    # BUG: Uncomment this ↓ later
    handler.finish_indexing()
