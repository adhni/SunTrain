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
    assert len({p['line'] for p in reference['patterns'].values()}) == 9
    assert all('stop_pattern' in p and 'stops' not in p for p in reference['patterns'].values())
    assert all(not p['coordinates'] for p in reference['paths'].values() if p['quality'] == 'approximate')
    seen = set()
    overnight = False
    for day, expected in [('2025-10-20', 664), ('2025-10-21', 663), ('2025-10-26', 725)]:
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
            assert p['operator'] == 'KORAIL' and s['number'].isdigit()
            occurrence = (s['number'], start)
            assert occurrence not in seen
            seen.add(occurrence)
            overnight |= end > payload['start'] + 21 * 3600
    assert overnight
    selected = replay.get_replay_day('2025-10-20', 'south_korea', modes=('high_speed_rail',))
    assert len(selected['services']) == 326
    assert {s['mode'] for s in selected['services']} == {'high_speed_rail'}
    assert all(p['line'].startswith('KTX') for p in selected['transit_patterns'].values())


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
