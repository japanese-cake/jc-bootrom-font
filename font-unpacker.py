#!/usr/bin/env python3

import logging
import optparse
import struct
import sys
import traceback

from pathlib import Path
from PIL import Image, ImageColor


#
# charset/fontset type
#
SYBTFNT_TYPE_7BIT = "7bit"
SYBTFNT_TYPE_8BIT = "8bit"
SYBTFNT_TYPE_16BIT = "16bit"

#
# glyph data and image sizes
#
SYBTFNT_12X24_GLYPH_DATA_SIZE = int(12 * 24 / 8)
SYBTFNT_12X24_GLYPH_IMAGE_SIZE = (12, 24)
SYBTFNT_24X24_GLYPH_DATA_SIZE = int(24 * 24 / 8)
SYBTFNT_24X24_GLYPH_IMAGE_SIZE = (24, 24)
SYBTFNT_32X32_GLYPH_DATA_SIZE = int(32 * 32 / 8)
SYBTFNT_32X32_GLYPH_IMAGE_SIZE = (32, 32)

#
# font glyph specs
#
SYBTFNT_ASCII = "ascii"
SYBTFNT_ASCII_OFFSET = 0
SYBTFNT_ASCII_GLYPH_GLOBAL_INDEX_START = 0
SYBTFNT_ASCII_GLYPH_DATA_SIZE = SYBTFNT_12X24_GLYPH_DATA_SIZE
SYBTFNT_ASCII_GLYPH_COUNT = 96
SYBTFNT_ASCII_SIZE = SYBTFNT_ASCII_GLYPH_COUNT * SYBTFNT_12X24_GLYPH_DATA_SIZE

SYBTFNT_ISO_8859_1 = "iso-8859-1"
SYBTFNT_ISO_8859_1_OFFSET = int(SYBTFNT_ASCII_OFFSET + SYBTFNT_ASCII_SIZE)
SYBTFNT_ISO_8859_1_GLYPH_GLOBAL_INDEX_START = SYBTFNT_ASCII_GLYPH_GLOBAL_INDEX_START + SYBTFNT_ASCII_GLYPH_COUNT
SYBTFNT_ISO_8859_1_GLYPH_DATA_SIZE = SYBTFNT_12X24_GLYPH_DATA_SIZE
SYBTFNT_ISO_8859_1_GLYPH_COUNT = 96
SYBTFNT_ISO_8859_1_SIZE = SYBTFNT_ISO_8859_1_GLYPH_COUNT * SYBTFNT_12X24_GLYPH_DATA_SIZE

SYBTFNT_JIS_X_0201 = "jis-x-0201"
SYBTFNT_JIS_X_0201_OFFSET = int(SYBTFNT_ISO_8859_1_OFFSET + SYBTFNT_ISO_8859_1_SIZE)
SYBTFNT_JIS_X_0201_GLYPH_GLOBAL_INDEX_START = SYBTFNT_ISO_8859_1_GLYPH_GLOBAL_INDEX_START + SYBTFNT_ISO_8859_1_GLYPH_COUNT
SYBTFNT_JIS_X_0201_GLYPH_DATA_SIZE = SYBTFNT_12X24_GLYPH_DATA_SIZE
SYBTFNT_JIS_X_0201_GLYPH_COUNT = 96
SYBTFNT_JIS_X_0201_SIZE = SYBTFNT_JIS_X_0201_GLYPH_COUNT * SYBTFNT_12X24_GLYPH_DATA_SIZE

SYBTFNT_JISX_0208 = "jis-x-0208"
SYBTFNT_JISX_0208_OFFSET = int(SYBTFNT_JIS_X_0201_OFFSET + SYBTFNT_JIS_X_0201_SIZE)
SYBTFNT_JISX_0208_GLYPH_GLOBAL_INDEX_START = SYBTFNT_JIS_X_0201_GLYPH_GLOBAL_INDEX_START + SYBTFNT_JIS_X_0201_GLYPH_COUNT
SYBTFNT_JISX_0208_GLYPH_DATA_SIZE = SYBTFNT_24X24_GLYPH_DATA_SIZE
SYBTFNT_JISX_0208_GLYPH_COUNT = 7056
SYBTFNT_JISX_0208_SIZE = SYBTFNT_JISX_0208_GLYPH_COUNT * SYBTFNT_24X24_GLYPH_DATA_SIZE

SYBTFNT_GAIJ = "sega-gaij"
SYBTFNT_GAIJ_OFFSET = int(SYBTFNT_JISX_0208_OFFSET + SYBTFNT_JISX_0208_SIZE)
SYBTFNT_GAIJ_GLYPH_GLOBAL_INDEX_START = SYBTFNT_JISX_0208_GLYPH_GLOBAL_INDEX_START + SYBTFNT_JISX_0208_GLYPH_COUNT
SYBTFNT_GAIJ_GLYPH_DATA_SIZE = SYBTFNT_24X24_GLYPH_DATA_SIZE
SYBTFNT_GAIJ_GLYPH_COUNT = 22
SYBTFNT_GAIJ_SIZE = SYBTFNT_GAIJ_GLYPH_COUNT * SYBTFNT_24X24_GLYPH_DATA_SIZE

SYBTFNT_VMU_ICON = "sega-vmu-icon"
SYBTFNT_VMU_ICON_OFFSET = int(SYBTFNT_GAIJ_OFFSET + SYBTFNT_GAIJ_SIZE)
SYBTFNT_VMU_ICON_GLYPH_GLOBAL_INDEX_START = SYBTFNT_GAIJ_GLYPH_GLOBAL_INDEX_START + SYBTFNT_GAIJ_GLYPH_COUNT
SYBTFNT_VMU_ICON_GLYPH_DATA_SIZE = SYBTFNT_32X32_GLYPH_DATA_SIZE
SYBTFNT_VMU_ICON_GLYPH_COUNT = 129
SYBTFNT_VMU_ICON_SIZE = SYBTFNT_VMU_ICON_GLYPH_COUNT * SYBTFNT_32X32_GLYPH_DATA_SIZE

#
# font ID offset and size in the bios
#
SYBTFNT_ID_OFFSET = 0x00100018
SYBTFNT_ID_SIZE = 0x08

#
# font data offset in the bios
#
SYBTFNT_DATA_OFFSET = SYBTFNT_ID_OFFSET + SYBTFNT_ID_SIZE
SYBTFNT_DATA_END_OFFSET = SYBTFNT_DATA_OFFSET + SYBTFNT_VMU_ICON_OFFSET + SYBTFNT_VMU_ICON_SIZE

#
# global logger to use
#
logger = logging.getLogger(Path(__file__).stem)


class FontUnpackerError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def get_glyph_ascii_code(glyph_global_index):
    if glyph_global_index >= SYBTFNT_ASCII_GLYPH_GLOBAL_INDEX_START and \
       glyph_global_index < SYBTFNT_ISO_8859_1_GLYPH_GLOBAL_INDEX_START:

        if glyph_global_index == SYBTFNT_ASCII_GLYPH_GLOBAL_INDEX_START:
            return f"{SYBTFNT_ASCII}-0x{glyph_global_index + 33 - 1:02x}-overline"

        if glyph_global_index == SYBTFNT_ISO_8859_1_GLYPH_GLOBAL_INDEX_START - 1:
            return f"{SYBTFNT_ASCII}-0x{glyph_global_index + 33 - 1:02x}-yen-sign"

        return f"{SYBTFNT_ASCII}-0x{glyph_global_index + 33 - 1:02x}"

    return "unknown"


def get_glyph_iso_8859_1_code(glyph_global_index):
    if glyph_global_index >= SYBTFNT_ISO_8859_1_GLYPH_GLOBAL_INDEX_START and \
       glyph_global_index < SYBTFNT_JIS_X_0201_GLYPH_GLOBAL_INDEX_START:
        return f"{SYBTFNT_ISO_8859_1}-0x{glyph_global_index + 64:02x}"

    return "unknown"


def get_glyph_jis_x_0201_code(glyph_global_index):
    if glyph_global_index >= SYBTFNT_JIS_X_0201_GLYPH_GLOBAL_INDEX_START and \
       glyph_global_index < SYBTFNT_JISX_0208_GLYPH_GLOBAL_INDEX_START:
        if glyph_global_index == 256:
            return f"{SYBTFNT_JIS_X_0201}-0x{glyph_global_index - 32:02x}-ext-wi"
        if glyph_global_index == 257:
            return f"{SYBTFNT_JIS_X_0201}-0x{glyph_global_index - 32:02x}-ext-we"
        if glyph_global_index == 258:
            return f"{SYBTFNT_JIS_X_0201}-0x{glyph_global_index - 32:02x}-ext-small-wa"
        if glyph_global_index == 259:
            return f"{SYBTFNT_JIS_X_0201}-0x{glyph_global_index - 32:02x}-ext-small-ka"
        if glyph_global_index == 259:
            return f"{SYBTFNT_JIS_X_0201}-0x{glyph_global_index - 32:02x}-ext-small-ke"
        if glyph_global_index >= 260:
            return f"{SYBTFNT_JIS_X_0201}-0x{glyph_global_index - 32:02x}-ext-diacritics"

        return f"{SYBTFNT_JIS_X_0201}-0x{glyph_global_index - 32:02x}"

    return "unknown"


def get_glyph_jis_x_0208_code(glyph_global_index):
    if glyph_global_index >= SYBTFNT_JISX_0208_GLYPH_GLOBAL_INDEX_START and \
       glyph_global_index < SYBTFNT_GAIJ_GLYPH_GLOBAL_INDEX_START:

        column_index = int((glyph_global_index - SYBTFNT_JISX_0208_GLYPH_GLOBAL_INDEX_START) % 94) + 0x21
        row_index = int((glyph_global_index - SYBTFNT_JISX_0208_GLYPH_GLOBAL_INDEX_START) / 94)
        # Are we in the 7th first row ranges (which correspond to 33-39 non-Kanji rows)?
        if row_index < 39 - 33 + 1:
            row_index += 33
        else:
            # Otherwise we are in the 48-116 range.
            row_index += 48 - 7

        return f"{SYBTFNT_JISX_0208}-0x{row_index:02x}{column_index:02x}"

    return "unknown"


def get_glyph_gaij_code(glyph_global_index):
    return f"{SYBTFNT_GAIJ}-0x{glyph_global_index - SYBTFNT_GAIJ_GLYPH_GLOBAL_INDEX_START:04x}"


def get_glyph_vmu_icon_code(glyph_global_index):
    return f"{SYBTFNT_VMU_ICON}-0x{glyph_global_index - SYBTFNT_VMU_ICON_GLYPH_GLOBAL_INDEX_START:04x}"


def read_font_id(filehandle):
    try:
        filehandle.seek(SYBTFNT_ID_OFFSET)
        font_id, = struct.unpack(f"<{SYBTFNT_ID_SIZE}s", filehandle.read(SYBTFNT_ID_SIZE))
        font_id = font_id.decode(encoding='UTF-8')
        logger.info(f"Font ID @0x{SYBTFNT_ID_OFFSET:08x} is {font_id}")

        return font_id
    except Exception as error:
        raise FontUnpackerError(f"Unable to decode font ID @0x{SYBTFNT_ID_OFFSET:08x}") from error


def unpack_glyphs_fontsets(bootROM_filehandle, output_path):
    logger.info(f"Creating output directory '{output_path}'")
    output_path.mkdir(parents=True, exist_ok=True)

    glyph_global_index = 0
    glyph_global_index = unpack_glyphs_fontset(bootROM_filehandle, output_path, glyph_global_index, SYBTFNT_TYPE_7BIT,
                                               SYBTFNT_ASCII, SYBTFNT_ASCII_OFFSET, SYBTFNT_ASCII_SIZE,
                                               SYBTFNT_ASCII_GLYPH_DATA_SIZE, SYBTFNT_12X24_GLYPH_IMAGE_SIZE,
                                               get_glyph_ascii_code)
    glyph_global_index = unpack_glyphs_fontset(bootROM_filehandle, output_path, glyph_global_index, SYBTFNT_TYPE_8BIT,
                                               SYBTFNT_ISO_8859_1, SYBTFNT_ISO_8859_1_OFFSET, SYBTFNT_ISO_8859_1_SIZE,
                                               SYBTFNT_ISO_8859_1_GLYPH_DATA_SIZE, SYBTFNT_12X24_GLYPH_IMAGE_SIZE,
                                               get_glyph_iso_8859_1_code)
    glyph_global_index = unpack_glyphs_fontset(bootROM_filehandle, output_path, glyph_global_index, SYBTFNT_TYPE_8BIT,
                                               SYBTFNT_JIS_X_0201, SYBTFNT_JIS_X_0201_OFFSET, SYBTFNT_JIS_X_0201_SIZE,
                                               SYBTFNT_JIS_X_0201_GLYPH_DATA_SIZE, SYBTFNT_12X24_GLYPH_IMAGE_SIZE,
                                               get_glyph_jis_x_0201_code)
    glyph_global_index = unpack_glyphs_fontset(bootROM_filehandle, output_path, glyph_global_index, SYBTFNT_TYPE_16BIT,
                                               SYBTFNT_JISX_0208, SYBTFNT_JISX_0208_OFFSET, SYBTFNT_JISX_0208_SIZE,
                                               SYBTFNT_JISX_0208_GLYPH_DATA_SIZE, SYBTFNT_24X24_GLYPH_IMAGE_SIZE,
                                               get_glyph_jis_x_0208_code)
    glyph_global_index = unpack_glyphs_fontset(bootROM_filehandle, output_path, glyph_global_index, SYBTFNT_TYPE_16BIT,
                                               SYBTFNT_GAIJ, SYBTFNT_GAIJ_OFFSET, SYBTFNT_GAIJ_SIZE,
                                               SYBTFNT_GAIJ_GLYPH_DATA_SIZE, SYBTFNT_24X24_GLYPH_IMAGE_SIZE,
                                               get_glyph_gaij_code)
    glyph_global_index = unpack_glyphs_fontset(bootROM_filehandle, output_path, glyph_global_index, SYBTFNT_TYPE_16BIT,
                                               SYBTFNT_VMU_ICON, SYBTFNT_VMU_ICON_OFFSET, SYBTFNT_VMU_ICON_SIZE,
                                               SYBTFNT_VMU_ICON_GLYPH_DATA_SIZE, SYBTFNT_32X32_GLYPH_IMAGE_SIZE,
                                               get_glyph_vmu_icon_code)


def unpack_glyphs_fontset(filehandle, output_path, glyph_global_index, fontset_type,
                          fontset_name, fontset_offset: int, fontset_size, fontset_glyph_size, font_size, fontset_get_code):
    fontset_output_path = output_path / fontset_type / fontset_name
    logger.info(f"Unpacking {fontset_type} fontset {fontset_name} glyphs in {fontset_output_path}")
    fontset_output_path.mkdir(parents=True, exist_ok=True)

    offset = SYBTFNT_DATA_OFFSET + fontset_offset
    while offset < SYBTFNT_DATA_OFFSET + fontset_offset + fontset_size:
        filehandle.seek(offset)

        output_filepath = fontset_output_path / f"glyph-{glyph_global_index}-{fontset_get_code(glyph_global_index)}.png"
        font_data = filehandle.read(fontset_glyph_size)

        image = Image.new("RGB", font_size)

        pixel_index = 0
        for byte in font_data:
            for bit_index in range(8):
                if ((byte << bit_index) & 0x80) != 0:
                    color = ImageColor.getcolor("black", "RGB")
                else:
                    color = ImageColor.getcolor("white", "RGB")
                image.putpixel((pixel_index % font_size[0], int(pixel_index / font_size[0])), color)
                pixel_index += 1
        image.save(output_filepath)

        offset += fontset_glyph_size
        glyph_global_index += 1

    return glyph_global_index


def main(argv=None):
    logging.basicConfig(format='%(module)s %(levelname)s: %(message)s', level=logging.INFO)

    if argv is None:
        argv = sys.argv

    optparser = optparse.OptionParser(usage="usage: %prog [options] bootROM.bin",
                                      description="Unpack all bootROM font glyphs")
    optparser.add_option("-f", "--font-id",
                         action="store_true", dest="font_id_only", default=False,
                         help="Read only the font ID")
    optparser.add_option("-d", "--debug",
                         action="store_true", dest="debug", default=False,
                         help="Change logger level to 'DEBUG'")
    (options, args) = optparser.parse_args()

    try:
        if options.debug:
            logger.setLevel(logging.DEBUG)

        if len(args) == 0:
            raise FontUnpackerError('No bootROM (BIOS) file specified')

        basepath = Path(__file__).resolve().parent
        input_file = Path(args[0])
        output_path = (basepath / "output").relative_to(basepath)

        logger.info(f"Opening bootROM '{input_file}'")
        with open(input_file, mode='rb') as inputfile_handle:
            output_path /= read_font_id(inputfile_handle)
            if not options.font_id_only:
                unpack_glyphs_fontsets(inputfile_handle, output_path)

        logger.info('Done.')
    except FontUnpackerError as error:
        logger.error(error)
        logger.debug(traceback.format_exc())
        optparser.print_help(sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
