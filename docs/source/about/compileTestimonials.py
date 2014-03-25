import csv

headText = """
Testimonials - what do people think of PsychoPy?
=====================================================

OK, so we know that `PsychoPy has quite a lot of users <http://www.psychopy.org/usage.php>`_

We know that quite a few people have written `manuscripts that cited PsychoPy 
<http://scholar.google.co.uk/scholar?cites=18194791051729814045&as_sdt=2005&sciodt=0,5&hl=en>`_ 

But did the users actually *enjoy* using the software or was it a painful experience? 
This page will hold the (roughly honest) opinions of users. If you'd like to add your 
own testimonial then go to this 
`google form <https://docs.google.com/forms/d/1FQhLie8VP0dB2YWss_oxuKlADFGIkveLpf-u4EuGQ14/viewform>`_ 
(Updating the testimonials will be done periodically so don't expect your comment to appear here instantly, 
but we'll try and remember to do it every now and then. Please don't swear!!)

.. raw:: html

"""

#use csv from python (not from numpy) due to handling newlines within quote char
with open('testimonials.csv', 'rb') as csvFile:
    spamreader = csv.reader(csvFile, delimiter=',', quotechar='"')
    headers = spamreader.next()
    print 'headers:', type(headers), headers
    entries=[]
    for thisRow in spamreader:
        print thisRow
        thisEntry = {}
        for fieldN, thisFieldName in enumerate(headers):
            thisEntry[thisFieldName] = thisRow[fieldN]
        entries.append(thisEntry)

companHead="Your Company or Institution"
nameHead='Your name (or anon, but a name is nicer)'
testimHead='Your thoughts on PsychoPy'
posnHead = 'Your position'

with open('testimonials.rst', 'wb') as outFile:
    outFile.write(headText)
    for thisEntry in entries:
        outFile.write('    <hr>%s <p>\n' %(thisEntry[testimHead].replace('\n', '<br>')))
        outFile.write('    - <em>%s, %s, %s </em><br>\n' %(thisEntry[nameHead], thisEntry[posnHead], thisEntry[companHead]))

