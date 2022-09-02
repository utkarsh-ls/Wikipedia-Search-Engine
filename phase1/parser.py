import sys
import xml.sax
import re
import json
import subprocess
import os

import index


class MyHandler(xml.sax.handler.ContentHandler):

    def __init__(self, path='./index/', save=False):
        # create an XMLReader
        self.parser = xml.sax.make_parser()
        # turn off namepsaces
        self.parser.setFeature(xml.sax.handler.feature_namespaces, 0)
        # override the default ContextHandler
        self.parser.setContentHandler(self)
        # HACK
        self.save = save

        self.index_path = path
        self.index = index.InvertedIndex(self.index_path)

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

        self.wiki_namespaces = ['user',
                                'wikipedia',
                                'file',
                                'mediaWiki',
                                'template',
                                'help',
                                'category',
                                'portal',
                                'draft',
                                'timedText',
                                'module']
        # Lemmatizer
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
        self.token_regex = re.compile(r"[^a-z0-9]+")
        self.ignore_regex = [
            # Alphanumeric
            re.compile(
                r"\b((\w*[0-9]\w*)(\w*[a-z]\w*))|((\w*[a-z]\w*)(\w*[0-9]\w*))\b"),
            # Numbers == 3 digits
            re.compile(r"\b[0-9]{3}\b"),
            # Numbers 4 digits, greater than 2022, less than 1000
            re.compile(r"\b(?:0(?:[0-9]{3})|20[3-9][0-9]|202[3-9]|2[1-9][0-9]{2}|[3-9][0-9]{3})\b"),
            # Numbers >= 5 digits
            re.compile(r"\b[0-9]{5,}\b"),
            # Letters = 1 char
            re.compile(r"\b[a-z]{1}\b"),
            # Letters >= 15 chars
            re.compile(r"\b[a-z]{15,}\b")
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
            if self.indexer() == True:
                self.current['tokens'] = 0
                self.current['doc_id'] += 1
                self.current['title'] = ''
                self.current['content'] = ''
                if self.save == True:
                    with open('posting_list.json', 'a+') as fd:
                        json.dump(self.pl, fd)
                        fd.write('\n')
            else:
                self.current['tokens'] = 0
                self.current['title'] = ''
                self.current['content'] = ''

    def finish_indexing(self):
        self.index.cleanup(self.tot_tokens)

    # Remove stopwords and/or perform stemming+cleaning
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
            to_continue = False
            for ig in self.ignore_regex:
                if ig.match(token):
                    to_continue = True
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
                        print('LOG ERROR(add_tags): ', e)
                        pass

    # Indexing of parsed content
    def indexer(self):
        self.pl = {}

        ### Create tokens for CONTENT
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

        ### Create tokens for TITLE
        data = self.current['title']
        namespace = data.split(':')[0]
        # Don't process if article is a Wiki namespace
        if namespace in self.wiki_namespaces:
            return False
        format_data = set()
        for tok in self.token_regex.split(data):
            if tok != '':
                format_data.add(tok)
        title_tokens = self.tokenizer(format_data)

        for tok in title_tokens:
            if tok in self.pl:
                self.pl[tok] = str(self.pl[tok]) + 't'
            else:
                self.pl[tok] = '1:t'

        ### Parse INFOBOX
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

        ### Parse Categories
        categories = self.categories_regex.findall(self.current['content'])
        self.add_tags(categories, 'c')

        ### Parse References
        references = self.references_regex.findall(self.current['content'])
        self.add_tags(references, 'r')

        ### Parse External Links
        content = self.external_regex.split(self.current['content'])
        links = []
        if len(content) > 1:
            content = content[1].split("\n")
            for l in content:
                if l and l[0] == "*":
                    _links = self.links_regex.findall(l)
                    for link in _links:
                        links.append(link)
        # Don't tokenize links
        self.add_tags(links, 'l', tokenize=False)

        self.index.addDoc(self.current['doc_id'],
                          self.current['title'].strip(), self.current['tokens'])

        for tok in self.pl:
            fields = self.pl[tok].split(':')
            self.index.addWord(tok, self.current['doc_id'],
                               int(fields[0]), fields[1])

        return True


if __name__ == "__main__":
    subprocess.run(['python3', 'initializer.py'])
    from nltk.corpus import stopwords
    # from nltk.stem import WordNetLemmatizer
    import Stemmer

    dump_file = sys.argv[1]
    index_fold_path = sys.argv[2]
    handler = MyHandler(path=index_fold_path)
    handler.parse(dump_file)
    # BUG: Uncomment this ↓ later
    handler.finish_indexing()
