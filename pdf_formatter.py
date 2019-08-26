import pdfcrowd

import pdfcrowd_token

class PDFFormatter(object):
    size="100in"

    def __init__(self):
        # create the API client instance
        u = pdfcrowd_token.uname
        k = pdfcrowd_token.key
        self.client = pdfcrowd.HtmlToPdfClient(u, k)
        self.client.setPageWidth(self.size)
        self.client.setPageHeight(self.size)


    def convert(self, html):
        # run the conversion and write the result to a file
        return self.client.convertString(html)
