#!/usr/bin/env python
# -*- coding:gb2312 -*-
from htmlentitydefs import entitydefs
from HTMLParser import HTMLParser
import sys, re, urllib2

#define a list of interesting tables.
interesting = ['Day Forecast for ZIP']

#定义一个HTMLParser.HTMLParser子类，并添加用来处理不同标签的函数
class WeatherParser(HTMLParser):
    """Class to parse weather data from www.wunderground.com."""
    def __init__(self):
        # Storage for parse tree
        self.taglevels = []
        # List of tags that are interesting
        self.handledtags = ['title', 'table', 'tr', 'td', 'th']
        # Set to the interesting tag currently being processed
        self.processing = None
        # True if currently processing an interesting tables
        self.interestingtable = 0
        # If processing an interesting table, holds cells in current row
        self.row = []
        # Initialize base class
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        """Called by base class to handle start tags. whenever a start tag is encountered."""
        if len(self.taglevels) and self.taglevels[-1]==tag:
            #Processing a previous version of this tag. Close it out
            #and then start a new on this one.
            self.handle_endtag(tag)
        
        #Note that we're now processing this tag，只要是一个开始标签就添加
        self.taglevels.append(tag)
        if tag == 'br':
            # Add a special newline token to the stream
            self.handle_data("<NEWLINE>")
        #如果是一个我们要处理的标签
        elif tag in self.handledtags:
            #Only bother saving off the data if it's a tag we handle.
            self.data = ''
            self.processing = tag
            
    def handle_data(self, data):
        """ Called by both HTMLParser and methods in WeatherParser to handle plain data. This function simply records incoming data if we are presently inside a handled tag."""
        if self.processing:  #检查是否处理这个标签，如果是就记录其中的数据
            #通常这是一个慢又差的方法
           self.data += data

    def handle_endtag(self, tag):
        """Handle a closing tag."""
        if not tag in self.taglevels:
            #we didn't have a start tag for this anyway. Just ignore.
            return

        while len(self.taglevels):
            #get the last tag on the list and remove it
            starttag = self.taglevels.pop()

            #finish processing it.
            if starttag in self.handledtags:
                self.finishprocessing(starttag)
            #if it's our tag, stop now
            if starttag == tag:
                break
    
    def cleanse(self):
        """Remove extra whitespace from the document."""
        #  \xa0 is the non-breaking space(&nbsp; in HTML)
        self.data = re.sub('(\s|\xa0)+',' ',self.data)
        self.data = self.data.replace('<NEWLINE>',"\n").strip()

    def finishprocessing(self, tag):
        """ Called by handle_endtag() to handle an interesting end tag."""
        global interesting
        self.cleanse()
        if tag == 'title' and tag == self.processing:
            #print out the title of page
            print "*** %s ***" % self.data
        elif (tag == 'td' or tag == 'th') and tag == self.processing:
            # Got a cell in a table.
            if not self.interestingtable:
                # If we're not already in an interesting table, see if this cell makes the table interesting.
                for item in interesting:
                    if re.search(item, self.data, re.I):
                        #yep, found an interestingtable. Note that, then remove it from the interesting list, print out a heading, and stop looking at the list.
                        self.interestingtable = 1
                        interesting = [x for x in interesting if x!= item]
                        print "\n *** %s\n" % self.data.strip()
                        break
                    else:
                        # Already in an interestingtable; just add this cell to the curren row.
                        self.row.append(self.data)
        elif tag == 'tr' and self.interestingtable:
            # print out an interesting row.
            self.writerow()
            self.row = []
        elif tag == 'table':
            #End of a table: note that system is no longer processing an interestingtable.
            self.interestingtable = 0

        self.processing = None

    def writerow(self):
        """Format a row for on-screen display."""

        cells = len(self.row)
        if cells < 2:
            #if there are no cells, the row is empty; display nothing.
            #if there is 1 cell, wunderground.com uses it as a header.
            #we don't want it, so again, display noting.
            return
        if cells > 2:
            #if it's a table with lots of cells, give each cell
            #the same amount of space, leaving room for a space between cells.
            width = (78 - cells) / cells
            maxwidth = width
        else:
            #if it's a table with two cells, make the left one narrow
            #and the rightone wide.\
            width = 20
            maxwidth = 58

        # Continue looping while at least  one cell has a line of data to print
        while [x for x in self.row if x!='']:
            #process each cell in the row.
            for i in range(len(self.row)):
                thisline = self.row[i]
                if thisline.find("\n")!=-1:
                    #if it has multiple lines, we want only the first;
                    # save it in thisline, and shove the rest back into
                    # the list for processing later.
                    (thisline, self.row[i]) = self.row[i].split("\n",1)
                else:
                    #just one line, we've already got it in thisline,
                    #so put the empty string in the list for later.
                    self.row[i] = ''
                thisline = thisline.strip()
                sys.stdout.write("%-*.*s " % (width, maxwidth, thisline))
            sys.stdout.write("\n")

 #处理html中的实体方法
    def handle_entityref(self, name):
        if entitydefs.has_key(name):
            self.handle_data(entitydefs[name])
        else:
            self.handle_data('&' + name + ';')

    #convert the character reference like &#174商标符号
    def handle_charref(self, name):
        #Validate the name.
        try:
            charnum = int(name)
        except ValueError:
            return
        if charnum < 1 or charnum > 255:
            return 
        self.handle_data(chr(charnum))

#HTMLParser的feed()方法会适当地调用handle_starttag,handle_data,handle_endtag方法。
sys.stdout.write("Enter ZIP code: ")
zip = sys.stdin.readline().strip()
url="http://www.wunderground.com/cgi-bin/findweather/getForecast?query="+zip+"&wuSelect=WEATHER"
print url

req = urllib2.Request(url)
fd = urllib2.urlopen(req)
#用正则表达式处理HTML中不规范的代码，在把文档发给HTMLParser之前，要预处理
parser = WeatherParser()
data = fd.read()
data = re.sub(' ([^ =]+)=[^ ="]+="', ' \\1="', data)
data = re.sub('(?s)<!--.*?-->','', data)
parser.feed(data)
