#!/usr/bin/env python
# coding: utf-8

# In[ ]:


"""
Name: Beamlak Bekele
Data: 1/25/2024
Description: Trained a model to recognize names in informal text, such as emails using Enron corpus data,which contains over 700 emails.
Used Conditional random fields as  a modeling method.

Tried to replicate the result from:  http://www.cs.cmu.edu/~einat/email.pdf this paper 
"""


# In[ ]:


#import intialization 
import sys
from os import listdir
from os.path import isfile, join
import configparser
from sqlalchemy import create_engine

import sys
from os import listdir
from os.path import isfile, join
import configparser
from sqlalchemy import create_engine

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import email
import mailparser
import xml.etree.ElementTree as ET
try:
	from talon.signature.bruteforce import extract_signature
except:
	
	from talon.signature.bruteforce import extract_signature
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import re

import dask.dataframe as dd
from distributed import Client
import multiprocessing as mp


# In[ ]:


#set the local location of the data  
mail_dir = './data/enronRandom-XML/train'
test_dir = './data/enronRandom-XML/test'


# In[ ]:


#All enron emails were sent using the Multipurpose internet Mail extension format. 
#using correct libaries and methods to clean the emails and put it a panda data base 
def process_email(index):
    """
    This function splits a raw email into constituent parts that can be used a features
    """
    email_path = index[0]
    #print (email_path)
    employee = index[1]
    folder = index[2]
    mail = mailparser.parse_from_file(email_path)
    full_body = email.message_from_string(mail.body)

    #only retrive the body of the email
    if full_body.is_multipart():
        retrun 
    else:
        mail_body=full_body.get_payload()

    split_body= clean_body(mail_body)
    headers = mail.headers
    #reformat date to be panda readable
    date_time = process_date(headers.get('Date'))
    email_dict = { 
                "employee" : employee,
                "email_folder": folder,
                "message_id": headers.get('Message-ID'),
                "date" : date_time,
                "from" : headers.get('From'),
                "subject": headers.get('Subject'),
                "body" : split_body['body'],
                "chain" : split_body['chain'],
                "signature": split_body['signature'],
                #"wholeEmail": headers.get('Subject')+" "+ split_body['body'],
                "full_email_path" : email_path #for debug purposes. 
    }
    #append data frame
    return email_dict
    
    


# In[ ]:


def clean_body(mail_body):
    '''
    This extracts both the email signature, and the forwarding email chain if it exists. 
    '''
    delimiters = ["-----Original Message-----","To:","From"]
    
    #Trying to split string by biggest delimiter. 
    old_len = sys.maxsize
    
    for delimiter in delimiters:
        split_body = mail_body.split(delimiter,1)
        new_len = len(split_body[0])
        if new_len <= old_len:
            old_len = new_len
            final_split = split_body
            
    #Then pull chain message
    if (len(final_split) == 1):
        mail_chain = None
    else:
        mail_chain = final_split[1] 
    
    #The following uses Talon to try to get a clean body, and seperate out the rest of the email. 
    clean_body, sig = extract_signature(final_split[0])
    
    return {'body': clean_body, 'chain' : mail_chain, 'signature': sig}


# In[ ]:


#convert the MIME date format to panda friendly type
def process_date(date_time):
    try:
        date_time = email.utils.format_datetime(email.utils.parsedate_to_datetime(date_time))
    except:
        date_time = None
    return date_time


# In[ ]:


def generate_email_paths(mail_dir):
    '''
    Given a mail directory, this will generate the file paths to each email in each inbox. 
    '''
    mailboxes = listdir(mail_dir)
    #mail_dir = './date/'
    #print (mailboxes)
    for folder in mailboxes:
        path = mail_dir+ "/" + folder
        emails = listdir(path)
        for single_email in emails:
            #print(single_email)
            full_path = path + "/" + single_email
            name = single_email.split("_",1)
            if isfile(full_path): #Skip directories.
                yield (full_path, name[0], folder)
        


# In[ ]:


import multiprocessing as mp
from os import listdir
try:
    cpus = mp.cpu_count()
except NotImplementedError:
    cpus = 2
pool = mp.Pool(processes=cpus)
print("CPUS: " + str(cpus))

#Catagorizes parts of the email and a data frame for training data 

indexes = generate_email_paths(mail_dir)
#print(indexes)
enron_email_df = pool.map(process_email,indexes)
#print(enron_email_df)
#Remove Nones from the list
enron_email_df = [i for i in enron_email_df if i]
#print(enron_email_df)
enron_email_df = pd.DataFrame(enron_email_df)

########################################################

#Catagorizes parts of the email and a data frame for testing data 
indexes = generate_email_paths(test_dir)
#print(indexes)
tenron_email_df = pool.map(process_email,indexes)
#print(enron_email_df)
#Remove Nones from the list
tenron_email_df = [i for i in tenron_email_df if i]
#print(enron_email_df)
tenron_email_df = pd.DataFrame(tenron_email_df)
#enron_email_df.describe()


# In[ ]:


#729 rows × 11 columns columns data in data frame 
#prints the data fram 
enron_email_df.describe()
#tenron_email_df.describe()
display (tenron_email_df)


# In[ ]:


"""
/true_name is one of the most common words because the corpus is labeled. The label is <true_name>. 
"""
#To understand more about the email corpus we can 
#Find the most common words
from collections import Counter
bd = enron_email_df["body"]         #the body column of the data frame 
print (Counter(" ".join(bd).split()).most_common(20))


# In[ ]:


# These libraries will be used to prepare the data to train the model 
#this includes extracting feature, and identifying labels 
from bs4 import BeautifulSoup as bs
from bs4.element import Tag
import codecs
import nltk
from nltk import word_tokenize, pos_tag
from sklearn.model_selection import train_test_split
import pycrfsuite
import os, os.path, sys
import glob
from xml.etree import ElementTree
import numpy as np
from sklearn.metrics import classification_report


# In[ ]:


#helper function 
#this function removes special characters and punctuations
def remov_punct(withpunct):
    punctuations = '''!()-[]{};:'"\,<>./?@#$%^&*_~'''
    without_punct = ""
    char = 'nan'
    for char in withpunct:
        if  str(char) not in punctuations:
            without_punct = without_punct + str(char)
    return(without_punct)

# functions for extracting features in documents
def extract_features(doc,t):
    return [word2features(doc, i,t) for i in range(len(doc))]

def get_labels(doc):
    return [label for (token, postag, label) in doc]


# In[ ]:


#The files in the data directory are XML files. It needs to be changed beautiful soup
#BS format will change email to HTML text style. T
#Then it tags each word as name or not name 

#train data 
#array docs is 2d array: each row has tuples ("word", tag)
#eg:[ ('Sincerely', 'NA'), ('Paula', 'true_name')]
docs = []
#array of all the word in the corpus 
sents = []

#Just using 200 email from corpus 
for b in range (200):
    sub= enron_email_df["body"][b]
    soup = bs(sub, "html5lib")
    for d in soup.find_all("body"):
       for wrd in d.contents:    
        tags = []
        NoneType = type(None)   
        if isinstance(wrd.name, NoneType) == True:
            withoutpunct = remov_punct(wrd)
            temp = word_tokenize(withoutpunct)
            for token in temp:
                tags.append((token,'NA'))            
        else:
            withoutpunct = remov_punct(wrd)
            withoutpunct = remov_punct(withoutpunct) #remove twice to remove email attachment 
            temp = word_tokenize(withoutpunct)
            for token in temp:
                if (wrd.name == "true_name"):
                    tags.append((token,wrd.name))  
                else:
                     tags.append((token,'NA'))   
        sents = sents + tags 
       docs.append(sents)
 
#test data 
#array docs is 2d array: each row has tuples ("word", tag)
#eg:[ ('Sincerely', 'NA'), ('Paula', 'true_name')]
tdocs = []
#array of all the word in the corpus 
tsents = []

#Prepare 160 email
for b in range (160):
    sub= tenron_email_df["body"][b]
    soup = bs(sub, "html5lib")
    for d in soup.find_all("body"):
       for wrd in d.contents:    
        tags = []
        NoneType = type(None)   
        if isinstance(wrd.name, NoneType) == True:
            withoutpunct = remov_punct(wrd)
            temp = word_tokenize(withoutpunct)
            for token in temp:
                tags.append((token,'NA'))            
        else:
            withoutpunct = remov_punct(wrd)
            withoutpunct = remov_punct(withoutpunct) #remove twice to remove email attachment 
            temp = word_tokenize(withoutpunct)
            for token in temp:
                if (wrd.name == "true_name"):
                    tags.append((token,wrd.name))  
                else:
                     tags.append((token,'NA'))   
        tsents = tsents + tags 
       tdocs.append(tsents)


# In[ ]:


#this cell used to extract name from email address in the from column 
fromlist = []
import xml.etree.ElementTree as ET
sub= enron_email_df["from"][6]
print (sub)
if (sub):
    soup = bs(sub, "html5lib")
    for d in soup.find_all("body"):
        for wrd in d: 
            wrd = wrd.text
            if (wrd != None):
                fromname = wrd.split("@")[0].split(".")
                for i in fromname:
                    fromlist.append(i)
   
print (fromlist)


# In[ ]:


#Convert the subject, from, and signature part of the email in to a list of token
#This will be used as a feature, since this section of emails usually are names or contain 
subjectlist=[]   #list of words in the subject
fromlist=[]      #list of parsed names from the emails in from column of data frame
signlist= []     #list of words from in the signature part of the email

# training data data frame
thedf= enron_email_df    
for b in range (len (thedf["subject"])):
    sub= thedf["subject"][b]
    if (sub):
        soup = bs(sub, "html5lib")
        for d in soup.find_all("body"):
           for wrd in d.contents:    
               withoutpunct = remov_punct(wrd)
               temp = word_tokenize(without unit)
               for token in temp:
                   #add each word to subject list
                    subjectlist.append(token)
    sub= thedf["from"][b]
    if (sub):
        soup = bs(sub, "html5lib")
        for d in soup.find_all("body"):
            for wrd in d: 
                wrd= wrd.text
                if (wrd != None):
                    #remove @ from email address
                    #split the username with "." as delimeter 
                    fromname = wrd.split("@")[0].split(".")
                    for i in fromname:
                        #add split username to from list
                        fromlist.append(i)
    sub= thedf["signature"][b]
    if (sub):
        soup = bs(sub, "html5lib")
        for d in soup.find_all("body"):
            for wrd in d.contents: 
                withoutpunct = remov_punct(wrd)
                temp = word_tokenize(withoutpunct)
                for token in temp:
                    #if the signature isn't number then add to signlist 
                    isnum=False
                    for w in token:
                        if w.isdigit():
                            isnum=True
                            break
                    if not isnum:
                        signlist.append(token)
        
print (signlist)     


#Convert the subject, from, and signature part of the email in to a list for the test data 
tsubjectlist=[]
tfromlist=[]
tsignlist = {}
thedf= tenron_email_df    
for b in range (len (thedf["subject"])):
    sub= thedf["subject"][b]
    if (sub):
        soup = bs(sub, "html5lib")
        for d in soup.find_all("body"):
           for wrd in d.contents:    
               withoutpunct = remov_punct(wrd)
               temp = word_tokenize(withoutpunct)
               for token in temp:
                    tsubjectlist.append(token)
    sub= thedf["from"][b]
    soup = bs(sub, "html5lib")
    if (sub):
        for d in soup.find_all("body"):
            for wrd in d: 
                wrd= wrd.text
                fromname = wrd.split("@")[0].split(".")
                for i in fromname:
                    tfromlist.append(i)
    sub= thedf["signature"][b]
    if (sub):
        soup = bs(sub, "html5lib")
        for d in soup.find_all("body"):
            for wrd in d.contents: 
                withoutpunct = remov_punct(wrd)
                temp = word_tokenize(withoutpunct)
                for token in temp:
                    tsignlist[token]= 0


# In[ ]:


#This function extract features

#if the token is a title 
def is_nametitle (word):
    title_patterns = ['mr.', 'ms.', 'mrs.', 'dr.', 'prof.', '.jr', 'staff', 'rep', 'reporter','president','ceo','says']
    word= word.lower()
    return any(word.startswith(pattern) for pattern in title_patterns)

# checks if word is in the common first name list in this directory 
def first_namedic (word):
    with open("first-name.txt" , 'r') as file:
            # Read all lines from the file
            lines = file.readlines()

            # Check if the word is in any of the lines
            for line in lines:
                if word.lower() in line:
                    return True

        # If the word is not found in any line
    return False


# checks if word is in the common last name list in this directory 
def last_namedic (word):
    with open("last-name.txt" , 'r') as file:
            # Read all lines from the file
            lines = file.readlines()

            # Check if the word is in any of the lines
            for line in lines:
                if word.lower() in line:
                    return True

        # If the word is not found in any line
    return False

#check if the word was in the header/subject of the email 
def is_inheader (word,t):
    if (t == "train"):
        mylist =subjectlist
    else:
         mylist =tsubjectlist
    if (word in mylist):
        return True
    else:
        return False
#check if the word was in the list of names extract from the email address in from column of the data frame 
def is_infrom (word,t):
    #mylist=fromlist
    if (t == "train"):
        mylist =fromlist
    else:
         mylist =tfromlist
    if (word in mylist):
        return True
    else:
        return False
#check if the word was in the header/subject of the email 
def is_insign (word,t):
    #mylist=signlist
    if (t == "train"):
        mylist =fromlist
    else:
         mylist =tfromlist
    if (word in mylist):
        return True
    else:
        return False


# In[ ]:


#Using the function above and libraries generate feauters 

def word2features(doc, i,t):
    word = doc[i][0]
    postag = doc[i][1]

    # Common features for all words. You may add more features here based on your custom use case
    features = [
            'bias',
            'word.lower=' + word.lower(),
            'word[-3:]=' + word[-3:],
            'word[-2:]=' + word[-2:],
            'word.isupper=%s' % word.isupper(),
            'word.istitle=%s' % word.istitle(),
            '-1:word.isntitle=%s' % is_nametitle(word),
            '-1:word.is_inheader=%s' % is_inheader(word,t),
            '-1:word.is_infrom=%s' % is_infrom(word,t),
            '-1:word.is_insign=%s' % is_insign(word,t)
            #'word.isdigit=%s' % word.isdigit(),
            #'postag=' + postag
        ]
    
    # Features for words that are not at the beginning of a document
    if i > 0:
            word1 = doc[i-1][0]
            postag1 = doc[i-1][1]
            features.extend([
                '-1:word.lower=' + word1.lower(),
                '-1:word.istitle=%s' % word1.istitle(),
                '-1:word.isupper=%s' % word1.isupper(),
                '-1:word.isntitle=%s' % is_nametitle(word1),
                '-1:word.isntitle=%s' % is_nametitle(word),
                '-1:word.is_inheader=%s' % is_inheader(word,t),
                '-1:word.is_infrom=%s' % is_infrom(word,t),
                '-1:word.is_insign=%s' % is_insign(word,t),
                '-1:word.isdigit=%s' % word1.isdigit(),
                '-1:postag=' + postag1
            ])
    else:
        # Indicate that it is the 'beginning of a document'
        features.append('BOS')
    
    # Features for words that are not at the end of a document
    if i < len(doc)-1:
            word1 = doc[i+1][0]
            postag1 = doc[i+1][1]
            features.extend([
                '+1:word.lower=' + word1.lower(),
                '+1:word.istitle=%s' % word1.istitle(),
                '+1:word.isupper=%s' % word1.isupper(),
                '-1:word.isntitle=%s' % is_nametitle(word1),
                '-1:word.isntitle=%s' % is_nametitle(word),
                '-1:word.is_inheader=%s' % is_inheader(word,t),
                '-1:word.is_infrom=%s' % is_infrom(word,t),
                '-1:word.is_insign=%s' % is_insign(word,t),
                '+1:word.isdigit=%s' % word1.isdigit(),
                '+1:postag=' + postag1
            ])
    else:
        # Indicate that it is the 'end of a document'
        features.append('EOS')
    
    return features


# In[ ]:


#change the doc list which only tuple (word,tag) to also have part of speech tag eg. ('me', 'PRP', 'NA')
data = []
for i, doc in enumerate(docs):
    tokens = [t for t, label in doc]    
    tagged = nltk.pos_tag(tokens)    
    data.append([(w, pos, label) for (w, label), (word, pos) in zip(doc, tagged)])


# In[ ]:


#change the tdoc tuples which only had (word,tag) to also have part of speech tag eg. ('me', 'PRP', 'NA')
tdata=[]    
for i, doc in enumerate(tdocs):
    tokens = [t for t, label in doc]    
    tagged = nltk.pos_tag(tokens)    
    tdata.append([(w, pos, label) for (w, label), (word, pos) in zip(doc, tagged)])


# In[ ]:


#genrate features and extract labels for training data  
X = [extract_features(doc,"train") for doc in data]
y = [get_labels(doc) for doc in data]
X_train, X_unused, y_train, y_unused = train_test_split(X, y, test_size=0.01, random_state=42)
print (len (X_train))
print (len (X_unused))


# In[ ]:


#genrate features and extract labels for training data  
tX = [extract_features(doc,"test") for doc in tdata]
ty = [get_labels(doc) for doc in tdata]
#print (tX[0])
X_test, X_unused, y_test, y_unused = train_test_split(tX, ty, test_size=0.01, random_state=42)


# In[ ]:


#train a CRF Model
import pycrfsuite
trainer = pycrfsuite.Trainer(verbose=False)
# Submit training data to the trainer
for xseq, yseq in zip(X_train, y_train):
    trainer.append(xseq, yseq)

# Set the parameters of the model
trainer.set_params({
    # coefficient for L1 penalty
    'c1': 0.1,

    # coefficient for L2 penalty
    'c2': 0.01,  

    # maximum number of iterations
    'max_iterations': 70,

    # whether to include transitions that
    # are possible, but not observed
    'feature.possible_transitions': True
})

# Provide a file name as a parameter to the train function, such that
# the model will be saved to the file when training is finished
trainer.train('crf.model')


# In[ ]:


#test random sample 
tagger = pycrfsuite.Tagger()
tagger.open('crf.model')
y_pred = [tagger.tag(xseq) for xseq in X_test]

#look at a random sample in the testing set
#i = 0
#for x, y in zip(y_pred[i], [x[1].split("=")[1] for x in X_test[i]]):
    #print("%s (%s)" % (y, x))


# In[ ]:


#See how good the model is preforming 

from sklearn.metrics import classification_report

# Create a mapping of labels to indices
labels = {"NA": 1, "true_name": 0}

# Convert the sequences of tags into a 1-dimensional array
predictions = np.array([labels[tag] for row in y_pred for tag in row])
truths = np.array([labels[tag] for row in y_test for tag in row])

# Print out the classification report
print(classification_report(
    truths, predictions,
    target_names=["true_name", "NA"]))


# In[ ]:




