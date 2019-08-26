import pdfcrowd

class PDFFormatter(object):
    size="100in"

    def __init__(self):
        # create the API client instance
        self.client = pdfcrowd.HtmlToPdfClient('royrapoport', 'cf8ff49e6afceb2ec756a71d0b4f42b0')
        self.client.setPageWidth(self.size)
        self.client.setPageHeight(self.size)


    def convert(self, html):
        # run the conversion and write the result to a file
        return self.client.convertString(html)
