import math

def termFrequency(document):                     # output the normalized term frequencies for all words
    termFrequencyDict = {}                       # creates a dictionary (hash table)
    for word in document:
        if word not in termFrequencyDict:
            termFrequencyDict[word] = document.count(word)/float(len(document))
    return termFrequencyDict

def inverseDocumentFrequency(documents):
    tempSet = set()
    idfDict, tempDict = {}, {}
    wordsList = []
    for doc in documents:
        wordsList.append(set(doc))
        tempSet |= wordsList[-1]                 # union operation
    for word in tempSet:                         # tempSet has all the unique words from all documents
        tempDict[word] = 0.0
    for word in tempDict:
        for i in range(len(documents)):
            if word in wordsList[i]:             # number of documents in which the word has appeared
                tempDict[word] += 1
    for word in tempDict:
            idfDict[word] = 1.0 + math.log(float(len(documents))/tempDict[word])
    return idfDict

def tfIdf(tf, idf):
    tf_idf = {}
    for doc in tf:                               # create a dictionary of dictionaries
        tf_idf[doc] = {}
    for doc in tf:
        for term in tf[doc]:
            tf_idf[doc][term] = tf[doc][term]*idf[term]
    return tf_idf

def sim(query, idf, tf_idf, document_size):
    query_set = set(query)                       # take the unique words in the query
    if len(query_set) == 0:
        return (-1, -1)
    term_freq = 1.0/len(query_set)               # the frequency of each term of the query is the same
    max_similarity = 0                           # initialization of similarity
    for doc in range(document_size):
        dotproductsum = 0                        # sum of the dot product of query and document
        query_mag = 0                            # query magnitude and doc. term magnitude
        doc_mag = 0
        for term in query_set:                   # global idf * term_freq * tf_idf of term in document
            dotproductsum += (idf[term] if term in idf else 0) * term_freq * (tf_idf[doc][term] if term in tf_idf[doc] else 0)
            query_mag += math.pow((idf[term] if term in idf else 0) * term_freq, 2)
        for word in tf_idf[doc]:                 # take the tf_idf of all terms in the document and square-add
            doc_mag += math.pow(tf_idf[doc][word], 2)
        cosine_sim = dotproductsum / (math.sqrt(query_mag * doc_mag) + 0.001) # add 0.001 to avoid 0/0 division
        if (cosine_sim >= max_similarity):       # check the highest cosine similarity in each iteration
             max_similarity = cosine_sim
             max_doc = doc
    if (max_similarity == 0):
        max_doc = "None"
    return (max_similarity, max_doc)
