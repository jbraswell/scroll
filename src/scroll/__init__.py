import os
from fpdf import FPDF
from .bmlt_objects import Format, Meeting
from .pdf_objects import (PDFColumnEnd, PDFMainSectionHeader, PDFSubSectionHeader, PDFFormatsTable, PDFMeeting,
                          PDFMainPagePlaceholder)


weekdays = [
    'Sunday',
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
]


class Booklet:
    PAPER_SIZES = {
        'letter': (216, 279),
        'legal': (216, 356),
        'tabloid': (279, 432),
    }
    VALID_FONTS = [
        'dejavusans',
        'dejavuserif'
    ]
    HEADER_FIELD_WEEKDAY = 'weekday'
    HEADER_FIELD_CITY = 'city'
    VALID_HEADER_FIELDS = [
        HEADER_FIELD_WEEKDAY,
        HEADER_FIELD_CITY
    ]

    def __init__(self, meetings, formats, output_file, bookletize=False, paper_size='Letter', time_column_width=None,
                 duration_column_width=None, meeting_font='dejavusans', meeting_font_size=10, header_font='dejavusans',
                 header_font_size=10, main_header_field='weekday', second_header_field=None,
                 meeting_separator_color='#D3D3D3', formats_table_header_text='Meeting Format Legend',
                 formats_table_header_font='dejavusans', formats_table_header_font_size=14,
                 formats_table_key_column_width=10, formats_table_margin_width=5,
                 formats_table_header_font_color='#000000', formats_table_header_fill_color='#FFFFFF'):
        self._meetings_data = meetings
        self._formats_data = formats
        self.output_file = output_file
        self.bookletize = bookletize
        self.time_column_width = time_column_width
        self.duration_column_width = duration_column_width
        if paper_size.lower() not in self.PAPER_SIZES.keys():
            raise ValueError("Invalid paper size, valid choices are: {}".format(', '.join(self.PAPER_SIZES.keys())))
        self.paper_size = self.PAPER_SIZES[paper_size.lower()]
        if meeting_font.lower() not in self.VALID_FONTS:
            raise ValueError("Invalid meeting font, valid choices are: {}".format(', '.join(self.VALID_FONTS)))
        self.meeting_font = meeting_font
        self.meeting_font_size = meeting_font_size
        if header_font.lower() not in self.VALID_FONTS:
            raise ValueError("Invalid header font, valid choices are: {}".format(', '.join(self.VALID_FONTS)))
        self.header_font = header_font
        self.header_font_size = header_font_size
        if main_header_field not in self.VALID_HEADER_FIELDS:
            raise ValueError("Invalid main header field, valid choices are: {}".format(', '.join(self.VALID_HEADER_FIELDS)))
        self.main_header_field = main_header_field
        if second_header_field and second_header_field not in self.VALID_HEADER_FIELDS:
            raise ValueError("Invalid second header field, valid choices are: {}".format(', '.join(self.VALID_HEADER_FIELDS)))
        self.second_header_field = second_header_field
        self.meeting_separator_color = meeting_separator_color
        self.formats_table_header_text = formats_table_header_text
        self.formats_table_header_font = formats_table_header_font
        self.formats_table_header_font_size = formats_table_header_font_size
        self.formats_table_key_column_width = formats_table_key_column_width
        self.formats_table_margin_width = formats_table_margin_width
        self.formats_table_header_font_color = formats_table_header_font_color
        self.formats_table_header_fill_color = formats_table_header_fill_color

    def _get_pdf_obj(self):
        if self.bookletize:
            # The bookletize option is for those who don't have, don't want to use, or don't
            # know how to use the "booklet" option on their printer. It does the hard work of
            # arranging the booklet pages on paper in a landscape orientation.
            pdf = FPDF(orientation='L', format=self.paper_size)
        else:
            # This produces booklet pages as single pdf pages. They're designed to be printed
            # using the "booklet" option on a printer, meaning two per page. For this reason,
            # we're dividing the specified paper size by 2.
            pdf = FPDF(format=(self.paper_size[1] / 2, self.paper_size[0]))
        pdf.set_margins(5, 5)
        pdf.set_auto_page_break(0, 5)
        base_font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dejavu-fonts-ttf-2.37/ttf/')
        pdf.add_font('dejavusans', '', os.path.join(base_font_path, 'DejaVuSansCondensed.ttf'), uni=True)
        pdf.add_font('dejavusans', 'B', os.path.join(base_font_path, 'DejaVuSansCondensed-Bold.ttf'), uni=True)
        pdf.add_font('dejavuserif', '', os.path.join(base_font_path, 'DejaVuSerifCondensed.ttf'), uni=True)
        pdf.add_font('dejavuserif', 'B', os.path.join(base_font_path, 'DejaVuSerifCondensed-Bold.ttf'), uni=True)
        return pdf

    def get_pdf_objects(self):
        pdf = self._get_pdf_obj()
        effective_page_width = pdf.w - pdf.l_margin - pdf.r_margin
        effective_page_height = pdf.h - pdf.t_margin - pdf.b_margin
        total_width = (effective_page_width / 2) - 1 if self.bookletize else effective_page_width

        pdf.add_page()

        def _append_pdf_objects(l, objs, pos):
            height = sum([o.height for o in objs])
            if pos + height > effective_page_height:
                l.append(PDFColumnEnd())
                if not isinstance(objs[0], PDFMainSectionHeader):
                    for obj in l[::-1]:
                        if isinstance(obj, PDFMainSectionHeader):
                            cont_header = obj.copy()
                            if not cont_header.text.endswith('(Continued)'):
                                cont_header.text += ' (Continued)'
                            height += cont_header.height
                            l.append(cont_header)
                            break
                    if not isinstance(objs[0], PDFSubSectionHeader):
                        for obj in l[::-1]:
                            if isinstance(obj, PDFSubSectionHeader):
                                cont_header = obj.copy()
                                if not cont_header.text.endswith('(Continued)'):
                                    cont_header.text += ' (Continued)'
                                height += cont_header.height
                                l.append(cont_header)
                                break
                pos = 0
            l.extend(objs)
            pos += height
            return pos

        pdf_objects = [
            PDFMainPagePlaceholder(),
            PDFColumnEnd()
        ]

        # Add meetings
        prev_main_header = None
        prev_second_header = None
        current_content_position = 0
        for m in self._meetings_data:
            append_objs = []
            meeting = PDFMeeting(Meeting(m), self._get_pdf_obj, total_width, time_column_width=self.time_column_width,
                                 duration_column_width=self.duration_column_width, font=self.meeting_font,
                                 font_size=self.meeting_font_size, separator_color=self.meeting_separator_color)
            new_main_header = getattr(meeting.meeting, self.main_header_field)
            if new_main_header != prev_main_header:
                if self.main_header_field == self.HEADER_FIELD_WEEKDAY:
                    text = weekdays[new_main_header - 1]
                else:
                    text = new_main_header
                header = PDFMainSectionHeader(
                    text,
                    self._get_pdf_obj,
                    total_width,
                    font=self.header_font,
                    font_size=self.header_font_size
                )
                append_objs.append(header)
                prev_main_header = new_main_header
                prev_second_header = None
            if self.second_header_field:
                new_second_header = getattr(meeting.meeting, self.second_header_field)
                if new_second_header != prev_second_header:
                    if self.second_header_field == self.HEADER_FIELD_WEEKDAY:
                        text = weekdays[new_second_header - 1]
                    else:
                        text = new_second_header
                    header = PDFSubSectionHeader(
                        text,
                        self._get_pdf_obj,
                        total_width,
                        font=self.header_font,
                        font_size=self.header_font_size
                    )
                    append_objs.append(header)
                    prev_second_header = new_second_header
            append_objs.append(meeting)
            current_content_position = _append_pdf_objects(pdf_objects, append_objs, current_content_position)

        # Add formats page
        if not isinstance(pdf_objects[-1], PDFColumnEnd):
            pdf_objects.append(PDFColumnEnd())
        formats = [Format(f) for f in self._formats_data]
        formats_table = PDFFormatsTable(
            formats,
            self._get_pdf_obj,
            total_width,
            font=self.meeting_font,
            font_size=self.meeting_font_size,
            table_header_text=self.formats_table_header_text,
            table_header_font=self.formats_table_header_font,
            table_header_font_size=self.formats_table_header_font_size,
            key_column_width=self.formats_table_key_column_width,
            margin_width=self.formats_table_margin_width,
            header_font_color=self.formats_table_header_font_color,
            header_fill_color=self.formats_table_header_fill_color
        )
        pdf_objects.append(formats_table)
        # TODO Append phone numbers to fill additional space

        return pdf_objects

    def get_pages(self):
        pdf_objects = self.get_pdf_objects()
        pages = []
        current_page = []
        for i in range(len(pdf_objects)):
            obj = pdf_objects[i]
            if isinstance(obj, PDFColumnEnd):
                pages.append(current_page)
                current_page = []
                continue
            current_page.append(obj)
            if i == len(pdf_objects) - 1:
                pages.append(current_page)
                current_page = []
        return pages

    def write_pdf(self):
        booklet_pages = self.get_pages()
        pdf = self._get_pdf_obj()

        if self.bookletize:
            pdf.add_page()
            effective_page_width = pdf.w - pdf.l_margin - pdf.r_margin
            column_width = (effective_page_width / 2) - 1

            last_page = booklet_pages.pop()
            for obj in last_page:
                obj.write(pdf)

            first_page = booklet_pages.pop(0)
            for obj in first_page:
                obj.write(pdf, x=column_width + pdf.l_margin + 2, y=pdf.get_y())

            total_booklet_length = len(booklet_pages)
            last_booklet_page_blank = total_booklet_length % 2 != 0
            if last_booklet_page_blank or total_booklet_length in [3, 4]:
                pdf.add_page()
                left_page = booklet_pages.pop(0)
                for obj in left_page:
                    obj.write(pdf)
            if total_booklet_length in [3, 4]:
                pdf.add_page()
                right_page = booklet_pages.pop(0)
                last_y = pdf.get_y()
                for obj in right_page:
                    obj.write(pdf, x=column_width + pdf.l_margin + 2, y=last_y)
                    last_y = pdf.get_y()

            while booklet_pages:
                pdf.add_page()
                odd_pdf_page = pdf.page_no() % 2 == 1
                original_y = pdf.get_y()

                left_page = booklet_pages.pop() if odd_pdf_page else booklet_pages.pop(0)
                for obj in left_page:
                    obj.write(pdf)

                if booklet_pages:
                    last_y = original_y
                    right_page = booklet_pages.pop(0) if odd_pdf_page else booklet_pages.pop()
                    for obj in right_page:
                        obj.write(pdf, x=column_width + pdf.l_margin + 2, y=last_y)
                        last_y = pdf.get_y()
        else:
            for page in booklet_pages:
                pdf.add_page()
                for obj in page:
                    obj.write(pdf)

        pdf.output(self.output_file, 'F')
        return
