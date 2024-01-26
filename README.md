# CRF_NER_proj
Named Entity Recognition (NER) is identifying and categorizing key information (entities) in text. An entity can be any word or series of words that consistently refer to the same thing, such as a person, organization, time, or location. Examples of use cases of NER include resume filtering for jobs, as NER is used to identify the necessary skills of a candidate, and customer support, where NER is used to classify incoming requests based on the customer’s needs. 

This project aims to train a model that identifies names in informal text like emails. 

Data used for training and testing is from Enron meeting and Enron random email corpus
The framework used to train the model is  Conditional random fields (CRF). It is a standard model for predicting the most likely sequence of labels that correspond to a sequence of inputs.
Example of an email 

```
Message-ID:  15929687.1072131933341.JavaMail.evans@thyme
Date: Wed, 1 Aug 2001 08:40:06 -0700 (PDT)
From: m..taylor@enron.com
Subject: Mtg w/<true_name> Matthew Scrimshaw
 </true_name> Mime-Version: 1.0
Content-Type: text/plain; charset=us-ascii
Content-Transfer-Encoding: 7bit

ask <true_name> Nikki  </true_name> if this is on the 2nd floor
```

crf.model is the model trained by the data. 

The models result :

|  | precision  | recall | f1-score   |support |
| --------- |  --------- |  --------- |  --------- |  --------- | 
  | true_name    |   0.86    |  0.69   |   0.76    | 51336|
  |        NA    |   0.98  |    0.99    |  0.99 |  1045873|
  |  accuracy     |           |         |  0.98 |  1097209|
  | macro avg   |    0.92   |  0.84   |   0.88 |  1097209 |
|weighted avg   |    0.98  |    0.98  |    0.98 |  1097209 |


Project Inspiration : http://www.cs.cmu.edu/~einat/email.pdf this paper 

Team: Beamlak Bekele, Iman Adetunji  

