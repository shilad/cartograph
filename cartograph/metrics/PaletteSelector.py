import csv
import random

class PaletteSelector:

    def __init__(self):
        self.scheme_dict = {'Qualitative': {}, 'Sequential': {}, 'Diverging': {}}
        self.parse_csv('/Users/sen/PycharmProjects/cartograph/cartograph/metrics/cb.csv')
        # Change the previous line to wherever the ColorBrewer file is located in your system--not sure how to make this
        # vary yet

    # Parses the CSV of ColorBrewer's color schemes (https://github.com/axismaps/colorbrewer/blob/master/cb.csv), making a
    # nested dictionary of CMYK values organized by type, palette name, number of colors in the palette ("version"), and
    # then number or letter of the color (meaning that each "version" dictionary contains twice as many dictionaries as
    # colors). The CMYK values are stored as lists of integers.
    def parse_csv(self, filepath):
        reader = csv.reader(open(filepath, 'r'))

        palette = ""
        type = ""
        version = 0
        reader.next()
        for row in reader:
            if row[0] != '':
                if row[0] != palette:
                    palette = row[0]
                    type = row[10]
                    self.scheme_dict[type][palette] = {}
            if row[1] != '':
                version = int(row[1])
                self.scheme_dict[type][palette][version] = {}
            colornum = int(row[4])
            colorletter = row[5]
            cmyk = [int(row[6]), int(row[7]), int(row[8]), int(row[9])]
            self.scheme_dict[type][palette][version][colornum] = cmyk
            self.scheme_dict[type][palette][version][colorletter] = cmyk
        return self.scheme_dict

    # Takes in the type of a dataset (qualitative, sequential, or diverging), the number of levels the data are divided
    # into, and the dictionary of the parsed CSV, and chooses a random color palette of the appropriate size and type from
    # the dictionary.
    def select_palette(self, scheme_type, num_levels):
        palette = random.choice(self.scheme_dict[scheme_type].keys())
        return self.scheme_dict[scheme_type][palette][num_levels]
