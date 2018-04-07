import re
from fpdf.html import hex2dec
from .bmlt_objects import Format, Meeting


def _get_lines(pdf, parts, max_line_length):
    lines = []
    current_line = ''
    for i in range(len(parts)):
        part = parts[i]
        proposed_line = current_line + ' ' + part if current_line else current_line + part
        if pdf.get_string_width(proposed_line) + 2 * pdf.c_margin > max_line_length:
            lines.append(current_line)
            current_line = part
        else:
            current_line = proposed_line

        if pdf.get_string_width(current_line) + 2 * pdf.c_margin > max_line_length:
            lines.append(current_line)
            current_line = ''
        elif i == len(parts) - 1:
            lines.append(current_line)
    return lines


class PDFMainPagePlaceholder:
    def write(self, pdf, x=None, y=None):
        pass


class PDFColumnEnd:
    pass


class PDFSectionHeader:
    def __init__(self, text, pdf_func, cell_width, line_padding=1, font='dejavusans', font_size=12,
                 font_color='#000000', fill_color='#FFFFFF'):
        self.text = text
        self.pdf_func = pdf_func
        self.cell_width = cell_width
        self.line_padding = line_padding
        self.font = font
        self.font_size = font_size
        self.font_color = font_color
        self.fill_color = fill_color

    def copy(self):
        return PDFMainSectionHeader(
            self.text,
            self.pdf_func,
            self.cell_width,
            line_padding=self.line_padding,
            font=self.font,
            font_size=self.font_size
        )

    @property
    def height(self):
        pdf = self.pdf_func()
        pdf.set_font(self.font, 'B', self.font_size)
        return pdf.font_size + self.line_padding + 1

    def write(self, pdf, x=None, y=None):
        if x is not None and y is not None:
            pdf.set_xy(x, y)
        pdf.set_font(self.font, 'B', self.font_size)
        pdf.set_text_color(*hex2dec(self.font_color))
        pdf.set_fill_color(*hex2dec(self.fill_color))
        pdf.cell(self.cell_width, h=pdf.font_size + self.line_padding, txt=self.text, border=0, ln=1, align='C', fill=1)
        pdf.ln(h=1)


class PDFMainSectionHeader(PDFSectionHeader):
    def __init__(self, text, pdf_func, cell_width, **kwargs):
        kwargs['font_color'] = '#FFFFFF'
        kwargs['fill_color'] = '#000000'
        super().__init__(text, pdf_func, cell_width, **kwargs)

    def copy(self):
        return PDFMainSectionHeader(
            self.text,
            self.pdf_func,
            self.cell_width,
            line_padding=self.line_padding,
            font=self.font,
            font_size=self.font_size
        )


class PDFSubSectionHeader(PDFSectionHeader):
    def __init__(self, text, pdf_func, cell_width, **kwargs):
        kwargs['font_color'] = '#000000'
        kwargs['fill_color'] = '#C0C0C0'
        super().__init__(text, pdf_func, cell_width, **kwargs)

    def copy(self):
        return PDFSubSectionHeader(
            self.text,
            self.pdf_func,
            self.cell_width,
            line_padding=self.line_padding,
            font=self.font,
            font_size=self.font_size
        )


class PDFFormatsTable:
    def __init__(self, formats, pdf_func, total_width, margin_width=5, font='dejavusans', font_size=12,
                 key_column_width=10, table_header_text=None, table_header_font='dejavusans',
                 table_header_font_size=12, header_font_color='#000000', header_fill_color='#FFFFFF'):
        self.pdf_func = pdf_func
        self.font = font
        self.font_size = font_size
        self.total_width = total_width
        self.margin_width = margin_width
        self.key_column_width = key_column_width
        self.table_header_text = table_header_text
        if self.table_header_text is None:
            self.table_header_text = 'Meeting Format Legend'
        self.table_header_font = table_header_font
        self.table_header_font_size = table_header_font_size
        self.header_font_color = header_font_color
        self.header_fill_color = header_fill_color
        self.formats = [PDFFormat(f, pdf_func, self.key_column_width, self.name_column_width, font=font, font_size=font_size) for f in formats]
        if len(self.formats) % 2 != 0:
            blank_format = Format({
                'id': '-1',
                'key_string': 'tmp',
                'name_string': 'tmp',
            })
            blank_format.key = ''
            blank_format.name = ''
            self.formats.append(PDFFormat(blank_format, pdf_func, self.key_column_width, self.name_column_width, font=font, font_size=font_size))

    @property
    def total_column_width(self):
        return (self.total_width - self.margin_width) / 2

    @property
    def name_column_width(self):
        return self.total_column_width - self.key_column_width

    @property
    def height(self):
        header = PDFSectionHeader(
            self.table_header_text,
            self.pdf_func,
            self.total_width,
            font=self.table_header_font,
            font_size=self.table_header_font_size,
            font_color=self.header_font_color,
            fill_color=self.header_fill_color
        )
        height = header.height

        for i in range(len(self.formats)):
            format = self.formats[i]
            left = i % 2 == 0
            other = None
            if left and i < len(self.formats) - 1:
                other = self.formats[i + 1]
            elif not left:
                other = self.formats[i - 1]
            if other:
                while format.height < other.height:
                    format.format.name += ' '
            if not left or i >= len(self.formats) - 1:
                height += format.height
        return height

    def write(self, pdf, x=None, y=None):
        if x is None or y is None:
            x = pdf.get_x()
            y = pdf.get_y()
        pdf.set_xy(x, y)

        header = PDFSectionHeader(
            self.table_header_text,
            self.pdf_func,
            self.total_width,
            font=self.table_header_font,
            font_size=self.table_header_font_size,
            font_color=self.header_font_color,
            fill_color=self.header_fill_color
        )
        header.write(pdf)

        left_x = x + (self.margin_width / 2)
        first = True
        for i in range(len(self.formats)):
            left = i % 2 == 0
            format = self.formats[i]
            if left:
                pdf.set_x(left_x)
            else:
                pdf.set_x(left_x + self.total_column_width)
            if first:
                border = 'LTRB' if left else 'TRB'
                if not left:
                    first = False
            else:
                border = 'LRB' if left else 'RB'
            before_y = pdf.get_y()
            other = None
            if left and i < len(self.formats) - 1:
                other = self.formats[i + 1]
            elif not left:
                other = self.formats[i - 1]
            if other:
                while format.height < other.height:
                    format.format.name += ' '
            format.write(pdf, border=border)
            if left:
                pdf.set_y(before_y)
            else:
                pdf.set_y(before_y + max(format.height, other.height))

        pdf.set_xy(x, pdf.get_y())


class PDFFormat:
    def __init__(self, format, pdf_func, key_column_width, name_column_width, font='dejavusans', font_size=10,
                 text_line_padding=1):
        if not isinstance(format, Format):
            raise TypeError('Expected Format object')
        self.pdf_func = pdf_func
        self.format = format
        self.key_column_width = key_column_width
        self.name_column_width = name_column_width
        self.font = font
        self.font_size = font_size
        self.text_line_padding = text_line_padding

    @property
    def height(self):
        pdf = self.pdf_func()

        pdf.set_font(self.font, '', self.font_size)
        name = self.format.name
        parts = re.split(r' ', name)
        lines = _get_lines(pdf, parts, self.name_column_width)
        text_height = pdf.font_size
        padding = len(lines) * self.text_line_padding
        height = (text_height * len(lines)) + padding
        return height

    def write(self, pdf, border='LTRB'):
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(*hex2dec('#000000'))
        key_cell_border = 0
        name_cell_border = 0
        if border:
            key_cell_border = border
            name_cell_border = border.replace('L', '')
        pdf.set_font(self.font, 'B', self.font_size)
        pdf.cell(self.key_column_width, h=max(pdf.font_size + self.text_line_padding, self.height), txt=self.format.key, ln=0, align='L', border=key_cell_border)
        pdf.set_font(self.font, '', self.font_size)
        pdf.multi_cell(self.name_column_width, h=pdf.font_size + self.text_line_padding, txt=self.format.name, border=name_cell_border)


class PDFMeeting:
    def __init__(self, meeting, pdf_func, total_width, time_column_width=None, duration_column_width=None,
                 font='dejavusans', font_size=12, separator_color='#D3D3D3'):
        if not isinstance(meeting, Meeting):
            raise TypeError('Expected Meeting object')
        self.pdf_func = pdf_func
        self.meeting = meeting
        self.time_column_width = time_column_width if time_column_width else 15
        self.duration_column_width = duration_column_width if duration_column_width else 15
        self.font = font
        self.font_size = font_size
        self.total_width = total_width
        self.separator_color = separator_color
        if not self.separator_color.startswith('#'):
            self.separator_color = '#' + self.separator_color

    def get_time(self):
        ampm = 'AM'
        hour, minute = str(self.meeting.start_time).split(':')[:2]
        hour = int(hour)
        if hour > 11:
            ampm = 'PM'
        if hour > 12:
            hour = hour - 12
        return str(hour) + ':' + minute + ampm

    def get_duration(self):
        hour, minute = str(self.meeting.duration).split(':')[:2]
        minute = str(round(int(minute) / 60))
        return hour + '.' + minute + 'HR'

    def get_name(self):
        return self.meeting.name.strip()

    def get_location(self):
        return self.meeting.location.strip()

    def get_formats(self):
        if self.meeting.formats:
            return '(' + self.meeting.formats + ')'
        return ''

    @property
    def meeting_column_width(self):
        return self.total_width - self.time_column_width - self.duration_column_width

    @property
    def height(self):
        pdf = self.pdf_func()

        pdf.set_font(self.font, 'B', self.font_size)
        meeting_name = self.get_name()
        meeting_formats = self.get_formats()
        if meeting_formats:
            meeting_name += ' ' + meeting_formats
        parts = meeting_name.split()
        lines = _get_lines(pdf, parts, self.meeting_column_width)
        text_height = pdf.font_size
        height = (text_height * len(lines))

        pdf.set_font(self.font, '', self.font_size)
        meeting_location = self.get_location()
        parts = meeting_location.split()
        lines = _get_lines(pdf, parts, self.meeting_column_width)
        text_height = pdf.font_size
        height += (text_height * len(lines))
        return height + pdf.line_width + 2  # 1mm line break before and after line

    def write(self, pdf, x=None, y=None):
        if x is None or y is None:
            x = pdf.get_x()
            y = pdf.get_y()
        pdf.set_xy(x, y)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(self.font, 'B', self.font_size)
        pdf.cell(self.time_column_width, h=pdf.font_size, txt=self.get_time(), ln=0, align='C')
        pdf.cell(self.duration_column_width, h=pdf.font_size, txt=self.get_duration(), ln=0, align='C')

        text = self.get_name()
        meeting_formats = self.get_formats()
        if meeting_formats:
            text += ' ' + meeting_formats
        pdf.multi_cell(self.meeting_column_width, h=pdf.font_size, txt=text, border=0, align='L')

        pdf.set_xy(x + self.duration_column_width + self.time_column_width, pdf.get_y())
        text = self.get_location()
        pdf.set_font(self.font, '', self.font_size)
        pdf.multi_cell(self.meeting_column_width, h=pdf.font_size, txt=text, border=0, align='L')

        pdf.ln(h=1)
        pdf.set_draw_color(*hex2dec(self.separator_color))
        if x is not None and y is not None:
            height = self.height - 1 - pdf.line_width
            pdf.line(x, y + height, x + self.total_width, y + height)
        else:
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + self.total_width, pdf.get_y())

        pdf.set_xy(x, pdf.get_y())
        pdf.ln(h=1)
