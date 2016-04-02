# -*- coding: utf-8 -*-

def ParseNewsTitle(title):
    return Regex(
        u'(?P<date>\d{2}\.\d{2}\.\d{4})\sДобавлена'
        u'\s(?P<episode>\d+)\sсерия\sсериала\s(?P<title>.+)'
        u'\s(?P<season>\d+)\sсезон'
    ).match(title).groupdict()
