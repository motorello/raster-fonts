#!/usr/bin/python3

import sys
import png
import curses.ascii
import math
import time

if len(sys.argv) < 2:
    sys.stderr.write("Please specify the input PNG file\n")
    sys.exit(1)

reader = png.Reader(filename=sys.argv[1])

data = reader.asRGB()
#data = reader.asDirect()

bitmap = list(data[2]) # get image RGB values

image_size = data[:2] # get image width and height

# let's put it in clear (256x512)
image_width  = image_size[0] # 256
image_height = image_size[1] # 512

char_size = (int(image_width / 16), int(image_height / 16)) # 16 characters in a row, 16 rows of characters

# let's put it in clear (16x32)
char_width  = char_size[0] # 16
char_height = char_size[1] # 32



raster = []

for line in bitmap:
    raster.append([c == 0xFF and 1 or 0 for c in [line[k+1] for k in range(0, image_width * 3, 3)]])

# array of character bitmaps; each bitmap is an array of lines, each line
# consists of 1 - bit is set and 0 - bit is not set
char_bitmaps = [] 
for c in range(0, 256): # for each character
    char_bitmap = []
    raster_row = int(c / 16) * char_height
    offset = int((c % 16) * char_width)

    for y in range(0, char_height): # for each scan line of the character
        char_bitmap.append(raster[raster_row + y][offset : offset + char_width])
    char_bitmaps.append(char_bitmap)

raster = None # no longer required



# how many bytes a single character scan column should be
num_bytes_per_scan_column = math.ceil(char_height / 8) # for RT-890 we store charaters by column

# convert the whole bitmap into an array of character bitmaps
char_bitmaps_processed = []

for c in range(0, len(char_bitmaps) - 1): # last character seems to be not printable by curses...
#for c in range(48, 49): # last character seems to be not printable by curses...
    bitmap = char_bitmaps[c]
    encoded_columns = []

    # for RT-890 (and I guess in general for 'st7735s' display type), I need to have an array of columns rather than rows, which is more tricky
    bitmap_rows = len(bitmap)    # which is 'char_height'
    bitmap_cols = len(bitmap[0]) # which is 'char_width'

    for col in range(0, bitmap_cols): # 0..15, starting from the bottom
        encoded_column = []

        for b in range(0, num_bytes_per_scan_column):
            offset = b * 8
            char_byte = 0
            mask = 0x01
            for x in range(0, 8):
                if offset + x >= char_height:
                    break

                if (bitmap[offset + x])[col]:
                    char_byte += mask

                mask <<= 1

            encoded_column.append(char_byte)
        encoded_columns.append([encoded_column, col])
    char_bitmaps_processed.append([c, encoded_columns])

char_bitmaps = None



# calculate the dimension of the array elements type definition
datatype_dim = 8
while (num_bytes_per_scan_column * 8) > datatype_dim:
    datatype_dim <<= 1

sys.stdout.write("""static const uint%i_t FontBigDigits%dx%d[][] = { // WARNING!! DOUBLE CHECK the data type (uint%i_t)
""" % (datatype_dim, char_width, char_height, datatype_dim))



for c in char_bitmaps_processed:
    sys.stdout.write("""
    /*
     * code=%d, hex=0x%02X, ascii="%s"
     */
""" % (c[0], c[0], curses.ascii.unctrl(c[0])))
    sys.stdout.write("    {")
    for line in c[1]:
        sys.stdout.write("\n        0x")
        for char_byte in reversed(line[0]):
            sys.stdout.write(("%02X" % char_byte))

        sys.stdout.write(",    /* character column %02d */" % line[1])
        #sys.stdout.write("  /* %s */" % str(bin(line[0])))
    sys.stdout.write("\n    },\n")
sys.stdout.write("""\n};
""")
