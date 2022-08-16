# import xml.sax
# # from xml.etree import ElementTree as ET


# # Try reducing tokens (eg: ignore tokens with length > 70)

# file = './data/enwiki-20220720-pages-articles-multistream15.xml-p15824603p17324602'

# # Index Creator
# class MyHandler(xml.sax.handler.ContentHandler):
#     def __init__(self):
#         self._charBuffer = []
#         self._result = []

#     def _getCharacterData(self):
#         data = ''.join(self._charBuffer).strip()
#         self._charBuffer = []
#         return data.strip()

#     def parse(self, f):
#         xml.sax.parse(f, self)
#         self.parse()
#         return self._result

#     def characters(self, data):
#         self._charBuffer.append(data)

#     def startElement(self, name, attrs):
#         if name == 'mediawiki':
#             self._result.append({})

#     def endElement(self, name):
#         if not name == 'mediawiki':
#             self._result[-1][name] = self._getCharacterData()

#     def parser(self):
#         files = []
#         file = open()

# # A list of all jobs
# jobs = MyHandler().parse(file)
# print(jobs)

# # if (__name__ == "__main__"):

# #     etree = ET.parse(file)
# #     jobtitle = etree.findall('.//title')
# #     print(jobtitle)
# q


import xml.sax


class MovieHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.CurrentData = ""
        self.type = ""
        self.format = ""
        self.year = ""
        self.rating = ""
        self.stars = ""
        self.description = ""

    # Call when an element starts
    def startElement(self, tag, attributes):
        self.CurrentData = tag
        if tag == "movie":
            print("*****Movie*****")
            title = attributes["title"]
            print("Title:", title)

    # Call when an elements ends

    def endElement(self, tag):
        if self.CurrentData == "type":
            print("Type:", self.type)
        elif self.CurrentData == "format":
            print("Format:", self.format)
        elif self.CurrentData == "year":
            print("Year:", self.year)
        elif self.CurrentData == "rating":
            print("Rating:", self.rating)
        elif self.CurrentData == "stars":
            print("Stars:", self.stars)
        elif self.CurrentData == "description":
            print("Description:", self.description)
        self.CurrentData = ""

    # Call when a character is read
    def characters(self, content):
        if self.CurrentData == "type":
            self.type = content
        elif self.CurrentData == "format":
            self.format = content
        elif self.CurrentData == "year":
            self.year = content
        elif self.CurrentData == "rating":
            self.rating = content
        elif self.CurrentData == "stars":
            self.stars = content
        elif self.CurrentData == "description":
            self.description = content

if (__name__ == "__main__"):

    # create an XMLReader
    parser = xml.sax.make_parser()
    # turn off namepsaces
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    # override the default ContextHandler
    Handler = MovieHandler()
    parser.setContentHandler(Handler)
    parser.parse("movies.xml")
