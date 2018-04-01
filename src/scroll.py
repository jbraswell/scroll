import argparse
import json
import requests
import urllib.parse
import sys
from scroll import Booklet


def get_data(args):
    def form_sort_string():
        key_map = {
            'weekday': 'weekday_tinyint',
            'city': 'location_municipality',
        }
        ret = key_map.get(args.main_header_field)
        if args.second_header_field:
            ret += ',' + key_map.get(args.second_header_field)
        ret += ',start_time'
        return ret

    qs = urllib.parse.urlencode({
        'switcher': 'GetSearchResults',
        'get_used_formats': '1',
        'sort_keys': form_sort_string(),
        'services[]': args.service_body_ids.split(','),
        'recursive': '1' if args.recursive else '0'
    }, doseq=True)
    url = 'https://tomato.na-bmlt.org/main_server/client_interface/json/?' + qs

    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0 +scroll'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception('Bad status code {} from {}'.format(response.status_code, url))
    try:
        data = json.loads(response.content)
    except json.decoder.JSONDecodeError:
        raise Exception('Invalid json returned from {}'.format(url))

    return data['meetings'], data['formats']


def get_pdf(args, meetings, formats):
    kwargs = {
        'paper_size': args.paper_size,
        'bookletize': args.bookletize,
        'main_header_field': args.main_header_field,
    }
    if args.time_column_width:
        kwargs['time_column_width'] = args.time_column_width
    if args.duration_column_width:
        kwargs['duration_column_width'] = args.duration_column_width
    if args.meeting_font:
        kwargs['meeting_font'] = args.meeting_font
    if args.meeting_font_size:
        kwargs['meeting_font_size'] = args.meeting_font_size
    if args.header_font:
        kwargs['header_font'] = args.header_font
    if args.header_font_size:
        kwargs['header_font_size'] = args.header_font_size
    if args.second_header_field:
        kwargs['second_header_field'] = args.second_header_field
    booklet = Booklet(meetings, formats, args.output_file, **kwargs)
    booklet.write_pdf()


def main():
    parser = argparse.ArgumentParser(prog='scroll')
    parser.add_argument(
        'service_body_ids',
        help='Comma-separated list of service body ids. Scroll will retrieve the meetings for these service bodies '
             'from tomato'
    )
    parser.add_argument(
        'paper_size', choices=Booklet.PAPER_SIZES.keys(),
        help='The paper size you intend to use when printing the PDF'
    )
    parser.add_argument(
        'output_file',
        help='The path to the PDF file generated by scroll'
    )

    parser.add_argument(
        '--recursive',
        dest='recursive',
        action='store_true',
        help='If set, all meetings belonging to child service bodies of the specified service_body_ids will be included'
    )
    parser.add_argument(
        '--main-header-field',
        dest='main_header_field',
        default='weekday',
        choices=Booklet.VALID_HEADER_FIELDS,
        help='The primary header field to use when generating the PDF. Defaults to weekday'
    )
    parser.add_argument(
        '--second-header-field',
        dest='second_header_field',
        choices=Booklet.VALID_HEADER_FIELDS,
        help='The secondary header field to use when generating the PDF. Defaults to none'
    )
    parser.add_argument(
        '--bookletize',
        dest='bookletize',
        action='store_true',
        help='For use with printers without a \'booklet\' option. Two booklet pages per PDF page'
    )
    parser.add_argument(
        '--time-column-width',
        dest='time_column_width',
        type=int,
        default=20,
        help='The width, in mm, of the meeting start time column. Defaults to 20'
    )
    parser.add_argument(
        '--duration-column-width',
        dest='duration_column_width',
        type=int,
        default=15,
        help='The width, in mm, of the meeting duration column. Defaults to 15'
    )
    parser.add_argument(
        '--meeting-font',
        dest='meeting_font',
        default='dejavusans',
        choices=Booklet.VALID_FONTS,
        help='The font used for each meeting. Defaults to dejavusans'
    )
    parser.add_argument(
        '--meeting-font-size',
        dest='meeting_font_size',
        type=int,
        default=10,
        help='The font size used for each meeting. Defaults to 10'
    )
    parser.add_argument(
        '--header-font',
        dest='header_font',
        default='dejavusans',
        choices=Booklet.VALID_FONTS,
        help='The font used for headers. Defaults to dejavusans'
    )
    parser.add_argument(
        '--header-font-size',
        dest='header_font_size',
        type=int,
        default=10,
        help='The font size used for headers. Defaults to 10'
    )

    args = parser.parse_args()
    for id in args.service_body_ids.split(','):
        try:
            int(id)
        except:
            raise Exception('--service-body-ids is invalid, invalid value: {}'.format(id))
    if args.main_header_field == args.second_header_field:
        raise Exception('--main-header-field and --second-header-field cannot be the same')

    meetings, formats = get_data(args)
    get_pdf(args, meetings, formats)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        sys.stderr.write('Error: ' + str(e) + '\n')
        sys.exit(1)
