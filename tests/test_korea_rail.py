"""KORAIL publication calendars, clocks and nationwide replay checks."""
import gzip
import json
import pytest
from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_korea_rail import OUTPUT, running_days, station_name, time_value, workbook


def test_published_weekdays_and_nonstop_placeholders():
    assert running_days('매일') == tuple(range(7))
    assert running_days('월,화,수,목,금') == (0, 1, 2, 3, 4)
    assert running_days('금토일') == (4, 5, 6)
    assert running_days(None, blank_daily=True) == tuple(range(7))
    for flag in [None, '공휴일', '월요일외']:
        with pytest.raises(ValueError): running_days(flag)
    assert time_value({'time': 0}) is None
    assert time_value({'time': 86400}) == 86400
    assert time_value({'time': 90120}) == 90120
    assert time_value('12:00') is None
    assert station_name('홍성(출발)') == station_name('홍성(도착)') == '홍성'
    assert station_name('진부(오대산)') == '진부'
    assert station_name('판교(경기)') != station_name('판교')


def test_bundled_korail_scope_geometry_and_business_day_ownership():
    with gzip.open(OUTPUT, 'rt') as f: reference = json.load(f)
    assert len(reference['days']) == 7
    assert reference['metadata']['unlocated_station_trip_exclusions'] == {}
    assert reference['metadata']['omitted_trips'] == {}
    assert len({p['line'] for p in reference['patterns'].values()}) == 11
    assert all('stop_pattern' in p and 'stops' not in p for p in reference['patterns'].values())
    assert all(not p['coordinates'] for p in reference['paths'].values() if p['quality'] == 'approximate')
    seen = set()
    overnight = False
    for day, expected in [('2025-10-20', 822), ('2025-10-21', 821), ('2025-10-26', 909)]:
        payload = replay.get_replay_day(day, 'south_korea')
        assert len(payload['services']) == expected
        assert descriptor(day, 'south_korea')['modes'] == ['high_speed_rail', 'train']
        assert payload['timezone'] == 'Asia/Seoul' and payload['passenger_data'] is False
        for s in payload['services']:
            p = payload['transit_patterns'][s['pattern']]
            start = s['departure'] + int(p['times'][1])
            end = s['departure'] + int(p['times'][-1])
            assert payload['start'] <= start < payload['start'] + 86400
            assert payload['end'] >= end
            assert p['operator'] in {'KORAIL', 'SR'} and s['number'].removeprefix('S').isdigit()
            occurrence = (p['operator'], s['number'], start)
            assert occurrence not in seen
            seen.add(occurrence)
            overnight |= end > payload['start'] + 21 * 3600
    assert overnight
    selected = replay.get_replay_day('2025-10-20', 'south_korea', modes=('high_speed_rail',))
    assert len(selected['services']) == 448
    assert {s['mode'] for s in selected['services']} == {'high_speed_rail'}
    assert all(p['line'].startswith('KTX') or p['line']=='SRT' for p in selected['transit_patterns'].values())


def test_representative_published_trains_and_station_disambiguation():
    with gzip.open(OUTPUT, 'rt') as f: reference = json.load(f)
    # Yangwon on the Yeongdong Line is not the identically named Seoul station;
    # Jangheung on the Gyooe Line is not Jeonnam Jangheung.
    stations = {s['name']: s for s in reference['stations']}
    assert stations['양원']['lon'] > 128
    assert stations['장흥']['lat'] > 37
    day = replay.get_replay_day('2025-10-20', 'south_korea')
    services = {s['number']: s for s in day['services']}
    for number, line, origin, destination in [('1013', 'ITX-Saemaeul', '서울', '부산'), ('109', 'KTX', '서울', '부산'), ('1256', 'ITX-Maum', '강릉', '부전')]:
        service = services[number]
        pattern = day['transit_patterns'][service['pattern']]
        assert (pattern['line'], pattern['origin'], pattern['destination']) == (line, origin, destination)


def test_xlsx_reader_preserves_24_hour_clock_and_train_number(tmp_path):
    from zipfile import ZipFile
    path = tmp_path / 'clock.xlsx'
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    with ZipFile(path, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="'+ns+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Clock" sheetId="1" r:id="r1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/styles.xml', '<styleSheet xmlns="'+ns+'"><cellXfs><xf numFmtId="0"/><xf numFmtId="20"/></cellXfs></styleSheet>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="'+ns+'"><sheetData><row r="1"><c r="A1" s="1"><v>0</v></c><c r="B1" s="1"><v>1</v></c><c r="C1" s="1"><v>0.5</v></c><c r="D1"><v>109</v></c></row></sheetData></worksheet>')
    row = workbook(path)['Clock'][0]
    assert row == [{'time': 0}, {'time': 86400}, {'time': 43200}, 109]


def test_itx_passing_times_dwell_and_midnight_are_distinguished():
    from scripts.prepare_korea_rail import parse_cheongchun
    rows = [
        ['시발역', '용산'], ['종착역', '춘천'], ['열차번호', 'S2001'],
        ['용산', ''], [None, {'time': 85800}],
        ['한남', ''], [None, {'time': 86100}],  # Passing clock, not a stop.
        ['가평', {'time': 0}], [None, {'time': 60}],
        ['춘천', {'time': 1800}], [None, ''],
    ]
    t = parse_cheongchun({'ITX-청춘 하행(평)': rows})[0]
    assert t['days'] == (0, 1, 2, 3, 4)
    assert t['calls'] == [('용산', '용산', 85800), ('가평', '가평', 86400), ('춘천', '춘천', 88200)]
    assert t['departures'] == [85800, 86460, 88200]
    assert parse_cheongchun({'ITX-청춘 하행(휴)': rows})[0]['days'] == (5, 6)
    rows[8][1] = {'time': 85700}
    with pytest.raises(ValueError): parse_cheongchun({'ITX-청춘 하행(평)': rows})


def test_srt_pdf_clocks_require_complete_valid_published_times():
    from scripts.prepare_korea_rail import pdf_clock
    assert pdf_clock('00:00') == 0
    assert pdf_clock('23:59') == 86340
    for text in ['6:30', '24:00', '12:60', '05:3005:47']:
        with pytest.raises(ValueError): pdf_clock(text)


def test_srt_running_days_and_itx_weekend_patterns():
    def services(day, line):
        payload = replay.get_replay_day(day, 'south_korea')
        return payload, {s['number']: s for s in payload['services']
                         if payload['transit_patterns'][s['pattern']]['line'] == line}
    monday, srt = services('2025-10-20', 'SRT')
    _, friday = services('2025-10-24', 'SRT')
    assert len(srt) == 122 and len(friday) == 132
    assert '305' not in srt and '305' in friday
    for number, destination in [('301', '부산'), ('381', '진주'), ('391', '포항'), ('651', '목포'), ('681', '여수EXPO')]:
        pattern = monday['transit_patterns'][srt[number]['pattern']]
        assert (pattern['operator'], pattern['origin'], pattern['destination']) == ('SR', '수서', destination)
    day, itx = services('2025-10-20', 'ITX-Cheongchun')
    _, weekend = services('2025-10-25', 'ITX-Cheongchun')
    assert len(itx) == 36 and len(weekend) == 52
    assert 'S2001' in itx and 'S2001' not in weekend
    assert 'S2051' in weekend and 'S2051' not in itx
    pattern = day['transit_patterns'][itx['S2001']['pattern']]
    assert (pattern['origin'], pattern['destination']) == ('용산', '춘천')
    assert int(pattern['times'][3])-int(pattern['times'][2]) == 60
    # The last weekday train genuinely crosses midnight.
    last = itx['S2035']
    assert last['departure']+int(day['transit_patterns'][last['pattern']]['times'][-1]) > day['start']+21*3600
