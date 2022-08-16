import os
import heapq

INDEX_BLOCK_SIZE = 1000000
DOC_BLOCK_SIZE = 1000
MERGED_BLOCK_SIZE = 10000
MAX_POSTING_LIST_SIZE = 10000

STATS_FILE = 'stats.txt'

# Inverted Index Create/Merge


class InvertedIndex():
    def __init__(self, dirname):
        self.dir = dirname
        if self.dir[-1] != '/':
            self.dir += '/'
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

        self.doc_block_id = 0
        self.index_block_id = 0
        self.merged_index_id = 0

        self.index = {}
        self.doc_map = {}
        self.merged_index = {}

        self.current = {
            'token': 0,
            'doc': 0,
            'term': 0
        }
        self.total = {
            'token': 0,
            'doc': 0,
            'block': 0
        }

    def getDocBlockName(self, id=-1):
        if id == -1:
            name = 'doc' + str(self.doc_block_id).zfill(4)
        else:
            name = 'doc' + str(id).zfill(4)
        return name

    def getIndBlockName(self, id=-1):
        if id == -1:
            name = 'blk' + str(self.index_block_id).zfill(6)
        else:
            name = 'blk' + str(id).zfill(6)
        return name

    def getMergedIndName(self, id=-1):
        if id == -1:
            name = 'ind' + str(self.merged_index_id).zfill(6)
        else:
            name = 'ind' + str(id).zfill(6)
        return name

    def addWord(self, token, docid, TF, tags):
        post = str(docid)+':'+str(TF)+':'+tags
        if token in self.index:
            self.index[token].append(post)
        else:
            self.index[token] = [post]
            self.current['term'] += 1
            self.current['token'] += 1

            if self.current['token'] >= INDEX_BLOCK_SIZE:
                self.dumpIndexBlock()

    def dumpIndexBlock(self):
        name = self.getIndBlockName()
        file_path = os.path.join(self.dir, name)
        with open(file_path, 'w') as f:
            for key, value in sorted(self.index.items()):
                token = [key]+value
                token = ';'.join(token)
                f.write(str(token)+'\n')
        self.createNewIndexBlock()

    def createNewIndexBlock(self):
        self.index_block_id += 1
        self.current['token'] = 0
        self.index = {}

    def addDoc(self, docid, title, token_count):
        self.doc_map[docid] = str(token_count) + ';' + title
        self.current['doc'] += 1
        self.total['doc'] += 1
        if self.current['doc'] >= DOC_BLOCK_SIZE:
            self.dumpDocBlock()

    def dumpDocBlock(self):
        name = self.getDocBlockName()
        file_path = os.path.join(self.dir, name)
        with open(file_path, 'w') as f:
            for key, value in sorted(self.doc_map.items()):
                token = str(key)+value
                token = ';'.join(token)
                f.write(str(token)+'\n')
        self.createNewDocBlock()

    def createNewDocBlock(self):
        self.doc_block_id += 1
        self.current['doc'] = 0
        self.doc_map = {}

    def mergeIndexBlock(self):
        num_blocks = 1000000
        done = False
        file_iters = []

        for block in range(num_blocks):
            name = self.getIndBlockName(block)
            try:
                fd = open(os.path.join(self.dir, name), 'r')
                file_iters.append(fd)
            except:
                break

        heap = []
        entries = []
        for fd in file_iters:
            line = fd.readline()
            while line:
                words = line.strip().split(';')
                title = words[0]
                pl_size = len(words)
                if pl_size > MAX_POSTING_LIST_SIZE:
                    entry = [title]
                    for w in words[1:]:
                        _, tf, tags = w.split(':')
                        if int(tf) > 1:
                            entry.append(w)
                        elif tags:
                            entry.append(w)
                else:
                    entry = words
                entries.append(entry)
                heapq.heappush(heap, title)
                line = fd.readline()

        token_count_merged_index = 0
        while not done:
            while(len(heap) > 0 and not heap[0]):
                heapq.heappop(heap)

            try:
                front = heapq.heappop(heap)
            except:
                print("Finished indexing -------------------")
                for i in file_iters:
                    if i:
                        i.close()
                break

            while(len(heap) > 0 and heap[0] == front):
                heapq.heappop(heap)

            self.merged_index[front] = []
            token_count_merged_index += 1

            file_touched = False

            for words in entries:
                if words[0] == front:
                    file_touched = True

                    if len(words[1:]) > MAX_POSTING_LIST_SIZE:
                        for w in words[1:]:
                            _, tf, tags = w.split(':')
                            if int(tf) > 1:
                                self.merged_index[front].append(w)
                            elif tags:
                                self.merged_index[front].append(w)
                    else:
                        self.merged_index[front] += words[1:]
                        # Increment file pointer
                        try:
                            entries[i] = file_iters[i].readline(
                            ).strip().split(' ')
                            heapq.heappush(heap, entries[i][0])
                        except:
                            pass

            if token_count_merged_index > MERGED_BLOCK_SIZE:
                print('Dumping tokens -------------------')
                self.dumpMergedIndexBlock()
                token_count_merged_index = 0

            if not file_touched:
                print("LOG ERROR: No file touched")
                for i in file_iters:
                    if i:
                        i.close()
                done = True

    def dumpMergedIndexBlock(self):
        name = self.getMergedIndName()
        file_path = os.path.join(self.dir, name)
        with open(file_path, 'w') as f:
            for key, value in sorted(self.merged_index.items()):
                token = [key]+value
                token = ';'.join(token)
                f.write(str(token)+'\n')
        self.createNewMergedIndexBlock()

    def createNewMergedIndexBlock(self):
        self.merged_index_id += 1
        self.merged_index = {}

    def cleanup(self, tot_tokens):
        self.total['token'] = tot_tokens
        self.dumpIndexBlock()
        self.dumpDocBlock()
        self.total['block'] = self.index_block_id
        print("TOTAL BLOCKS CREATED " + str(self.total['block']))
        self.mergeIndexBlock()
        # Dump remaining merged indexes
        self.dumpMergedIndexBlock()

        # for block in range(self.total['block']):
        #     # Remove all blocks
        #     name = self.getIndBlockName(block)
        #     file_path = os.path.join(self.dir, name)
        #     os.remove(file_path)

        # generate stat file for implementation of BM-25
        stat_file = os.path.join(self.dir, STATS_FILE)
        with open(stat_file, "w+") as f:
            f.write("NUM_DOCS=" + str(self.total['doc']) + '\n')
            f.write("TOKEN_COUNT=" + str(self.total['token']) + '\n')
            f.write("BLOCKS_CREATED=" + str(self.total['block']) + '\n')
            f.write("MERGED_BLOCKS_CREATED=" + str(self.merged_index_id) + '\n')
            f.write("DOC_BLOCKS_CREATED=" + str(self.doc_block_id) + '\n')

        