# Test suite for log_analyzer.py
import pytest
from log_analyzer import parse_log_lines


def test_parse_log_lines_basic():
    lines = [
        'TOTAL_AUDIO_TO_ANALYZE: 5',
        'ANALYZING_AUDIO: 2/5: file2.wav',
        'Some unrelated line',
    ]
    patterns = {
        'total': r'TOTAL_AUDIO_TO_ANALYZE:\s*(\d+)',
        'current': r'ANALYZING_AUDIO:\s*(\d+)/(\d+):\s*(.*)'
    }
    result = parse_log_lines(lines, patterns)
    assert 'total' in result
    assert result['total'] == 5
    assert 'current' in result
    assert result['current']['idx'] == 2
    assert result['current']['total'] == 5
    assert result['current']['item'] == 'file2.wav'


def test_parse_log_lines_unparsed():
    lines = ['Unmatched log entry']
    patterns = {}
    result = parse_log_lines(lines, patterns, show_unparsed=True)
    assert 'unparsed' in result
    assert result['unparsed'] == ['Unmatched log entry']
