#  Search Engine for Wikipedia

## The Directory Structure

```
2019101010
├──#doc
|   ├──#doc******
├──#index
|   ├──#ind******
├──#secondary
|   ├──#secondary.txt
├── index.py
├── index.sh
├── initializer.py
├── parser.py
├──#queries_op.txt
├── README.md
├── search.py
├──#stats.txt
```

`NOTE`: The files and directories marked with `'#'` are created after running the code.

- [`doc`](./doc) - Folder containing the documents_id ─ title mapping.
    - [`doc******`](./doc/doc******) - Files containing the documents_id ─ title mapping, with a 6 digit number in the name(******).
- [`index`](./index) - Folder containing the inverted index built.
    - [`ind******`](./index/ind******) - Files containing the inverted index, with a 6 digit number in the name(******). Each file has a list of tokens, along with the posting list in the format:
        - ```{token};[{doc_id}:{term_freq}:{fields}]```
- [`secondary`](./secondary) - Folder containing the secondary index of the inverted index.
    - [`secondary.txt`](./secondary/secondary.txt) - 1 File containing the secondary index in the format:
        - ```{index_file_name (ind******)};{1st token in the index file}```

### Index Creation
- [`index.py`](./index.py) - This file contains the code for creating the merged index, and the doc-title mapping from the posting list.
- [`index.sh`](./index.sh) - This file contains a 1-line command for starting the index creation (calls `parser.py` to start parsing the dump).
- [`initializer.py`](./initializer.py) - This file contains code for installing some of the libraries modules needed.
- [`parser.py`](./parser.py) - This file has the code to parse the xml file, and create/store the tokens in the posting list. (calls the `index.py` file to build index). Also calls `initializer.py` to install the libraries/modules needed.
- [`stats.txt`](./stats.txt) - This contains the stats of the index created:
    - Index Size (in GB)
    - Number of files in which the inverted index is split
    - Number of tokens in the inverted index
```
bash index.sh {dump_file_path} ./index
```

### Query Parsing and Searching
- [`search.py`](./search.py) - This contains the code to parse the query given in a file, and write the 10 most relevant results + time taken to the output file.
```
python3 search.py {Query_file_path}
```

## Optimizations and Improvements
1. Removing certain type of tokens including:
    - Tokens with a mix of `numbers` and `alphabets`.
    - Tokens containing only `alphabets` with `size ≥ 15`.
    - Tokens containing only `numbers` with `size = 3` or `size ≥ 5`.
    - Tokens containing only `numbers` of `size = 4`, and not between [`1000`, `2022`].

    ```diff
    + IMPROVEMENTS: Reduced the size of the index by ~ 15%-20%.
    ```

1. For the `Posting List`, storing only the total frequency of the token in the document, and not the frequency of the token in each field.
    
    ```diff
    + IMPROVEMENTS: Reduced the size of the index.
    ```
1. For the `Posting List`, storing all the non-body fields in which token occurs as a single string.

    Ex: ```tir``` => token is +nt in the title, infobox, references
    
    ```diff
    + IMPROVEMENTS: Reduced the size of the index.
    ```

1. Giving weights to the fields based on their importance, which is later used in the calculation of the TF-IDF score:
    - `Title`: 100
    - `Body`: 1
    - `Infobox`: 40
    - `Category`: 40
    - `External Links`: 10
    - `References`: 10
    
    ```diff
    + IMPROVEMENTS: Improve quality of the search results.
    ```

1. Using TF-IDF to calculate the relevance score of a document for a query, where for each word in a doc:
    - `TF` = $\sum_{fields}$(frequency of query word in a field)*(field weight).
    - `IDF` = $log(\frac{N=50,000,000}{\text{posting list size}})$.
    
    `Score` = $\sum_{query\ words}$ TF * IDF.
    
    ```NOTE```: The frequency of queries for non-body fields is assumed to be boolean (1 if present, 0 if not present in the posting list)

    ```diff
    + IMPROVEMENTS: Improve search results relevance.
    ```

1. Using TF-IDF once to retrive a set of 100 documents, without penalizing the document size (in TF).

    Then again using TF-IDF on these documents to get the top 10 documents, this time penalizing the document size (stored in `doc******` file).

    ```diff
    + IMPROVEMENTS: Improve the quality of the search results, and reduce search time (compared to using document size in TF for all documents).
    ```

## Index creation time and size

Due to some time related issues, processing of the 90 GB dump file was not completed, and the index creation time and size provided here are scaled from the 1.4 GB dump file (by a factor of 60).

The `'stats.txt'` file also contains the stats for the 1.4 GB dump.

``` Time: 14:03 hours``` <br>
``` Size: 17.82 GB ```


## Index Format

Each file has a list of tokens, along with the posting list in the format:
<br>
 ```{token};({doc_id}:{term_freq}:{fields});({doc_id}:{term_freq}:{fields})...```
<br>
Here:
- `token`: The token for which we are considering the posting list
- `doc_id`: One of the document id in which the token occurs.
- `term_freq`: The number of times the token occurs in the document (This is the combined term freq., including body, title, infobox, category, external links, references).
- `fields`: All fields except body in which the token occurs (Each field denoted by a character):
    - `t`: Title
    - `i`: Infobox
    - `c`: Category
    - `e`: External Links
    - `r`: References
