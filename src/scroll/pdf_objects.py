import re
from html.parser import HTMLParser
from fpdf.html import hex2dec
from .bmlt_objects import Format, Meeting


class StyledString:
    def __init__(self, value, style=''):
        self.value = str(value)
        self.style = style.upper()

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.style + ':' + self.value

    def split(self, *args, **kwargs):
        return [StyledString(s, style=self.style) for s in self.value.split(*args, **kwargs)]


class StyledStringParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output = []
        self.tags = []

    def reset(self):
        super().reset()
        self.output = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        if tag in ('b', 'i', 'u'):
            self.tags.append(tag)

    def handle_endtag(self, tag):
        if self.tags:
            self.tags.pop()

    def handle_data(self, data):
        style = ''.join(set(self.tags))
        self.output.append(StyledString(data, style=style))


def get_multi_cell_lines(pdf, text, max_line_length):
    lines = []
    current_line = ''
    parts = re.split(r' ', text)
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


def get_styled_line_cells(pdf, text, max_line_length, font, font_style, font_size):
    parser = StyledStringParser()
    parser.feed(text)
    parts = []
    for part in parser.output:
        if isinstance(part, StyledString):
            parts.extend([StyledString(p, style=part.style) for p in re.split(r' ', part.value)])
        else:
            parts.extend(part)

    lines = []
    current_line = []
    for i in range(len(parts)):
        part = parts[i]
        proposed_line = current_line.copy()
        if proposed_line:
            if isinstance(proposed_line[-1], StyledString) and isinstance(part, StyledString):
                if proposed_line[-1].style == part.style:
                    proposed_line[-1] = StyledString(str(proposed_line[-1]) + ' ' + str(part), style=part.style)
                else:
                    proposed_line.append(part)
            elif isinstance(proposed_line[-1], str) and isinstance(part, str):
                proposed_line[-1] = proposed_line[-1] + ' ' + part
            else:
                proposed_line.append(part)
        else:
            proposed_line.append(part)

        def get_width(line):
            w = 0
            for s in line:
                if isinstance(s, StyledString):
                    pdf.set_font(font, s.style, font_size)
                else:
                    pdf.set_font(font, font_style, font_size)
                w += pdf.get_string_width(str(s))
            return w

        width = get_width(proposed_line)
        if width + len(proposed_line) * 2 * pdf.c_margin > max_line_length:
            lines.append(current_line)
            current_line = [part]
        else:
            current_line = proposed_line

        width = get_width(current_line)
        if width + len(proposed_line) * 2 * pdf.c_margin > max_line_length:
            lines.append(current_line)
            current_line = []
        elif i == len(parts) - 1:
            lines.append(current_line)
    return lines


class PDFColumnEnd:
    pass


class PDFObject:
    def __init__(self, pdf_func):
        self.pdf_func = pdf_func

    @property
    def height(self):
        raise NotImplementedError()

    def write(self, pdf, x=None, y=None):
        raise NotImplementedError()


class PDFBlankPage(PDFObject):
    @property
    def height(self):
        pass

    def write(self, pdf, x=None, y=None):
        pass


class PDFSectionHeader(PDFObject):
    def __init__(self, text, pdf_func, cell_width, line_padding=1, font='dejavusans', font_size=12,
                 font_color='#000000', fill_color='#FFFFFF'):
        super().__init__(pdf_func)
        self.text = text
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


class PDFFormatsTable(PDFObject):
    def __init__(self, formats, pdf_func, total_width, margin_width=5, font='dejavusans', font_size=14,
                 key_column_width=10, table_header_text=None, header_font='dejavusans',
                 header_font_size=12, header_font_color='#000000', header_fill_color='#FFFFFF'):
        super().__init__(pdf_func)
        self.font = font
        self.font_size = font_size
        self.total_width = total_width
        self.margin_width = margin_width
        self.key_column_width = key_column_width
        self.table_header_text = table_header_text
        if self.table_header_text is None:
            self.table_header_text = 'Meeting Format Legend'
        self.header_font = header_font
        self.header_font_size = header_font_size
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
            font=self.header_font,
            font_size=self.header_font_size,
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
            font=self.header_font,
            font_size=self.header_font_size,
            font_color=self.header_font_color,
            fill_color=self.header_fill_color
        )
        header.write(pdf)

        left_x = x + (self.margin_width / 2)
        first = True
        current_y = pdf.get_y()
        for i in range(len(self.formats)):
            left = i % 2 == 0
            format = self.formats[i]
            current_x = left_x if left else left_x + self.total_column_width
            if first:
                border = 'LTRB' if left else 'TRB'
                if not left:
                    first = False
            else:
                border = 'LRB' if left else 'RB'
            before_y = current_y
            other = None
            if left and i < len(self.formats) - 1:
                other = self.formats[i + 1]
            elif not left:
                other = self.formats[i - 1]
            if other:
                while format.height < other.height:
                    format.format.name += ' '
            format.write(pdf, x=current_x, y=current_y, border=border)
            current_y = before_y if left else before_y + max(format.height, other.height)

        pdf.set_xy(x, pdf.get_y())


class PDFFormat(PDFObject):
    def __init__(self, format, pdf_func, key_column_width, name_column_width, font='dejavusans', font_size=10,
                 text_line_padding=1):
        if not isinstance(format, Format):
            raise TypeError('Expected Format object')
        super().__init__(pdf_func)
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
        lines = get_multi_cell_lines(pdf, self.format.name, self.name_column_width)
        text_height = pdf.font_size
        padding = len(lines) * self.text_line_padding
        height = (text_height * len(lines)) + padding
        return height

    def write(self, pdf, x=None, y=None, border='LTRB'):
        if x is not None and y is not None:
            pdf.set_xy(x, y)
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


class PDFMeeting(PDFObject):
    def __init__(self, meeting, pdf_func, total_width, time_column_width=None, duration_column_width=None,
                 font='dejavusans', font_size=12, separator_color='#D3D3D3'):
        if not isinstance(meeting, Meeting):
            raise TypeError('Expected Meeting object')
        super().__init__(pdf_func)
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
        lines = get_multi_cell_lines(pdf, meeting_name, self.meeting_column_width)
        text_height = pdf.font_size
        height = (text_height * len(lines))

        pdf.set_font(self.font, '', self.font_size)
        meeting_location = self.get_location()
        lines = get_multi_cell_lines(pdf, meeting_location, self.meeting_column_width)
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


class PDFPhoneList(PDFObject):
    def __init__(self, pdf_func, total_width, total_height, number_column_width=15, font='dejavusans', font_size=10,
                 font_color='#000000', header_text='Phone Numbers', header_font='dejavusans', header_font_size=14,
                 header_font_color='#000000', header_fill_color='#FFFFFF', header_top_margin=5, line_padding=5):
        super().__init__(pdf_func)
        self.total_width = total_width
        self.total_height = total_height
        self.number_column_width = number_column_width
        self.font = font
        self.font_size = font_size
        self.font_color = font_color
        self.header_text = header_text
        self.header_font = header_font
        self.header_font_size = header_font_size
        self.header_font_color = header_font_color
        self.header_fill_color = header_fill_color
        self.header_top_margin = header_top_margin
        self.line_padding = line_padding
        self.num_numbers = int((total_height - self.header_height) / self.line_height)

    @property
    def line_height(self):
        pdf = self.pdf_func()
        pdf.set_font(self.font, '', self.font_size)
        return pdf.font_size + self.line_padding

    @property
    def header_height(self):
        header = PDFSectionHeader(
            self.header_text,
            self.pdf_func,
            self.total_width,
            font=self.header_font,
            font_size=self.header_font_size,
            font_color=self.header_font_color,
            fill_color=self.header_fill_color
        )
        return header.height + self.header_top_margin + 3

    @property
    def height(self):
        pdf = self.pdf_func()
        return self.header_height + (self.line_height * self.num_numbers + pdf.line_width)

    def write(self, pdf, x=None, y=None):
        if x is not None and y is not None:
            pdf.set_xy(x, y)
        x = pdf.get_x()
        pdf.set_xy(x, pdf.get_y() + self.header_top_margin)
        header = PDFSectionHeader(
            self.header_text,
            self.pdf_func,
            self.total_width,
            font=self.header_font,
            font_size=self.header_font_size,
            font_color=self.header_font_color,
            fill_color=self.header_fill_color
        )
        header.write(pdf)
        pdf.ln(h=3)
        pdf.set_x(x)
        line_width = self.total_width - (self.number_column_width * 2)
        pdf.set_draw_color(*hex2dec('#000000'))
        for i in range(self.num_numbers):
            pdf.set_font(self.font, '', self.font_size)
            pdf.cell(self.number_column_width, h=pdf.font_size, txt=str(i + 1) + '.', align='R', ln=0)
            pdf.line(
                pdf.get_x(),
                pdf.get_y() + pdf.font_size,
                pdf.get_x() + line_width,
                pdf.get_y() + pdf.font_size
            )
            pdf.set_xy(x, pdf.get_y() + pdf.font_size + self.line_padding)


class PDFTwelveSteps(PDFObject):
    def __init__(self, pdf_func, total_width, font='dejavusans', font_size=12, font_color='#000000',
                 header_text='The Twelve Steps of NA', header_font='dejavusans', header_font_size=14,
                 header_font_color='#000000', header_fill_color='#FFFFFF', header_top_margin=0, line_padding=0,
                 number_colulmn_width=10):
        super().__init__(pdf_func)
        self.total_width = total_width
        self.font = font
        self.font_size = font_size
        self.font_color = font_color
        self.header_text = header_text
        self.header_font = header_font
        self.header_font_size = header_font_size
        self.header_font_color = header_font_color
        self.header_fill_color = header_fill_color
        self.header_top_margin = header_top_margin
        self.line_padding = line_padding
        self.number_column_width = number_colulmn_width

    @property
    def steps(self):
        return [
            'We admitted that we were powerless over our addiction, that our lives had become unmanageable.',
            'We came to believe that a Power greater than ourselves could restore us to sanity.',
            'We made a decision to turn our will and our lives over to the care of God <i>as we understood Him</i>.',
            'We made a searching and fearless moral inventory of ourselves.',
            'We admitted to God, to ourselves, and to another human being the exact nature of our wrongs.',
            'We were entirely ready to have God remove all these defects of character.',
            'We humbly asked Him to remove our shortcomings.',
            'We made a list of all persons we had harmed, and became willing to make amends to them all.',
            'We made direct amends to such people wherever possible, except when to do so would injure them or others.',
            'We continued to take personal inventory and when we were wrong promptly admitted it.',
            'We sought through prayer and meditation to improve our conscious contact with God <i>as we understood Him</i>, praying only for knowledge of His will for us and the power to carry that out.',
            'Having had a spiritual awakening as a result of these steps, we tried to carry this message to addicts, and to practice these principles in all our affairs.',
        ]

    @property
    def header_height(self):
        header = PDFSectionHeader(
            self.header_text,
            self.pdf_func,
            self.total_width,
            font=self.header_font,
            font_size=self.header_font_size,
            font_color=self.header_font_color,
            fill_color=self.header_fill_color
        )
        return header.height + self.header_top_margin + 3

    @property
    def steps_height(self):
        pdf = self.pdf_func()
        pdf.set_font(self.font, '', self.font_size)
        text_height = pdf.font_size
        height = 0
        for step in self.steps:
            lines = get_styled_line_cells(pdf, step, self.steps_column_width, self.font, '', self.font_size)
            padding = len(lines) * self.line_padding
            height += (text_height * len(lines)) + padding
        height += text_height * len(self.steps) - 1
        return height

    @property
    def height(self):
        return self.header_height + self.steps_height

    @property
    def steps_column_width(self):
        return self.total_width - (self.number_column_width * 2)

    def write(self, pdf, x=None, y=None):
        if x is not None and y is not None:
            pdf.set_xy(x, y)
        x = pdf.get_x()
        pdf.set_xy(x, pdf.get_y() + self.header_top_margin)
        header = PDFSectionHeader(
            self.header_text,
            self.pdf_func,
            self.total_width,
            font=self.header_font,
            font_size=self.header_font_size,
            font_color=self.header_font_color,
            fill_color=self.header_fill_color
        )
        header.write(pdf)
        pdf.ln(h=3)
        pdf.set_x(x)
        for i in range(len(self.steps)):
            pdf.set_font(self.font, '', self.font_size)
            pdf.cell(self.number_column_width, h=pdf.font_size, txt=str(i + 1) + '.', align='R', ln=0)
            step = self.steps[i]
            lines = get_styled_line_cells(pdf, step, self.steps_column_width, self.font, '', self.font_size)
            for line in lines:
                for text in line:
                    style = text.style if isinstance(text, StyledString) else ''
                    text = str(text)
                    pdf.set_font(self.font, style, self.font_size)
                    pdf.cell(pdf.get_string_width(text), h=pdf.font_size, txt=text, align='L', ln=0)
                pdf.ln(h=pdf.font_size + self.line_padding)
                pdf.set_xy(x + self.number_column_width, pdf.get_y())
            pdf.ln(h=pdf.font_size + self.line_padding)
            pdf.set_xy(x + self.number_column_width, pdf.get_y())
            if i < len(self.steps) - 1:
                pdf.set_xy(x, pdf.get_y())


class PDFTwelveTraditions(PDFTwelveSteps):
    def __init__(self, *args, **kwargs):
        if 'header_text' not in kwargs:
            kwargs['header_text'] = 'The Twelve Traditions of NA'
        super().__init__(*args, **kwargs)

    @property
    def steps(self):
        return [
            'Our common welfare should come first; personal recovery depends on NA unity.',
            'For our group purpose there is but one ultimate authority—a loving God as He may express Himself in our group conscience. Our leaders are but trusted servants; they do not govern.',
            'The only requirement for membership is a desire to stop using.',
            'Each group should be autonomous except in matters affecting other groups or NA as a whole.',
            'Each group has but one primary purpose—to carry the message to the addict who still suffers.',
            'An NA group ought never endorse, finance, or lend the NA name to any related facility or outside enterprise, lest problems of money, property, or prestige divert us from our primary purpose.',
            'Every NA group ought to be fully self-supporting, declining outside contributions.',
            'Narcotics Anonymous should remain forever nonprofessional, but our service centers may employ special workers.',
            'NA, as such, ought never be organized, but we may create service boards or committees directly responsible to those they serve.',
            'Narcotics Anonymous has no opinion on outside issues; hence the NA name ought never be drawn into public controversy.',
            'Our public relations policy is based on attraction rather than promotion; we need always maintain personal anonymity at the level of press, radio, and films.',
            'Anonymity is the spiritual foundation of all our traditions, ever reminding us to place principles before personalities.',
        ]
